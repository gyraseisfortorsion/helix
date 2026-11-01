import pytest
from conftest import demo_session

from api.eligibility import investigation_eligibility
from api.science import resolve_variant


@pytest.mark.parametrize(
    "a,b,ref,eligible,status",
    [
        ("G", "G", "G", False, "reference_only"),
        ("G", "A", "G", True, "ready"),
        ("A", "A", "G", True, "ready"),
        ("A", "T", "G", False, "multiple_alternatives"),
        (None, None, "G", False, "missing"),
        ("G", "GA", "G", False, "unsupported"),
        ("G", "G", None, True, "reference_check"),
    ],
)
def test_call_eligibility_distinguishes_copies_from_different_alternatives(a, b, ref, eligible, status):
    value = investigation_eligibility({"rsid": "rs1", "allele1": a, "allele2": b, "ref": ref})
    assert value["eligible"] is eligible
    assert value["status"] == status


def test_reference_only_call_explained_before_queueing_model_work(client):
    session, headers = demo_session(client)
    profile = session["profiles"][0]["id"]
    variants = client.get(f"/api/profiles/{profile}/variants", headers=headers).json()
    pah = next(v for v in variants if v["rsid"] == "rs5030858")
    assert pah["investigation"]["status"] == "reference_only"
    response = client.post(
        "/api/investigations", headers=headers, json={"profile_id": profile, "variant_id": "rs5030858"}
    )
    assert response.status_code == 422
    assert "G/G" in response.json()["detail"]
    assert "No alternative allele was observed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_conflicting_calls_are_not_arbitrarily_selected(store, monkeypatch):
    from api import science

    base = {
        "rsid": "rs1",
        "chrom": "20",
        "pos": 100,
        "build": "GRCh38",
        "ref": "G",
        "allele1": "G",
        "allele2": "A",
    }
    monkeypatch.setattr(
        science, "investigation_calls", lambda *args, **kwargs: [base, {**base, "allele2": "G"}]
    )
    with pytest.raises(ValueError, match="conflicting calls"):
        await resolve_variant(store, "workspace", "profile", "rs1")


def test_no_rsid_snv_uses_coordinates_but_requires_reference_and_supported_assembly():
    base = {
        "rsid": None,
        "build": "GRCh38",
        "chrom": "20",
        "pos": 35430145,
        "ref": "C",
        "allele1": "C",
        "allele2": "G",
    }
    assert investigation_eligibility(base)["eligible"]
    assert investigation_eligibility({**base, "ref": None})["status"] == "reference_missing"
    assert investigation_eligibility({**base, "build": "GRCh37"})["status"] == "coordinate_unsupported"


def test_public_coordinate_selection_requires_the_observed_alternative(client):
    session = client.post("/api/session", json={"demo": True}).json()
    headers = {"Authorization": "Bearer " + session["token"]}
    profile = session["profiles"][0]["id"]
    variants = client.get(f"/api/profiles/{profile}/variants", headers=headers).json()
    unnamed = next(v for v in variants if v["pos"] == 35430145)
    assert unnamed["rsid"] is None
    assert unnamed["investigation"]["eligible"]
    assert unnamed["investigation_id"] == "GRCh38:20:35430145:C:G"
    good = client.post(
        "/api/investigations",
        headers=headers,
        json={"profile_id": profile, "variant_id": unnamed["investigation_id"]},
    )
    assert good.status_code == 202
    for requested in [
        "GRCh38:20:35430145:C:T",
        "GRCh38:20:35430145:C:C",
        "GRCh37:20:35430145:C:G",
        "GRCh38:20:1:C:G",
    ]:
        response = client.post(
            "/api/investigations", headers=headers, json={"profile_id": profile, "variant_id": requested}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("reference", ["C", "A"])
async def test_coordinate_variant_checks_reference_before_predicting(store, monkeypatch, reference):
    from api import science
    from api.public_demo import seed_public_demo

    profile = seed_public_demo(store, "workspace")[0]
    calls = []

    async def fetch(chrom, pos, length):
        calls.append((chrom, pos, length))
        return reference, pos

    monkeypatch.setattr(science, "reference_window", fetch)
    if reference != "C":
        with pytest.raises(ValueError, match="Reference allele mismatch"):
            await resolve_variant(store, "workspace", profile["id"], "GRCh38:20:35430145:C:G")
    else:
        variant = await resolve_variant(store, "workspace", profile["id"], "GRCh38:20:35430145:C:G")
        assert variant["rsid"] is None
        assert (variant["chrom"], variant["pos"], variant["ref"], variant["alt"]) == (
            "20",
            35430145,
            "C",
            "G",
        )
    assert calls == [("20", 35430145, 1)]


@pytest.mark.asyncio
async def test_coordinate_conflicts_are_retained_not_filtered_out(store, monkeypatch):
    from api import datasets

    base = {
        "rsid": None,
        "chrom": "20",
        "pos": 100,
        "build": "GRCh38",
        "ref": "C",
        "allele1": "C",
        "allele2": "G",
    }
    monkeypatch.setattr(datasets, "find_variant", lambda *args, **kwargs: [base, {**base, "allele2": "C"}])
    with pytest.raises(ValueError, match="conflicting calls"):
        await resolve_variant(store, "workspace", "profile", "GRCh38:20:100:C:G")
