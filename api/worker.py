import asyncio
import json
import time
from pathlib import Path

from .agents import Dependencies, answer_question
from .config import settings
from .datasets import import_dataset
from .science import investigate
from .store import Store


def claim_next(store: Store) -> dict | None:
    with store.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
        if not row:
            return None
        conn.execute("UPDATE jobs SET status='running',updated=? WHERE id=?", (time.time(), row["id"]))
    result = dict(row)
    result["payload"] = json.loads(result["payload"])
    return result


async def execute_job(store: Store, job: dict):
    payload, workspace, job_id = job["payload"], job["workspace"], job["id"]
    try:
        if job["kind"] == "import":
            store.event(job_id, "stage", "Data import", "Validating and importing the file")
            result = await asyncio.to_thread(
                import_dataset,
                store,
                workspace,
                payload["profile_id"],
                Path(payload["source"]),
                payload["kind"],
                payload["metadata"],
                payload["filename"],
            )
        elif job["kind"] == "chat":
            result = await answer_question(
                Dependencies(store, workspace, payload["profile_id"], job_id), payload["question"]
            )
        elif job["kind"] == "investigation":
            result = await investigate(store, workspace, payload, job_id)
        else:
            raise ValueError("Unknown job type.")
        # Deletion during execution must not restore a deleted profile's results.
        if not store.profile(workspace, payload["profile_id"]):
            return
        store.finish(job_id, result)
        store.event(job_id, "completed", "Workspace", "Results are ready")
    except Exception as exc:
        message = (
            str(exc)
            if isinstance(exc, ValueError)
            else f"{type(exc).__name__}: the dependency did not complete. No result was substituted."
        )
        store.finish(job_id, error=message)
        store.event(job_id, "failed", "Workspace", message)
    finally:
        if job["kind"] == "import":
            Path(payload["source"]).unlink(missing_ok=True)


async def loop(store: Store, stop: asyncio.Event):
    # There is one worker per store. Recover interrupted runs as retryable failures, not endless spinners.
    with store.connection() as conn:
        interrupted = conn.execute("SELECT id FROM jobs WHERE status='running'").fetchall()
    for row in interrupted:
        message = "The server restarted before this run finished. Your question is saved; retry the answer."
        store.finish(row["id"], error=message)
        store.event(row["id"], "failed", "Workspace", message)
    while not stop.is_set():
        job = await asyncio.to_thread(claim_next, store)
        if job:
            await execute_job(store, job)
        else:
            try:
                await asyncio.wait_for(stop.wait(), timeout=0.3)
            except TimeoutError:
                pass


def main():
    asyncio.run(loop(Store(settings), asyncio.Event()))
