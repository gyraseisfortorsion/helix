import base64
import io
import json

import httpx
import numpy as np
import pytest
import respx

from api.agents import validate_claims
from api.models import Answer, Claim
from api.science import evo2_sequence_score, reference_window


def test_unsupported_citations_are_blocked():
    with pytest.raises(ValueError, match="unsupported evidence"):
        validate_claims(
            Answer(title="Bad", response="Claim", claims=[Claim(text="Claim", evidence_ids=["invented"])]), {}
        )


@pytest.mark.asyncio
@respx.mock
async def test_evo2_alignment_uses_next_token_and_ascii_indices(store):
    store.config.evo2_base_url = "http://model.test"
    logits = np.full((4, 1, 512), -20.0)
    for i, base in enumerate("CGT"):
        logits[i, 0, ord(base)] = 20.0
    buffer = io.BytesIO()
    np.savez(buffer, output_layer=logits)
    respx.post("http://model.test/biology/arc/evo2/forward").mock(
        return_value=httpx.Response(200, json={"data": base64.b64encode(buffer.getvalue()).decode()})
    )
    score = await evo2_sequence_score(store, "ACGT")
    assert abs(score) < 0.00001


@pytest.mark.asyncio
@respx.mock
async def test_evo2_nonfinite_outputs_are_withheld(store):
    store.config.evo2_base_url = "http://model.test"
    buffer = io.BytesIO()
    np.savez(buffer, output_layer=np.full((4, 1, 512), np.nan))
    respx.post("http://model.test/biology/arc/evo2/forward").mock(
        return_value=httpx.Response(200, json={"data": base64.b64encode(buffer.getvalue()).decode()})
    )
    with pytest.raises(ValueError, match="non-finite"):
        await evo2_sequence_score(store, "ACGT")


@pytest.mark.asyncio
@respx.mock
async def test_evo2_hosted_endpoint_is_exact_and_authenticated(store):
    endpoint = "https://health.api.nvidia.com/v1/biology/arc/evo2-7b/forward"
    store.config.evo2_forward_url = endpoint
    store.config.evo2_base_url = "http://old-service.test"
    store.config.evo2_access_token = "test-token"
    logits = np.full((1, 4, 512), -20.0)
    for i, base in enumerate("CGT"):
        logits[0, i, ord(base)] = 20.0
    buffer = io.BytesIO()
    np.savez(buffer, **{"unembed.output": logits})
    route = respx.post(endpoint, headers={"Authorization": "Bearer test-token"}).mock(
        return_value=httpx.Response(200, json={"data": base64.b64encode(buffer.getvalue()).decode()})
    )
    assert abs(await evo2_sequence_score(store, "ACGT")) < 0.00001
    assert route.called
    assert json.loads(route.calls[0].request.content)["output_layers"] == ["unembed"]


@pytest.mark.asyncio
@respx.mock
async def test_evo2_binary_npz_response_is_supported(store):
    store.config.evo2_base_url = "http://model.test"
    logits = np.full((4, 1, 512), -20.0)
    for i, base in enumerate("CGT"):
        logits[i, 0, ord(base)] = 20.0
    buffer = io.BytesIO()
    np.savez(buffer, **{"output_layer.output": logits})
    respx.post("http://model.test/biology/arc/evo2/forward").mock(
        return_value=httpx.Response(
            200, content=buffer.getvalue(), headers={"Content-Type": "application/zip"}
        )
    )
    assert abs(await evo2_sequence_score(store, "ACGT")) < 0.00001


@pytest.mark.asyncio
@respx.mock
@pytest.mark.parametrize("wrong_window", [False, True])
async def test_reference_fetch_checks_assembly_interval_and_coordinate_conversion(wrong_window):
    route = respx.get(
        "https://api.genome.ucsc.edu/getData/sequence",
        params={
            "genome": "hg38",
            "chrom": "chr20",
            "start": "95",
            "end": "103",
        },
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "genome": "hg19" if wrong_window else "hg38",
                "chrom": "chr20",
                "start": 95,
                "end": 103,
                "dna": "ACGTACGT",
            },
        )
    )
    if wrong_window:
        with pytest.raises(ValueError, match="different assembly"):
            await reference_window("20", 100, 8)
    else:
        assert await reference_window("20", 100, 8) == ("ACGTACGT", 96)
    assert route.called
