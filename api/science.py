import asyncio
import base64
import importlib.metadata
import io
import time
from urllib.parse import urlsplit

import httpx
import numpy as np

from .datasets import investigation_calls
from .eligibility import investigation_eligibility
from .services import cache_hash, ensembl_variant
from .store import Store


async def resolve_variant(store: Store, workspace: str, profile_id: str, variant_id: str) -> dict:
    calls = investigation_calls(store, workspace, profile_id, variant_id)
    if not calls:
        raise ValueError("This variant is not measured in the selected profile.")
    call = calls[0]
    signatures = {
        (
            c["build"],
            c["chrom"],
            c["pos"],
            c.get("ref"),
            tuple(sorted((c.get("allele1") or "?", c.get("allele2") or "?"))),
        )
        for c in calls
    }
    if len(signatures) > 1:
        raise ValueError(
            "This profile contains conflicting calls for that variant. Resolve the conflicting imports before running a molecular comparison."
        )
    eligibility = investigation_eligibility(call)
    if not eligibility["eligible"]:
        raise ValueError(eligibility["reason"])
    if variant_id.startswith("GRCh38:"):
        _, chrom, pos, ref, alt = variant_id.split(":")
        reference, _ = await reference_window(chrom, int(pos), 1)
        if reference != ref:
            raise ValueError(
                "Reference allele mismatch against GRCh38; no model was run. Automatic strand flipping is not allowed."
            )
        return {
            "id": variant_id,
            "rsid": call.get("rsid"),
            "build": "GRCh38",
            "chrom": chrom,
            "pos": int(pos),
            "ref": ref,
            "alt": alt,
            "original_call": call,
        }
    annotation = await ensembl_variant(store, variant_id, build="GRCh38")
    mappings = [
        m
        for m in annotation["mappings"]
        if m.get("assembly_name") == "GRCh38"
        and m.get("coord_system") == "chromosome"
        and m.get("strand") == 1
    ]
    if len(mappings) != 1:
        raise ValueError("A unique forward-strand GRCh38 mapping is required.")
    mapped = mappings[0]
    ref, *alternates = mapped["allele_string"].split("/")
    if call["build"] == "GRCh38" and (
        call["chrom"] != mapped["seq_region_name"] or call["pos"] != mapped["start"]
    ):
        raise ValueError("The uploaded coordinates conflict with the public rsID mapping.")
    if call["build"] == "GRCh37":
        original = await ensembl_variant(store, variant_id, build="GRCh37")
        matches = [
            m
            for m in original["mappings"]
            if m.get("assembly_name") == "GRCh37"
            and m.get("seq_region_name") == call["chrom"]
            and m.get("start") == call["pos"]
            and m.get("strand") == 1
            and m.get("allele_string") == mapped["allele_string"]
        ]
        if len(matches) != 1:
            raise ValueError("The selected SNV could not be mapped consistently between assemblies.")
    observed = {call["allele1"], call["allele2"]}
    if call.get("ref") and call["ref"] != ref:
        raise ValueError("Reference allele mismatch; automatic strand flipping is not allowed.")
    if not observed.issubset({ref, *alternates}):
        raise ValueError("Observed alleles do not match forward-strand reference data.")
    observed_alt = observed - {ref}
    if not observed_alt:
        raise ValueError(
            f"Your measured {variant_id} call is {call['allele1']}/{call['allele2']}, matching reference {ref}. No alternative allele was observed, so there is nothing to compare."
        )
    if len(observed_alt) > 1:
        raise ValueError(
            "Two different alternative alleles were observed. Choose a biallelic call for this comparison."
        )
    alt = observed_alt.pop()
    if len(ref) != 1 or len(alt) != 1 or set(ref + alt) - set("ACGT"):
        raise ValueError("Molecular investigations currently support single-nucleotide variants only.")
    return {
        "id": variant_id,
        "rsid": variant_id,
        "build": "GRCh38",
        "chrom": mapped["seq_region_name"],
        "pos": mapped["start"],
        "ref": ref,
        "alt": alt,
        "original_call": call,
    }


async def reference_window(chrom: str, pos: int, length: int) -> tuple[str, int]:
    start = pos - length // 2
    if start < 1:
        raise ValueError("The reference window extends beyond the chromosome boundary.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            "https://api.genome.ucsc.edu/getData/sequence",
            params={"genome": "hg38", "chrom": "chr" + chrom, "start": start - 1, "end": start + length - 1},
        )
        response.raise_for_status()
    result = response.json()
    if any(
        result.get(key) != value
        for key, value in {
            "genome": "hg38",
            "chrom": "chr" + chrom,
            "start": start - 1,
            "end": start + length - 1,
        }.items()
    ):
        raise ValueError("Reference service returned a different assembly or genomic interval.")
    sequence = result.get("dna", "").upper()
    if len(sequence) != length or set(sequence) - set("ACGT"):
        raise ValueError("Reference window contains ambiguous or missing bases.")
    return sequence, start


def _track_payload(track, interval_start: int) -> list[dict]:
    if track is None or getattr(track, "values", None) is None:
        return []
    values = np.asarray(track.values)
    if values.size == 0:
        return []
    if values.ndim == 1:
        values = values[:, None]
    resolution = int(getattr(track, "resolution", 1))
    stride = max(1, len(values) // 1000)
    metadata = getattr(track, "metadata", None)
    output = []
    for i in range(min(values.shape[-1], 4)):
        name = (
            str(metadata.iloc[i].get("name", f"Track {i + 1}")) if metadata is not None else f"Track {i + 1}"
        )
        if metadata is not None:
            strand = metadata.iloc[i].get("strand")
            if isinstance(strand, str) and strand in {"+", "-"}:
                name += f" (strand {strand})"
        # Bin means preserve scale; each series is independently labeled.
        ys = [float(np.mean(values[j : j + stride, i])) for j in range(0, len(values), stride)]
        if not np.isfinite(ys).all():
            raise ValueError("Model returned non-finite predictions.")
        output.append(
            {
                "name": name,
                "x": [interval_start + j * resolution for j in range(0, len(values), stride)],
                "y": ys,
                "resolution": resolution,
                "display_bin": stride,
            }
        )
    return output


def alphagenome_contexts(api_key: str) -> list[dict]:
    from alphagenome.models.v1 import dna_client, dna_model

    client = dna_client.create(api_key, model_version=dna_model.ModelVersion.ALL_FOLDS, timeout=60)
    metadata = client.output_metadata(organism=dna_client.Organism.HOMO_SAPIENS)
    result = {}
    for name in ["dnase", "atac", "rna_seq"]:
        frame = getattr(metadata, name, None)
        if frame is None:
            continue
        for _, row in frame.iterrows():
            curie = row.get("ontology_curie")
            if not isinstance(curie, str):
                continue
            entry = result.setdefault(
                curie, {"id": curie, "name": str(row.get("biosample_name", curie)), "outputs": []}
            )
            if name.upper() not in entry["outputs"]:
                entry["outputs"].append(name.upper())
    return sorted(result.values(), key=lambda value: value["name"])


def alphagenome_predict(api_key: str, variant: dict, context: str) -> dict:
    try:
        from alphagenome.data import genome
        from alphagenome.models import dna_client
    except ImportError:
        from alphagenome.data import genome
        from alphagenome.models.v1 import dna_client
    from alphagenome.models.v1 import dna_model

    client = dna_client.create(api_key, model_version=dna_model.ModelVersion.ALL_FOLDS, timeout=90)
    metadata = client.output_metadata(organism=dna_client.Organism.HOMO_SAPIENS)
    supported = []
    labels = []
    for name in ["dnase", "atac", "rna_seq"]:
        frame = getattr(metadata, name, None)
        if frame is not None and "ontology_curie" in frame and context in set(frame["ontology_curie"]):
            supported.append(getattr(dna_client.OutputType, name.upper()))
            selected = frame[frame["ontology_curie"] == context]
            labels.extend(selected["biosample_name"].dropna().unique().tolist())
    if not supported:
        raise ValueError(
            "The requested context has no supported RNA/accessibility tracks. No tissue substitution was made."
        )
    v = genome.Variant(
        chromosome="chr" + variant["chrom"],
        position=variant["pos"],
        reference_bases=variant["ref"],
        alternate_bases=variant["alt"],
    )
    interval = v.reference_interval.resize(131072)
    output = client.predict_variant(
        interval=interval,
        variant=v,
        organism=dna_client.Organism.HOMO_SAPIENS,
        requested_outputs=supported,
        ontology_terms=[context],
    )
    tracks = []
    for name in ["dnase", "atac", "rna_seq"]:
        ref = _track_payload(getattr(output.reference, name, None), interval.start + 1)
        alt = _track_payload(getattr(output.alternate, name, None), interval.start + 1)
        for a, b in zip(ref, alt, strict=True):
            tracks.append(
                {
                    "modality": name.upper(),
                    "name": a["name"],
                    "x": a["x"],
                    "reference": a["y"],
                    "alternate": b["y"],
                    "units": "Model-normalized assay signal",
                }
            )
    if not tracks:
        raise ValueError("The service returned no usable predictions for the selected context.")
    return {
        "tracks": tracks,
        "context_name": ", ".join(sorted(set(labels))),
        "model_version": "ALL_FOLDS",
        "sdk_version": importlib.metadata.version("alphagenome"),
        "context": context,
        "interval": {"start": interval.start, "end": interval.end},
        "limitations": [
            "Predictions describe the specified reference biological context, not your current cells.",
            "Chromatin accessibility predictions are not measurements of DNA methylation.",
            "These tracks are not disease probabilities or lifestyle intervention evidence.",
        ],
    }


async def evo2_sequence_score(store: Store, sequence: str) -> float:
    headers = {}
    if store.config.evo2_access_token:
        headers["Authorization"] = "Bearer " + store.config.evo2_access_token
    endpoint = store.config.evo2_forward_endpoint
    if not endpoint:
        raise ValueError("Configure EVO2_FORWARD_URL or EVO2_BASE_URL before scoring.")
    # The hosted StripedHyena server uses native Arc layer names, unlike NIM 2.x.
    layer = "unembed" if urlsplit(endpoint).hostname == "health.api.nvidia.com" else "output_layer"
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            endpoint,
            json={"sequence": sequence, "output_layers": [layer]},
            headers=headers,
        )
        response.raise_for_status()
    tensor_bytes = (
        response.content
        if "zip" in response.headers.get("content-type", "")
        else base64.b64decode(response.json()["data"])
    )
    with np.load(io.BytesIO(tensor_bytes), allow_pickle=False) as arrays:
        key = next((k for k in (layer, layer + ".output") if k in arrays), None)
        if key is None:
            raise ValueError(f"Expected {layer} logits tensor was not returned.")
        logits = np.asarray(arrays[key], dtype=np.float64)
    if logits.shape == (1, len(sequence), 512):
        logits = logits[0]
    elif logits.shape == (len(sequence), 1, 512):
        logits = logits[:, 0]
    if logits.shape != (len(sequence), 512) or not np.isfinite(logits).all():
        raise ValueError("Unexpected or non-finite Evo 2 logits; scoring withheld.")
    # Autoregressive alignment: position t predicts observed base t+1.
    logits = logits[:-1]
    targets = np.frombuffer(sequence[1:].encode("ascii"), dtype=np.uint8)
    maximum = logits.max(axis=-1)
    log_z = maximum + np.log(np.exp(logits - maximum[:, None]).sum(axis=-1))
    return float(np.mean(logits[np.arange(len(targets)), targets] - log_z))


async def evo2_predict(store: Store, variant: dict, mutagenesis: bool, job: str) -> dict:
    store.event(job, "stage", "Reference sequence", "Fetching and validating the GRCh38 reference window")
    reference, start = await reference_window(variant["chrom"], variant["pos"], 8192)
    offset = variant["pos"] - start
    if reference[offset] != variant["ref"]:
        raise ValueError("The downloaded reference base does not match the variant.")
    complement = str.maketrans("ACGT", "TGCA")

    async def score(sequence, label=None):
        if label:
            store.event(job, "stage", "Evo 2", f"Scoring {label}: forward strand")
        forward = await evo2_sequence_score(store, sequence)
        if label:
            store.event(job, "stage", "Evo 2", f"Scoring {label}: reverse complement")
        reverse = await evo2_sequence_score(store, sequence.translate(complement)[::-1])
        return (forward + reverse) / 2

    ref_score = await score(reference, "reference sequence")
    alternate = reference[:offset] + variant["alt"] + reference[offset + 1 :]
    alt_score = await score(alternate, "alternative sequence")
    heatmap = []
    if mutagenesis:
        for position in range(offset - 5, offset + 6):
            for base in "ACGT":
                delta = (
                    0.0
                    if base == reference[position]
                    else await score(reference[:position] + base + reference[position + 1 :]) - ref_score
                )
                heatmap.append({"position": start + position, "base": base, "delta": delta})
            store.event(
                job, "progress", "Molecular model", "Scored a nearby position", {"position": start + position}
            )
    return {
        "reference_score": ref_score,
        "alternate_score": alt_score,
        "delta": alt_score - ref_score,
        "units": "Mean per-token log-likelihood, averaged over both strands",
        "window_length": 8192,
        "reference_source": {
            "provider": "UCSC Genome Browser",
            "assembly": "hg38/GRCh38",
            "chrom": "chr" + variant["chrom"],
            "start_0based": start - 1,
            "end_exclusive": start + 8192 - 1,
        },
        "heatmap": heatmap,
        "model": "Evo 2 (configured NIM deployment)",
        "context": "sequence_only",
        "context_name": "Sequence model (no tissue context)",
        "limitations": [
            "Sequence compatibility is not gene-expression direction, pathogenicity or disease probability.",
            "This adapter requires parity validation against the official scorer before scientific accuracy claims.",
        ],
    }


async def investigate(store: Store, workspace: str, payload: dict, job: str) -> dict:
    profile = store.profile(workspace, payload["profile_id"])
    if not profile or not profile.get("external_analysis_consent"):
        raise ValueError(
            "Enable external-analysis consent on this profile before sending selected variants to providers."
        )
    model = payload["model"]
    if model == "alphagenome" and not store.config.alphagenome_api_key:
        raise ValueError("AlphaGenome is not configured. Add ALPHAGENOME_API_KEY to the backend .env.")
    if model == "evo2" and not store.config.evo2_forward_endpoint:
        raise ValueError(
            "Evo 2 is not configured. Set EVO2_FORWARD_URL for a hosted forward endpoint or EVO2_BASE_URL for a self-hosted NIM."
        )
    store.event(job, "stage", "Genomics", "Validating the uploaded allele against public reference mappings")
    variant = await resolve_variant(store, workspace, payload["profile_id"], payload["variant_id"])
    key = f"molecular:{workspace}:" + cache_hash(
        {
            "workspace": workspace,
            "variant": variant,
            "model": model,
            "context": payload["context"] if model == "alphagenome" else "sequence_only",
            "mutagenesis": payload.get("mutagenesis", False),
        }
    )
    cached = store.cached(key)
    if cached:
        from .molecular_report import explain_prediction

        return {**cached, "execution": "cached", "explanation": explain_prediction(cached)}
    store.event(job, "stage", "Molecular model", f"Requesting {model} predictions in the selected context")
    started = time.time()
    async with asyncio.timeout(600):
        if model == "alphagenome":
            result = await asyncio.to_thread(
                alphagenome_predict, store.config.alphagenome_api_key, variant, payload["context"]
            )
        else:
            result = await evo2_predict(store, variant, payload.get("mutagenesis", False), job)
    result.update(
        {
            "variant": variant,
            "provider": model,
            "execution": "live",
            "created_at": time.time(),
            "elapsed_seconds": round(time.time() - started, 2),
            "request_hash": key.rsplit(":", 1)[1],
        }
    )
    from .molecular_report import explain_prediction

    result["explanation"] = explain_prediction(result)
    store.cache(key, result)
    return result
