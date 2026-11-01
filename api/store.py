import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import Settings


def identifier() -> str:
    return uuid.uuid4().hex


class Store:
    def __init__(self, config: Settings):
        self.config = config
        self.root = config.dna_data_dir.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "helix.sqlite3"
        with self.connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, token_hash TEXT UNIQUE, expires REAL, demo INTEGER);
            CREATE TABLE IF NOT EXISTS profiles (
              id TEXT PRIMARY KEY, workspace TEXT, payload TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS datasets (
              id TEXT PRIMARY KEY, workspace TEXT, profile TEXT, kind TEXT,
              filename TEXT, path TEXT, metadata TEXT, report TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, workspace TEXT, kind TEXT, payload TEXT, status TEXT,
              result TEXT, error TEXT, created REAL, updated REAL);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT, kind TEXT, agent TEXT,
              message TEXT, data TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS cache (
              key TEXT PRIMARY KEY, payload TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS conversations (
              id TEXT PRIMARY KEY, workspace TEXT, profile TEXT, title TEXT, created REAL, updated REAL);
            CREATE INDEX IF NOT EXISTS dataset_profile ON datasets(workspace,profile,kind);
            CREATE INDEX IF NOT EXISTS events_job ON events(job,id);
            CREATE INDEX IF NOT EXISTS conversation_profile ON conversations(workspace,profile,updated);
            CREATE INDEX IF NOT EXISTS chat_conversation ON jobs(workspace,kind,json_extract(payload,'$.conversation_id'),created);
            """)
            # Preserve pre-history-UI jobs; arbitrary legacy IDs were only unique within a workspace/profile.
            legacy = conn.execute(
                "SELECT j.* FROM jobs j LEFT JOIN conversations c ON c.id=json_extract(j.payload,'$.conversation_id') "
                "AND c.workspace=j.workspace AND c.profile=json_extract(j.payload,'$.profile_id') "
                "WHERE j.kind='chat' AND c.id IS NULL ORDER BY j.created"
            ).fetchall()
            for row in legacy:
                payload = json.loads(row["payload"])
                profile = payload.get("profile_id")
                if not conn.execute(
                    "SELECT 1 FROM profiles WHERE id=? AND workspace=?", (profile, row["workspace"])
                ).fetchone():
                    continue
                conversation = uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"helix:{row['workspace']}:{profile}:{payload.get('conversation_id') or 'legacy'}",
                ).hex
                conn.execute(
                    "INSERT OR IGNORE INTO conversations VALUES (?,?,?,?,?,?)",
                    (
                        conversation,
                        row["workspace"],
                        profile,
                        payload.get("question", "Previous chat")[:70],
                        row["created"],
                        row["updated"],
                    ),
                )
                conn.execute(
                    "UPDATE conversations SET updated=MAX(updated,?) WHERE id=?",
                    (row["updated"], conversation),
                )
                payload["conversation_id"] = conversation
                conn.execute("UPDATE jobs SET payload=? WHERE id=?", (json.dumps(payload), row["id"]))

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def session(self, demo: bool) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        workspace = identifier()
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO sessions VALUES (?,?,?,?)",
                (workspace, hashlib.sha256(token.encode()).hexdigest(), time.time() + 8 * 3600, int(demo)),
            )
        return token, workspace

    def authenticate(self, token: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE token_hash=? AND expires>?",
                (hashlib.sha256(token.encode()).hexdigest(), time.time()),
            ).fetchone()
        return dict(row) if row else None

    def profile(self, workspace: str, profile_id: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM profiles WHERE id=? AND workspace=?", (profile_id, workspace)
            ).fetchone()
        return {"id": row["id"], **json.loads(row["payload"])} if row else None

    def profiles(self, workspace: str) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM profiles WHERE workspace=? ORDER BY created", (workspace,)
            ).fetchall()
        return [{"id": row["id"], **json.loads(row["payload"])} for row in rows]

    def create_profile(self, workspace: str, payload: dict) -> dict:
        profile_id = identifier()
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO profiles VALUES (?,?,?,?)",
                (profile_id, workspace, json.dumps(payload), time.time()),
            )
        return {"id": profile_id, **payload}

    def datasets(self, workspace: str, profile_id: str, kind: str | None = None) -> list[dict]:
        query = "SELECT * FROM datasets WHERE workspace=? AND profile=?"
        params = [workspace, profile_id]
        if kind:
            query += " AND kind=?"
            params.append(kind)
        query += " ORDER BY created DESC"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {**dict(r), "metadata": json.loads(r["metadata"]), "report": json.loads(r["report"])}
            for r in rows
        ]

    def add_dataset(
        self,
        workspace: str,
        profile_id: str,
        kind: str,
        name: str,
        path: Path,
        metadata: dict,
        report: dict,
        dataset_id: str | None = None,
    ) -> str:
        dataset_id = dataset_id or identifier()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute(
                "SELECT 1 FROM profiles WHERE id=? AND workspace=?", (profile_id, workspace)
            ).fetchone():
                path.unlink(missing_ok=True)
                raise ValueError("Profile was deleted before import completed.")
            conn.execute(
                "INSERT INTO datasets VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    dataset_id,
                    workspace,
                    profile_id,
                    kind,
                    name,
                    str(path),
                    json.dumps(metadata),
                    json.dumps(report),
                    time.time(),
                ),
            )
        return dataset_id

    def new_job(self, workspace: str, kind: str, payload: dict) -> str:
        job = identifier()
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
                (job, workspace, kind, json.dumps(payload), "queued", None, None, time.time(), time.time()),
            )
        return job

    def conversations(self, workspace: str, profile: str) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT c.*, (SELECT COUNT(*) FROM jobs j WHERE j.workspace=c.workspace AND j.kind='chat' "
                "AND json_extract(j.payload,'$.conversation_id')=c.id) AS message_count "
                "FROM conversations c WHERE c.workspace=? AND c.profile=? ORDER BY c.updated DESC,c.id",
                (workspace, profile),
            ).fetchall()
        return [{k: r[k] for k in r.keys() if k != "workspace"} for r in rows]

    def new_conversation(self, workspace: str, profile: str, title: str = "New chat") -> dict:
        if not self.profile(workspace, profile):
            raise LookupError("Profile not found.")
        conversation, now = identifier(), time.time()
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO conversations VALUES (?,?,?,?,?,?)",
                (conversation, workspace, profile, title, now, now),
            )
        return {
            "id": conversation,
            "profile": profile,
            "title": title,
            "created": now,
            "updated": now,
            "message_count": 0,
        }

    def conversation(self, workspace: str, conversation: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id=? AND workspace=?", (conversation, workspace)
            ).fetchone()
        return {k: row[k] for k in row.keys() if k != "workspace"} if row else None

    def queue_chat(
        self, workspace: str, profile: str, question: str, conversation: str | None
    ) -> tuple[str, str]:
        now, job = time.time(), identifier()
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute(
                "SELECT 1 FROM profiles WHERE id=? AND workspace=?", (profile, workspace)
            ).fetchone():
                raise LookupError("Profile not found.")
            if conversation:
                if not conn.execute(
                    "SELECT 1 FROM conversations WHERE id=? AND workspace=? AND profile=?",
                    (conversation, workspace, profile),
                ).fetchone():
                    raise LookupError("Chat not found for this profile.")
            else:
                conversation = identifier()
                conn.execute(
                    "INSERT INTO conversations VALUES (?,?,?,?,?,?)",
                    (conversation, workspace, profile, "New chat", now, now),
                )
            pending = conn.execute(
                "SELECT 1 FROM jobs WHERE workspace=? AND kind='chat' AND status IN ('queued','running') "
                "AND json_extract(payload,'$.conversation_id')=?",
                (workspace, conversation),
            ).fetchone()
            if pending:
                raise ValueError("This chat is still answering. Wait for the reply or start a new chat.")
            count = conn.execute(
                "SELECT COUNT(*) FROM jobs WHERE workspace=? AND kind='chat' AND json_extract(payload,'$.conversation_id')=?",
                (workspace, conversation),
            ).fetchone()[0]
            payload = {"profile_id": profile, "question": question, "conversation_id": conversation}
            conn.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
                (job, workspace, "chat", json.dumps(payload), "queued", None, None, now, now),
            )
            conn.execute(
                "UPDATE conversations SET updated=?,title=CASE WHEN ?=0 THEN ? ELSE title END WHERE id=?",
                (now, count, " ".join(question.split())[:70], conversation),
            )
        return job, conversation

    def conversation_messages(self, workspace: str, conversation: str, limit: int = 200) -> dict:
        item = self.conversation(workspace, conversation)
        if not item:
            raise LookupError("Chat not found.")
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE workspace=? AND kind='chat' AND json_extract(payload,'$.conversation_id')=? "
                "AND json_extract(payload,'$.profile_id')=? ORDER BY created DESC,id DESC LIMIT ?",
                (workspace, conversation, item["profile"], limit + 1),
            ).fetchall()
            has_more = len(rows) > limit
            rows = list(reversed(rows[:limit]))
            by_job: dict[str, list] = {r["id"]: [] for r in rows}
            if rows:
                placeholders = ",".join("?" for _ in rows)
                for event in conn.execute(
                    f"SELECT * FROM events WHERE job IN ({placeholders}) ORDER BY id", list(by_job)
                ).fetchall():
                    by_job[event["job"]].append({**dict(event), "data": json.loads(event["data"])})
        messages = []
        for row in rows:
            result = json.loads(row["result"]) if row["result"] else {}
            messages.append(
                {
                    "id": row["id"],
                    "question": json.loads(row["payload"])["question"],
                    "answer": result.get("answer"),
                    "error": row["error"],
                    "status": row["status"],
                    "created": row["created"],
                    "events": by_job[row["id"]],
                }
            )
        return {"conversation": item, "messages": messages, "has_more": has_more}

    def retry_chat(self, workspace: str, job_id: str) -> str:
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = conn.execute(
                "SELECT * FROM jobs WHERE id=? AND workspace=? AND kind='chat'", (job_id, workspace)
            ).fetchone()
            if not job:
                raise LookupError("Message not found.")
            if job["status"] in {"queued", "running"}:
                raise ValueError("This answer is already running.")
            payload = json.loads(job["payload"])
            conversation = payload.get("conversation_id")
            newer = conn.execute(
                "SELECT 1 FROM jobs WHERE workspace=? AND kind='chat' AND json_extract(payload,'$.conversation_id')=? AND created>?",
                (workspace, conversation, job["created"]),
            ).fetchone()
            if newer:
                raise ValueError("Ask this question again as a new message to keep later replies consistent.")
            conn.execute(
                "UPDATE jobs SET status='queued',result=NULL,error=NULL,updated=? WHERE id=?",
                (time.time(), job_id),
            )
            conn.execute("DELETE FROM events WHERE job=?", (job_id,))
        return conversation

    def job(self, workspace: str, job_id: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id=? AND workspace=?", (job_id, workspace)
            ).fetchone()
        if not row:
            return None
        value = dict(row)
        value["payload"] = json.loads(value["payload"])
        value["result"] = json.loads(value["result"]) if value["result"] else None
        return value

    def event(self, job: str, kind: str, agent: str, message: str, data: dict | None = None):
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO events(job,kind,agent,message,data,created) VALUES (?,?,?,?,?,?)",
                (job, kind, agent, message, json.dumps(data or {}), time.time()),
            )

    def events(self, job: str, after: int = 0) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE job=? AND id>? ORDER BY id", (job, after)
            ).fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def finish(self, job: str, result: Any = None, error: str | None = None):
        with self.connection() as conn:
            conn.execute(
                "UPDATE jobs SET status=?,result=?,error=?,updated=? WHERE id=?",
                (
                    "failed" if error else "completed",
                    json.dumps(result) if result is not None else None,
                    error,
                    time.time(),
                    job,
                ),
            )
            row = conn.execute(
                "SELECT workspace,payload FROM jobs WHERE id=? AND kind='chat'", (job,)
            ).fetchone()
            if row:
                payload = json.loads(row["payload"])
                conn.execute(
                    "UPDATE conversations SET updated=? WHERE id=? AND workspace=? AND profile=?",
                    (
                        time.time(),
                        payload.get("conversation_id"),
                        row["workspace"],
                        payload.get("profile_id"),
                    ),
                )

    def cached(self, key: str, ttl: int = 86400) -> Any | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT payload FROM cache WHERE key=? AND created>?", (key, time.time() - ttl)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def cache(self, key: str, payload: Any):
        with self.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, json.dumps(payload), time.time())
            )
