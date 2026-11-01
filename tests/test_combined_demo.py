import json

from api.agents import Dependencies, build_context, evidence_answer
from api.combined_demo import ensure_combined_demo
from api.datasets import find_variant, records
from api.demo_cases import load_cases
from api.public_demo import load_bundle, seed_public_demo


def test_combined_demo_preserves_public_values_and_original_identities(store):
    originals = seed_public_demo(store, "workspace")
    profiles = ensure_combined_demo(store, "workspace")
    bundle, _ = load_bundle()
    for persona in profiles[:2]:
        assert persona["provenance"] == "composite_demo"
        assert persona["age"] in {30, 31}
        assert "Fictional demo scenario" in persona["history"]
        assert persona["demo_scenario_date"] == "2020-03-31"
        source = next(p for p in bundle["profiles"] if p["key"] == persona["genetic_sample_key"])
        calls = records(store, "workspace", persona["id"], "genetics")
        assert {json.dumps(r, sort_keys=True) for r in calls} == {
            json.dumps(r, sort_keys=True)
            for r in [
                *source["datasets"][0]["rows"],
                *load_cases()["genetics_supplements"][persona["genetic_sample_key"]]["rows"],
            ]
        }
        assert len(records(store, "workspace", persona["id"], "wearables")) == 90
        assert store.datasets("workspace", persona["id"], "methylation") == []
    for original in originals:
        assert store.profile("workspace", original["id"]) == original
        kinds = {d["kind"] for d in store.datasets("workspace", original["id"])}
        assert kinds == ({"wearables"} if original["public_dataset_key"] == "pmdata_p01" else {"genetics"})
    assert ensure_combined_demo(store, "workspace") == profiles
    assert len(store.profiles("workspace")) == 10
    assert all(len(store.datasets("workspace", p["id"])) == 3 for p in profiles[:2])


def test_context_distinguishes_demo_persona_from_source_reference(store):
    originals = seed_public_demo(store, "workspace")
    alex = ensure_combined_demo(store, "workspace")[0]
    job = store.new_job("workspace", "chat", {"profile_id": alex["id"]})
    deps = Dependencies(store, "workspace", alex["id"], job)
    context = build_context(deps, "Could my knee pain be genetic?")
    assert context["data_identity"]["mode"] == "composite_demo"
    assert context["data_identity"]["source_identity_matched"] is False
    assert context["wearable_period"] == {"start": "2020-03-01", "end": "2020-03-31"}
    assert set(context["wearables"]) == {"steps", "sleep_duration", "resting_heart_rate"}
    assert context["profile"]["age"] == 31
    assert context["variants"]["rs143383"]
    assert context["genetic_coverage"]["available_calls"] == 22
    assert context["genetic_coverage"]["question_selected_calls"] == 1
    heart = build_context(Dependencies(store, "workspace", alex["id"], job), "Can DNA explain my heart rate?")
    assert heart["genetic_coverage"]["available_calls"] == 22
    assert heart["genetic_coverage"]["question_selected_calls"] == 0
    assert heart["datasets"] and heart["data_identity"]["mode"] == "composite_demo"
    assert deps.evidence["your_genetics"].provenance == "public_reference"
    assert "independent of the DNA donor" in deps.evidence["your_wearables"].context
    answer = evidence_answer(context, deps.evidence)
    assert "Your data includes a call" in answer.response
    assert "Alex Morgan's demo profile" not in answer.response
    assert "2020-03-31" in answer.response and "steps" in answer.response
    assert "not show that activity or this variant caused" in answer.response
    source_job = store.new_job("workspace", "chat", {"profile_id": originals[0]["id"]})
    source = build_context(Dependencies(store, "workspace", originals[0]["id"], source_job), "Knee pain")
    assert source["data_identity"]["mode"] == "public_reference"
    assert source["profile"]["age"] is None and not source["wearables"]


def test_existing_public_sessions_get_personas_without_losing_chats(client):
    store = client.app.state.store
    token, workspace = store.session(True)
    source = seed_public_demo(store, workspace)[0]
    job, chat = store.queue_chat(workspace, source["id"], "Old source chat", None)
    headers = {"Authorization": "Bearer " + token}
    response = client.post("/api/demo/combined-profiles", headers=headers)
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) == 10
    assert profiles[0]["demo_persona_key"] == "alex-v1"
    assert len(client.post("/api/demo/combined-profiles", headers=headers).json()) == 10
    assert store.conversation(workspace, chat)["profile"] == source["id"]
    assert store.job(workspace, job) is not None
    assert client.get("/api/profiles", headers=headers).json() == profiles


def test_persona_methylation_is_optional_and_only_matches_its_genetic_source(client):
    session = client.post("/api/session", json={"demo": True}).json()
    alex, sam = session["profiles"][:2]
    headers = {"Authorization": "Bearer " + session["token"]}
    path = f"/api/profiles/{alex['id']}"
    assert client.get(path + "/methylation", headers=headers).json()["samples"] == []
    response = client.post(path + "/demo-methylation", headers=headers)
    assert response.status_code == 200
    assert response.json()["samples"][0]["metadata"]["sample_id"] == "HG002/GM24385"
    assert client.post(f"/api/profiles/{sam['id']}/demo-methylation", headers=headers).status_code == 403
    assert find_variant(client.app.state.store, session["workspace_id"], alex["id"], rsid="rs143383")
    private = client.post("/api/session", json={"demo": False}).json()
    assert (
        client.post(
            "/api/demo/combined-profiles", headers={"Authorization": "Bearer " + private["token"]}
        ).status_code
        == 403
    )
