from copy import deepcopy

from api.analysis import family_comparison, methylation_summary
from api.combined_demo import ensure_combined_demo
from api.datasets import records
from api.demo_cases import load_cases
from api.methylation import clock_report, repeat_comparisons
from api.public_demo import seed_public_demo
from api.trait_catalog import assess_trait, heart_snapshot


def test_expanded_examples_have_actual_trait_calls_and_public_carrier_pair(store):
    seed_public_demo(store, "workspace")
    profiles = ensure_combined_demo(store, "workspace")
    assert len(profiles) == 10
    for key, call_count, observed in [("alex-v1", 22, 4), ("sam-v1", 26, 7)]:
        p = next(p for p in profiles if p.get("demo_persona_key") == key)
        result = assess_trait(store, "workspace", p["id"], heart_snapshot())
        assert result["uploaded_call_count"] == call_count
        assert result["observed_count"] == observed
        assert result["unresolved_count"] == 0
        assert len(records(store, "workspace", p["id"], "wearables")) == 90
    a, b = [
        next(p for p in profiles if p.get("public_dataset_key") == key)
        for key in ["family-na12043", "family-na20332"]
    ]
    result = family_comparison(store, "workspace", a["id"], b["id"])
    pah = next(c for c in result["conditions"] if c["gene"] == "PAH")
    assert pah["parent_a"]["genotype"] == pah["parent_b"]["genotype"] == "G/A"
    assert pah["affected_genotype_probability"] == 0.25
    assert pah["inheritance"] == {
        "two_reference": 0.25,
        "one_assessed_allele": 0.5,
        "two_assessed_alleles": 0.25,
    }
    # Other sites absent in this source must not be synthesized into reference calls.
    assert all(
        c["parent_a"]["status"] == c["parent_b"]["status"] == "unknown"
        for c in result["conditions"]
        if c["gene"] != "PAH"
    )
    before = {p["id"]: len(store.datasets("workspace", p["id"])) for p in profiles}
    assert ensure_combined_demo(store, "workspace") == profiles
    assert {p["id"]: len(store.datasets("workspace", p["id"])) for p in profiles} == before
    assert load_cases()["family_profiles"][0]["datasets"][0]["rows"][0]["quality"] is None


def test_real_same_donor_repeat_uses_reported_years_and_cohort_ranges(store):
    seed_public_demo(store, "workspace")
    profiles = ensure_combined_demo(store, "workspace")
    p = next(p for p in profiles if p.get("demo_scenario") == "repeat_methylation")
    result = methylation_summary(store, "workspace", p["id"])
    assert len(result["samples"]) == 2
    for sample in result["samples"]:
        report = sample["age_report"]
        assert report["status"] == "ready"
        assert report["present_sites"] == 71
        assert report["estimate_years"] is not None
        assert report["age_at_collection"] is None
        assert report["calendar_age_difference_years"] is None
        assert sample["metadata"]["collected_at"] == "Not reported"
        assert sample["metadata"]["subject_id"] == "GSE73115:Individual_1"
        assert report["age_range_at_collection"] in [[73, 82], [83, 92]]
    comparison = result["comparisons"][0]
    assert comparison["status"] == "descriptive_only"
    assert comparison["time_precision"] == "year"
    assert comparison["from"] == "1997" and comparison["to"] == "2007"
    assert comparison["elapsed_years"] == 10
    assert comparison["estimate_change_years"] is not None
    assert "not independently validated" in comparison["comparability_basis"]
    changed = deepcopy(result["samples"])
    changed[0]["metadata"]["subject_id"] = "a different donor"
    assert repeat_comparisons(changed)[0]["status"] == "blocked"


def test_cohort_age_range_is_not_accepted_as_an_unsourced_private_age():
    import json
    from pathlib import Path

    bundle = json.loads((Path(__file__).parents[1] / "api/repeat_demo/bundle.json").read_text())
    sample = bundle["datasets"][0]
    values = {p["cpg_id"]: p["beta"] for p in sample["rows"]}
    for fields in [
        {"provenance": "uploaded"},
        {"age_range_source": ""},
        {"age_range_at_collection": [18, 30]},
    ]:
        report = clock_report(values, {**sample["metadata"], **fields})
        assert report["status"] == "needs_data" and report["estimate_years"] is None


def test_profile_coverage_and_family_no_dna_guard(client):
    session = client.post("/api/session", json={"demo": True}).json()
    headers = {"Authorization": "Bearer " + session["token"]}
    profiles = client.get("/api/profiles", headers=headers).json()
    pm = next(p for p in profiles if p.get("public_dataset_key") == "pmdata_p01")
    a = next(p for p in profiles if p.get("demo_persona_key") == "alex-v1")
    assert pm["data_coverage"] == {"genetic_calls": 0, "wearable_records": 90, "methylation_samples": 0}
    assert a["data_coverage"]["genetic_calls"] == 22
    response = client.post(
        "/api/family-comparisons", headers=headers, json={"profile_a": a["id"], "profile_b": pm["id"]}
    )
    assert response.status_code == 422 and "Both profiles need genetic data" in response.json()["detail"]
