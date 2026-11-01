import time

from conftest import demo_session


def wait_job(client, job, headers):
    for _ in range(100):
        result = client.get(f"/api/jobs/{job}", headers=headers).json()
        if result["status"] in {"completed", "failed"}:
            return result
        time.sleep(0.03)
    raise AssertionError("Worker did not finish")


def test_dna_only_demo_has_no_methylation_requirement(client):
    session, headers = demo_session(client)
    assert client.get("/api/health").json()["methylation_required"] is False
    profile = session["profiles"][0]["id"]
    data = client.get(f"/api/profiles/{profile}/datasets", headers=headers).json()
    assert {d["kind"] for d in data} == {"genetics", "wearables"}
    assert client.get(f"/api/profiles/{profile}/methylation", headers=headers).json()["samples"] == []


def test_workspace_isolation_includes_profiles_jobs_and_artifacts(client):
    a, ha = demo_session(client)
    _, hb = demo_session(client)
    profile = a["profiles"][0]["id"]
    assert client.get(f"/api/profiles/{profile}/variants", headers=hb).status_code == 404
    job = client.post(
        "/api/messages", headers=ha, json={"profile_id": profile, "question": "My knee hurts, is it genetic?"}
    ).json()["job_id"]
    assert client.get(f"/api/jobs/{job}", headers=hb).status_code == 404
    assert client.get(f"/api/jobs/{job}/events", headers=hb).status_code == 404
    assert client.get(f"/api/jobs/{job}/export", headers=hb).status_code == 404


def test_evidence_only_answer_is_reviewable_and_does_not_claim_live_agents(client):
    session, headers = demo_session(client)
    job = client.post(
        "/api/messages",
        headers=headers,
        json={"profile_id": session["profiles"][0]["id"], "question": "My knee hurts, is it genetic?"},
    ).json()["job_id"]
    result = wait_job(client, job, headers)
    assert result["status"] == "completed", result
    answer = result["result"]["answer"]
    assert answer["mode"] == "evidence_only"
    assert "does not establish" in answer["response"]
    assert answer["unknowns"]
    evidence_ids = {e["id"] for e in answer["evidence"]}
    assert all(set(c["evidence_ids"]).issubset(evidence_ids) for c in answer["claims"])
    assert any(e["provenance"] == "synthetic" for e in answer["evidence"])


def test_private_upload_end_to_end_without_methylation(client):
    session = client.post("/api/session", json={"demo": False}).json()
    headers = {"Authorization": "Bearer " + session["token"]}
    profile = client.post("/api/profiles", headers=headers, json={"name": "My profile"}).json()
    assert not profile["external_analysis_consent"]
    content = client.get("/api/templates/genetics").text
    uploaded = client.post(
        f"/api/profiles/{profile['id']}/datasets",
        headers=headers,
        data={"kind": "genetics", "metadata": '{"build":"GRCh38"}'},
        files={"file": ("calls.vcf", content)},
    )
    result = wait_job(client, uploaded.json()["job_id"], headers)
    assert result["status"] == "completed", result
    calls = client.get(f"/api/profiles/{profile['id']}/variants", headers=headers).json()
    assert calls[0]["allele2"] == "A"
    assert client.get(f"/api/profiles/{profile['id']}/methylation", headers=headers).json()["samples"] == []


def test_missing_molecular_key_returns_explicit_failure(client):
    session, headers = demo_session(client)
    response = client.post(
        "/api/investigations",
        headers=headers,
        json={"profile_id": session["profiles"][0]["id"], "variant_id": "rs143383"},
    )
    result = wait_job(client, response.json()["job_id"], headers)
    assert result["status"] == "failed"
    assert "ALPHAGENOME_API_KEY" in result["error"]
    assert result["result"] is None


def test_profile_deletion_removes_datasets_and_results(client):
    session, headers = demo_session(client)
    profile = session["profiles"][0]["id"]
    assert client.delete(f"/api/profiles/{profile}", headers=headers).status_code == 204
    assert client.get(f"/api/profiles/{profile}/datasets", headers=headers).status_code == 404


def test_synthetic_methylation_only_attaches_to_synthetic_profile(client):
    session = client.post("/api/session", json={"demo": False}).json()
    headers = {"Authorization": "Bearer " + session["token"]}
    profile = client.post("/api/profiles", headers=headers, json={"name": "Real profile"}).json()
    assert client.post(f"/api/profiles/{profile['id']}/demo-methylation", headers=headers).status_code == 403
