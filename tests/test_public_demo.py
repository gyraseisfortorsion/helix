import hashlib

from api.datasets import find_variant
from api.public_demo import ROOT, load_bundle, seed_public_demo


def test_public_snapshot_hash_identity_and_no_cross_person_merging(store):
    bundle, manifest = load_bundle()
    assert hashlib.sha256((ROOT / "bundle.json").read_bytes()).hexdigest() == manifest["bundle_sha256"]
    profiles = seed_public_demo(store, "workspace")
    assert [p["public_dataset_key"] for p in profiles] == ["hg002", "hg003", "hg004", "pmdata_p01"]
    for profile in profiles:
        assert profile["age"] is None
        assert profile["provenance"] == "public_reference"
        kinds = {d["kind"] for d in store.datasets("workspace", profile["id"])}
        assert kinds == ({"wearables"} if profile["public_dataset_key"] == "pmdata_p01" else {"genetics"})
    call = find_variant(store, "workspace", profiles[0]["id"], rsid="rs143383")[0]
    assert (call["allele1"], call["allele2"], call["quality"]) == ("G", "A", 50)
    assert not find_variant(store, "workspace", profiles[0]["id"], rsid="rs75527207")
    assert len(bundle["profiles"][0]["datasets"][0]["rows"]) == 18


def test_default_session_uses_public_data_and_only_hg002_gets_its_methylation(client):
    session = client.post("/api/session", json={"demo": True}).json()
    assert session["demo_source"] == "public"
    headers = {"Authorization": "Bearer " + session["token"]}
    hg002, father, _, wearable = [
        p
        for p in session["profiles"]
        if p.get("public_dataset_key") in {"hg002", "hg003", "hg004", "pmdata_p01"}
    ]
    path = f"/api/profiles/{hg002['id']}"
    assert client.get(path + "/methylation", headers=headers).json()["samples"] == []
    result = client.post(path + "/demo-methylation", headers=headers)
    assert result.status_code == 200
    sample = result.json()["samples"][0]
    assert sample["metadata"]["sample_id"] == "HG002/GM24385"
    assert sample["metadata"]["collected_at"] == "Not reported"
    assert sample["report"]["accepted"] == 407
    assert all(0 <= p["beta"] <= 1 for p in sample["probes"])
    assert client.post(f"/api/profiles/{father['id']}/demo-methylation", headers=headers).status_code == 403
    assert client.post(f"/api/profiles/{wearable['id']}/demo-methylation", headers=headers).status_code == 403
    repeated = client.post(path + "/demo-methylation", headers=headers).json()
    assert len(repeated["samples"]) == 1


def test_public_bismark_beta_uses_measured_counts_and_no_zero_depth_sites():
    bundle, _ = load_bundle()
    for site in bundle["optional_methylation"]["rows"]:
        assert site["coverage"] >= 10
        assert site["coverage"] == site["methylated_reads"] + site["unmethylated_reads"]
        assert site["beta"] == site["methylated_reads"] / site["coverage"]
        assert site["cpg_id"] == f"chr20:{site['pos']}"
        assert 35433001 <= site["pos"] <= 35443000
