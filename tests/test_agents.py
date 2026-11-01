import json
from types import SimpleNamespace

import pytest

from api import agents
from api.agents import Dependencies, ReviewResult, SpecialistResult, answer_question, build_context
from api.demo import seed_demo
from api.models import Answer, Claim


class ScriptedAgent:
    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.prompts = []

    async def run(self, prompt, **kwargs):
        self.prompts.append(json.loads(prompt))
        return SimpleNamespace(output=self.outputs.pop(0))


@pytest.mark.asyncio
@pytest.mark.parametrize("final_approval", [True, False])
async def test_review_has_profile_context_and_unapproved_answers_are_withheld(
    store, monkeypatch, final_approval
):
    profile = seed_demo(store, "workspace")[0]
    store.config.anthropic_api_key = "test-only"
    job = store.new_job("workspace", "chat", {"profile_id": profile["id"]})
    specialist = SpecialistResult(summary="Limited evidence", claims=[], unknowns=[])
    draft = Answer(
        title="Draft", response="Draft conclusion", claims=[Claim(text="Association", evidence_ids=["gdf5"])]
    )
    revised = draft.model_copy(update={"response": "A supported association does not diagnose pain."})
    coordinator = ScriptedAgent(draft, revised)
    reviewer = ScriptedAgent(
        ReviewResult(approved=False, issues=["Remove an unsupported conclusion."]),
        ReviewResult(approved=final_approval, issues=[] if final_approval else ["Still unsupported."]),
    )
    monkeypatch.setattr(
        agents,
        "make_agents",
        lambda model: (ScriptedAgent(specialist), ScriptedAgent(specialist), coordinator, reviewer),
    )
    deps = Dependencies(store, "workspace", profile["id"], job)
    if final_approval:
        result = await answer_question(deps, "Could knee pain be genetic?")
        assert result["answer"]["response"] == revised.response
        assert result["answer"]["mode"] == "live"
    else:
        result = await answer_question(deps, "Could knee pain be genetic?")
        assert result["answer"]["mode"] == "evidence_only"
        assert "did not pass evidence review" in result["answer"]["notice"]
        assert result["answer"]["response"] != revised.response
    assert len(reviewer.prompts) == 2
    assert reviewer.prompts[0]["measured_context"]["profile"]["age"] == 31
    assert len(coordinator.prompts) == 2


@pytest.mark.asyncio
async def test_invalid_citation_is_revised_before_publication(store, monkeypatch):
    profile = seed_demo(store, "workspace")[0]
    store.config.anthropic_api_key = "test-only"
    job = store.new_job("workspace", "chat", {"profile_id": profile["id"]})
    specialist = SpecialistResult(summary="Limited evidence", claims=[], unknowns=[])
    draft = Answer(
        title="Draft",
        response="Unsupported draft",
        claims=[Claim(text="Association", evidence_ids=["made-up"])],
    )
    revised = draft.model_copy(
        update={
            "response": "A supported association does not diagnose pain.",
            "claims": [Claim(text="Association", evidence_ids=["gdf5"])],
        }
    )
    coordinator = ScriptedAgent(draft, revised)
    reviewer = ScriptedAgent(ReviewResult(approved=True, issues=[]))
    monkeypatch.setattr(
        agents,
        "make_agents",
        lambda model: (ScriptedAgent(specialist), ScriptedAgent(specialist), coordinator, reviewer),
    )
    result = await answer_question(
        Dependencies(store, "workspace", profile["id"], job), "Could knee pain be genetic?"
    )
    assert result["answer"]["mode"] == "live"
    assert result["answer"]["response"] == revised.response
    assert len(reviewer.prompts) == 1
    assert "unsupported evidence" in coordinator.prompts[1]["review_issues"][0]


@pytest.mark.asyncio
async def test_budget_limit_returns_explicit_library_answer_instead_of_losing_question(store, monkeypatch):
    from pydantic_ai.exceptions import UsageLimitExceeded

    class LimitedAgent:
        async def run(self, *args, **kwargs):
            raise UsageLimitExceeded("Test budget exhausted")

    profile = seed_demo(store, "workspace")[0]
    store.config.anthropic_api_key = "test-only"
    job = store.new_job("workspace", "chat", {"profile_id": profile["id"]})
    monkeypatch.setattr(agents, "make_agents", lambda model: (LimitedAgent(), LimitedAgent(), None, None))
    result = await answer_question(
        Dependencies(store, "workspace", profile["id"], job), "Could knee pain be genetic?"
    )
    assert result["answer"]["mode"] == "evidence_only"
    assert "budget" in result["answer"]["notice"]
    assert "not establish" in result["answer"]["response"]


def test_chat_only_receives_completed_molecular_runs_for_active_profile(store):
    profiles = seed_demo(store, "workspace")
    other = seed_demo(store, "other-workspace")[0]
    for workspace, profile in [("workspace", p) for p in profiles] + [("other-workspace", other)]:
        job = store.new_job(workspace, "investigation", {"profile_id": profile["id"]})
        store.finish(
            job,
            {
                "provider": "alphagenome",
                "context_name": profile["name"],
                "tracks": [],
                "limitations": ["Research only."],
            },
        )
    chat = store.new_job("workspace", "chat", {"profile_id": profiles[0]["id"]})
    deps = Dependencies(store, "workspace", profiles[0]["id"], chat)
    context = build_context(deps, "Explain my molecular investigation")
    assert len(context["completed_investigations"]) == 1
    assert context["completed_investigations"][0]["context_name"] == profiles[0]["name"]
    assert len([e for e in deps.evidence.values() if e.category == "prediction"]) == 1


def test_repeated_cached_runs_do_not_duplicate_prediction_evidence(store):
    profile = seed_demo(store, "workspace")[0]
    for _ in range(3):
        job = store.new_job("workspace", "investigation", {"profile_id": profile["id"]})
        store.finish(
            job,
            {
                "provider": "alphagenome",
                "context_name": "HepG2",
                "request_hash": "same-request",
                "execution": "cached",
                "tracks": [],
                "limitations": [],
            },
        )
    chat = store.new_job("workspace", "chat", {"profile_id": profile["id"]})
    deps = Dependencies(store, "workspace", profile["id"], chat)
    context = build_context(deps, "Explain the prediction")
    assert len(context["completed_investigations"]) == 1
    assert len([e for e in deps.evidence.values() if e.category == "prediction"]) == 1
