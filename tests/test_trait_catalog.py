import json
from types import SimpleNamespace

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import respx
from test_api import wait_job

from api import agents
from api.agents import Dependencies, ReviewResult, SpecialistResult, answer_question, investigate_trait_data
from api.datasets import GENETIC_SCHEMA
from api.models import Answer, Claim
from api.trait_catalog import BASE, assess_trait, discover_catalog, heart_snapshot, relevant_associations


def association(**updates):
    return {
        "association_id": 123,
        "p_value": 1e-12,
        "snp_allele": [{"rs_id": "rs123", "effect_allele": "A"}],
        "locations": ["1:100"],
        "reported_trait": ["Resting heart rate"],
        "mapped_genes": ["TEST"],
        "accession_id": "GCST123",
        "pubmed_id": "12345",
        "beta": "0.1 unit increase",
        **updates,
    }


def catalog():
    return {
        "status": "available",
        "trait": "heart rate",
        "ontology_id": "OBA_1001087",
        "associations": relevant_associations([association()], "heart rate"),
        "retrieval": "test_public_catalog",
        "retrieved_at": "2026-11-01",
        "source_url": BASE + "/associations",
        "associations_retrieved": 1,
        "catalog_association_count": 1,
    }


def attach_calls(store, tmp_path, rows, workspace="workspace"):
    profile = store.create_profile(
        workspace,
        {
            "name": "Software test profile",
            "external_analysis_consent": True,
            "timezone": "UTC",
            "provenance": "synthetic",
        },
    )
    path = tmp_path / (profile["id"] + ".parquet")
    pq.write_table(pa.Table.from_pylist(rows, schema=GENETIC_SCHEMA), path)
    store.add_dataset(
        workspace,
        profile["id"],
        "genetics",
        "test.vcf",
        path,
        {"provenance": "synthetic"},
        {"accepted": len(rows), "warnings": []},
    )
    return profile


def call(**updates):
    return {
        "chrom": "1",
        "pos": 100,
        "ref": "G",
        "alt": "A",
        "allele1": "G",
        "allele2": "A",
        "genotype": "0/1",
        "rsid": "rs123",
        "build": "GRCh38",
        **updates,
    }


@pytest.mark.parametrize(
    "updates",
    [
        {"reported_trait": ["Heart rate response to exercise"]},
        {"reported_trait": ["fetal heart rate"]},
        {"reported_trait": ["heart rate (HR, minimum, inv-normal transformed)"]},
        {"p_value": 0.01},
        {"multi_snp_haplotype": True},
        {"snp_interaction": True},
        {"locations": []},
        {"snp_allele": [{"rs_id": "rs123-rs456"}]},
    ],
)
def test_trait_filter_does_not_substitute_other_phenotypes_or_unsupported_records(updates):
    assert relevant_associations([association(**updates)], "heart rate") == []


def test_genotype_join_handles_unnamed_calls_conflicts_and_assembly(store, tmp_path):
    profile = attach_calls(store, tmp_path, [call(rsid=None), call(rsid=None)])
    result = assess_trait(store, "workspace", profile["id"], catalog())
    assert result["uploaded_call_count"] == 1
    assert result["observed_count"] == 1
    assert result["findings"][0]["genotype"] == "A/G"
    assert "no individual heart-rate direction" in result["findings"][0]["interpretation"]
    other = attach_calls(store, tmp_path, [call(allele1="A", allele2="A"), call()])
    conflicting = assess_trait(store, "workspace", other["id"], catalog())
    assert conflicting["unresolved_count"] == 1 and conflicting["observed_count"] == 0
    for updates in [{"allele1": None}, {"pos": 101}, {"build": "GRCh37"}]:
        p = attach_calls(store, tmp_path, [call(**updates)])
        actual = assess_trait(store, "workspace", p["id"], catalog())
        assert actual["observed_count"] == 0 and actual["unresolved_count"] == 1


def test_trait_join_does_not_read_another_profile_or_assume_reference(store, tmp_path):
    yes = attach_calls(store, tmp_path, [call()])
    no = attach_calls(store, tmp_path, [call(rsid="rs456", pos=200)])
    result = assess_trait(store, "workspace", no["id"], catalog())
    assert result["observed_count"] == 0 and result["not_observed_count"] == 1
    assert "unknown, not reference or negative" in result["scope"]
    assert assess_trait(store, "workspace", yes["id"], catalog())["observed_count"] == 1
    assert assess_trait(store, "other-workspace", yes["id"], catalog())["uploaded_call_count"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_live_discovery_uses_exact_ontology_and_caches_only_public_data(store):
    trait = respx.get(BASE + "/efo-traits").mock(
        return_value=httpx.Response(
            200, json={"_embedded": {"efo_traits": [{"efo_trait": "heart rate", "efo_id": "OBA_1001087"}]}}
        )
    )
    rows = respx.get(BASE + "/associations").mock(
        return_value=httpx.Response(
            200, json={"_embedded": {"associations": [association()]}, "page": {"totalElements": 1000}}
        )
    )
    result = await discover_catalog(store, "resting heart rate", live=True)
    assert result["retrieval"] == "live_public_catalog" and result["truncated"]
    assert rows.calls[0].request.url.params["efo_id"] == "OBA_1001087"
    assert rows.calls[0].request.url.params["sort"] == "p_value"
    assert rows.calls[0].request.url.params["show_child_trait"] == "false"
    assert (await discover_catalog(store, "heart rate", live=True))["retrieval"] == "cached_public_catalog"
    assert trait.call_count == rows.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_advertised_but_missing_results_fall_back_explicitly_instead_of_negative(store):
    respx.get(BASE + "/efo-traits").mock(
        return_value=httpx.Response(
            200, json={"_embedded": {"efo_traits": [{"efo_trait": "heart rate", "efo_id": "OBA_1001087"}]}}
        )
    )
    respx.get(BASE + "/associations").mock(
        return_value=httpx.Response(200, json={"page": {"totalElements": 1000}})
    )
    result = await discover_catalog(store, "heart rate", live=True)
    assert result["retrieval"] == "bundled_public_snapshot"
    assert result["associations"] and result["live_notice"]


@pytest.mark.asyncio
@respx.mock
async def test_trait_ambiguity_does_not_turn_into_an_unrelated_lookup(store):
    respx.get(BASE + "/efo-traits").mock(
        return_value=httpx.Response(
            200, json={"_embedded": {"efo_traits": [{"efo_trait": "exercise response", "efo_id": "X"}]}}
        )
    )
    result = await discover_catalog(store, "ambiguous trait", live=True)
    assert result["status"] == "needs_trait_selection"
    assert "not substituted" in result["reason"]


@pytest.mark.asyncio
@respx.mock
async def test_no_external_requests_without_consent_and_repeated_tools_reuse_check(store, tmp_path):
    # No external requests are mocked: respx fails this test if one is attempted.
    profile = attach_calls(store, tmp_path, [call()])
    with store.connection() as conn:
        p = dict(profile)
        p.pop("id")
        p["external_analysis_consent"] = False
        conn.execute("UPDATE profiles SET payload=? WHERE id=?", (json.dumps(p), profile["id"]))
    job = store.new_job("workspace", "chat", {"profile_id": profile["id"]})
    deps = Dependencies(store, "workspace", profile["id"], job)
    first = await investigate_trait_data(deps, "resting heart rate", live=True)
    assert first["retrieval"] == "bundled_public_snapshot"
    count = len(store.events(job))
    assert await investigate_trait_data(deps, "pulse", live=True) is first
    assert len(store.events(job)) == count


def test_heart_question_runs_the_local_check_before_evidence_only_answer(client):
    session = client.post("/api/session", json={"demo": True}).json()
    headers = {"Authorization": "Bearer " + session["token"]}
    job = client.post(
        "/api/messages",
        headers=headers,
        json={
            "profile_id": session["profiles"][0]["id"],
            "question": "why is my resting heart rate so low, is it connected to genes?",
        },
    ).json()["job_id"]
    result = wait_job(client, job, headers)
    check = result["result"]["trait_checks"]["heart rate"]
    assert check["status"] == "checked" and check["uploaded_call_count"] == 22
    assert check["variants_checked"] == len({r["rsid"] for r in heart_snapshot()["associations"]})
    assert check["observed_count"] == 4
    answer = result["result"]["answer"]
    assert f"I checked {check['variants_checked']} published heart rate" in answer["response"]
    assert "not a negative genetic result" in answer["response"]
    assert "In Alex" not in answer["response"] and "this app" not in answer["response"]
    assert any(e["id"] == "trait-check-heart-rate" for e in answer["evidence"])
    events = client.app.state.store.events(job)
    assert any(e["agent"] == "Genomics" and "Checking" not in e["message"] for e in events)


@pytest.mark.asyncio
async def test_required_check_reaches_specialists_coordinator_and_reviewer(store, monkeypatch):
    from api.demo import seed_demo

    profile = seed_demo(store, "workspace")[0]
    store.config.anthropic_api_key = "test-only"
    job = store.new_job("workspace", "chat", {"profile_id": profile["id"]})

    async def offline_catalog(*args, **kwargs):
        return heart_snapshot()

    monkeypatch.setattr(agents, "discover_catalog", offline_catalog)

    class Scripted:
        def __init__(self, output):
            self.output = output
            self.prompts = []

        async def run(self, prompt, **kwargs):
            self.prompts.append(json.loads(prompt))
            return SimpleNamespace(output=self.output)

    specialists = [
        Scripted(SpecialistResult(summary="Checked calls", claims=[], unknowns=[])) for _ in range(2)
    ]
    coordinator = Scripted(
        Answer(
            title="Your heart rate",
            response="I checked your supplied calls.",
            claims=[Claim(text="Limited lookup", evidence_ids=["trait-check-heart-rate"])],
        )
    )
    reviewer = Scripted(ReviewResult(approved=True, issues=[]))
    monkeypatch.setattr(agents, "make_agents", lambda model: (*specialists, coordinator, reviewer))
    answer = await answer_question(
        Dependencies(store, "workspace", profile["id"], job), "Can my genes explain my resting heart rate?"
    )
    assert answer["answer"]["mode"] == "live"
    assert specialists[0].prompts[0]["trait_checks"]["heart rate"]["status"] == "checked"
    assert coordinator.prompts[0]["context"]["trait_checks"]["heart rate"]["status"] == "checked"
    assert reviewer.prompts[0]["measured_context"]["trait_checks"]["heart rate"]["status"] == "checked"
