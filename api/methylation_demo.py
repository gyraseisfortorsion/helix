"""A real blood reference sample, kept separate from composite demo identities."""

import hashlib
import json
from pathlib import Path
from threading import Lock

from .public_demo import attach
from .store import Store

ROOT = Path(__file__).parent / "methylation_demo"
_lock = Lock()


def load_blood_bundle() -> dict:
    content = (ROOT / "bundle.json").read_bytes()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if hashlib.sha256(content).hexdigest() != manifest["bundle_sha256"]:
        raise ValueError("Blood methylation snapshot failed its provenance hash check.")
    return json.loads(content)


def ensure_blood_demo(store: Store, workspace: str) -> dict:
    with _lock:
        bundle = load_blood_bundle()
        sample = next(s for s in bundle["samples"] if s["accession"] == bundle["demo_accession"])
        key = sample["accession"]
        url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={key}"
        profile = next((p for p in store.profiles(workspace) if p.get("public_dataset_key") == key), None)
        if profile is None:
            profile = store.create_profile(
                workspace,
                {
                    "name": f"{key} · public blood sample",
                    "age": int(sample["age"]),
                    "timezone": "UTC",
                    "goals": "Understand a published methylation-age research report",
                    "history": "Public GEO control sample; no personal symptoms or matched genetic/wearable data supplied.",
                    "dietary_constraints": "",
                    "external_analysis_consent": True,
                    "provenance": "public_reference",
                    "public_dataset_key": key,
                    "source_name": "GEO GSE41169 · whole blood",
                    "source_url": url,
                    "data_notes": "Real human whole-blood reference sample, separate from HG002 and PMData. Only the 71 clock sites are included. Collection date not reported; no longitudinal pair or raw QC data is available.",
                },
            )
        if not store.datasets(workspace, profile["id"], "methylation"):
            attach(
                store,
                workspace,
                profile["id"],
                {
                    "kind": "methylation",
                    "filename": f"{key}-Hannum-71-CpGs.csv",
                    "metadata": {
                        "build": "GRCh37",
                        "tissue": "whole blood",
                        "assay": "Illumina 450K",
                        "collected_at": "Not reported",
                        "age_at_collection": sample["age"],
                        "subject_id": key,
                        "preprocessing": sample["preprocessing"],
                        "qc_status": "public_processed",
                        "provenance": "public_reference",
                        "source_name": "GEO GSE41169 · " + key,
                        "source_url": url,
                        "selection": "The exact 71 Hannum clock CpGs from the original processed matrix. Values unchanged; no imputation.",
                        "limitations": "Processed research data; raw intensities unavailable. No raw control-probe QC or cell-mixture correction. No collection date or repeat sample. Not matched to any DNA or wearables in this app.",
                    },
                    "rows": [
                        {"cpg_id": p, "beta": v, "chrom": None, "pos": None}
                        for p, v in sample["betas"].items()
                    ],
                },
            )
        return profile
