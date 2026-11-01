import asyncio
import json

import pytest
from conftest import demo_session
from fastapi.testclient import TestClient
from test_api import wait_job

from api.agents import Dependencies, build_context
from api.demo import seed_demo
from api.main import create_app
from api.models import Answer, Claim, EvidenceRecord
from api.store import Store
from api.worker import claim_next, loop


def test_multiple_chats_keep_messages_and_restore_after_app_restart(client):
    session, headers = demo_session(client)
    profile = session["profiles"][0]["id"]
    first = client.post(
        "/api/messages",
        headers=headers,
        json={"profile_id": profile, "question": "Could my knee pain be genetic?"},
    ).json()
    assert wait_job(client, first["job_id"], headers)["status"] == "completed"
    second = client.post(
        "/api/messages",
        headers=headers,
        json={
            "profile_id": profile,
            "conversation_id": first["conversation_id"],
            "question": "Explain the knee evidence",
        },
    ).json()
    assert wait_job(client, second["job_id"], headers)["status"] == "completed"
    fresh = client.post(f"/api/profiles/{profile}/conversations", headers=headers, json={}).json()
    assert fresh["id"] != first["conversation_id"]
    assert len(client.get(f"/api/profiles/{profile}/conversations", headers=headers).json()) == 2
    with TestClient(create_app(client.app.state.store.config, embedded_worker=False)) as restarted:
        history = restarted.get("/api/conversations/" + first["conversation_id"], headers=headers).json()
        assert [m["question"] for m in history["messages"]] == [
            "Could my knee pain be genetic?",
            "Explain the knee evidence",
        ]
        assert all(m["answer"]["mode"] == "evidence_only" for m in history["messages"])
        assert restarted.get("/api/conversations/" + fresh["id"], headers=headers).json()["messages"] == []


def test_chat_ownership_is_scoped_to_workspace_and_profile(client):
    a, ha = demo_session(client)
    _, hb = demo_session(client)
    p, other = [x["id"] for x in a["profiles"]]
    result = client.post(
        "/api/messages", headers=ha, json={"profile_id": p, "question": "Knee genetics"}
    ).json()
    assert wait_job(client, result["job_id"], ha)["status"] == "completed"
    assert client.get("/api/conversations/" + result["conversation_id"], headers=hb).status_code == 404
    assert (
        client.post(
            "/api/messages",
            headers=ha,
            json={
                "profile_id": other,
                "conversation_id": result["conversation_id"],
                "question": "Cross-profile injection",
            },
        ).status_code
        == 404
    )
    assert client.post(f"/api/messages/{result['job_id']}/retry", headers=hb).status_code == 404


def test_retry_keeps_one_message_and_prevents_parallel_or_stale_replies(store):
    profile = seed_demo(store, "workspace")[0]
    job, chat = store.queue_chat("workspace", profile["id"], "Knee genetics", None)
    with pytest.raises(ValueError, match="still answering"):
        store.queue_chat("workspace", profile["id"], "Duplicate", chat)
    store.finish(job, error="Temporary failure")
    assert store.retry_chat("workspace", job) == chat
    history = store.conversation_messages("workspace", chat)
    assert len(history["messages"]) == 1
    assert history["messages"][0]["status"] == "queued"
    store.finish(job, {"answer": Answer(title="Done", response="Supported").model_dump()})
    store.queue_chat("workspace", profile["id"], "A later question", chat)
    with pytest.raises(ValueError, match="later replies"):
        store.retry_chat("workspace", job)


def test_legacy_messages_migrate_without_merging_workspace_or_profile(store):
    a, b = seed_demo(store, "one")
    other = seed_demo(store, "two")[0]
    ids = []
    for workspace, profile, question in [
        ("one", a, "First"),
        ("one", a, "Second"),
        ("one", b, "Other profile"),
        ("two", other, "Other workspace"),
    ]:
        job = store.new_job(
            workspace,
            "chat",
            {"profile_id": profile["id"], "conversation_id": "same-legacy-id", "question": question},
        )
        store.finish(job, {"answer": Answer(title="Done", response="Supported").model_dump()})
        ids.append((workspace, job))
    restored = Store(store.config)
    chats = [restored.job(w, j)["payload"]["conversation_id"] for w, j in ids]
    assert chats[0] == chats[1]
    assert len(set(chats)) == 3
    assert len(restored.conversation_messages("one", chats[0])["messages"]) == 2
    assert restored.conversation("two", chats[0]) is None


def test_memory_only_uses_this_chat_and_bounds_old_evidence(store):
    profile = seed_demo(store, "workspace")[0]
    job, first = store.queue_chat("workspace", profile["id"], "First knee question", None)
    evidence = [
        EvidenceRecord(id=f"paper-{i}", category="experiment", title=f"Study {i}", summary="x" * 30_000)
        for i in range(30)
    ]
    answer = Answer(
        title="Long answer",
        response="Earlier answer " * 1000,
        claims=[Claim(text="Supported", evidence_ids=[e.id for e in evidence])],
        evidence=evidence,
    )
    store.finish(job, {"answer": answer.model_dump()})
    unrelated, _ = store.queue_chat("workspace", profile["id"], "Unrelated topic", None)
    store.finish(unrelated, {"answer": Answer(title="Other", response="SECRET OTHER CHAT").model_dump()})
    current, _ = store.queue_chat("workspace", profile["id"], "Explain knee genetics", first)
    context = build_context(Dependencies(store, "workspace", profile["id"], current), "Explain knee genetics")
    assert len(context["conversation_history"]) == 1
    assert "SECRET OTHER CHAT" not in json.dumps(context)
    assert len(json.dumps(context)) < 20_000
    assert len(context["conversation_history"][0]["answer"]) < 1100


@pytest.mark.asyncio
async def test_interrupted_worker_run_is_retryable_not_stuck(store):
    profile = seed_demo(store, "workspace")[0]
    job, _ = store.queue_chat("workspace", profile["id"], "Knee question", None)
    assert claim_next(store)["id"] == job
    stop = asyncio.Event()
    stop.set()
    await loop(store, stop)
    assert store.job("workspace", job)["status"] == "failed"
    assert "server restarted" in store.job("workspace", job)["error"].lower()
    store.retry_chat("workspace", job)
    assert store.job("workspace", job)["status"] == "queued"
