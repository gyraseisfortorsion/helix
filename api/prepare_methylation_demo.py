"""Build a bounded public snapshot and a reproducibility check from GEO's original matrix.

Usage: python -m api.prepare_methylation_demo --matrix /path/to/GSE41169_series_matrix.txt.gz
The original matrix is deliberately not distributed with the app.
"""

import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median

from .methylation import ROOT as MODEL_ROOT
from .methylation import coefficients

ROOT = Path(__file__).parent / "methylation_demo"
SOURCE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE41nnn/GSE41169/matrix/GSE41169_series_matrix.txt.gz"


def prepare(matrix: Path):
    weights = coefficients()
    metadata = {}
    selected = {}
    with gzip.open(matrix, "rt") as handle:
        for number, line in enumerate(handle, 1):
            row = next(csv.reader([line], delimiter="\t"))
            if not row:
                continue
            if number in {33, 41, 47, 48, 58}:
                metadata[number] = row[1:]
            if row[0] in weights:
                selected[row[0]] = [float(v) if v else None for v in row[1:]]
    assert set(selected) == set(weights), "All 71 CpGs must be present"
    samples = []
    for i, accession in enumerate(metadata[33]):
        betas = {p: selected[p][i] for p in sorted(weights) if selected[p][i] is not None}
        assert all(math.isfinite(v) and 0 <= v <= 1 for v in betas.values())
        samples.append(
            {
                "accession": accession,
                "age": float(metadata[47][i].split(": ")[-1]),
                "sex": metadata[41][i].split(": ")[-1],
                "cohort_group": "control" if metadata[48][i].split(": ")[-1] == "1" else "schizophrenia",
                "preprocessing": metadata[58][i],
                "betas": betas,
            }
        )
    demo = next(s["accession"] for s in samples if s["cohort_group"] == "control" and 19 <= s["age"] <= 101)
    payload = {"series": "GSE41169", "source_url": SOURCE, "demo_accession": demo, "samples": samples}
    ROOT.mkdir(exist_ok=True)
    bundle = ROOT / "bundle.json"
    bundle.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    expected = {
        r["id"]: float(r["Predicted"]) for r in csv.DictReader((MODEL_ROOT / "expected_biolearn.csv").open())
    }
    predictions = {
        s["accession"]: math.fsum(weights[p] * s["betas"][p] for p in weights)
        for s in samples
        if len(s["betas"]) == 71
    }
    parity = max(abs(predictions[k] - v) for k, v in expected.items())
    assert parity < 1e-8, parity
    adult = [s for s in samples if 19 <= s["age"] <= 101 and len(s["betas"]) == 71]
    errors = [predictions[s["accession"]] - s["age"] for s in adult]

    def metrics(group):
        e = [predictions[s["accession"]] - s["age"] for s in group]
        return (
            {"n": len(e), "mae_years": round(mean(abs(v) for v in e), 4), "bias_years": round(mean(e), 4)}
            if e
            else {"n": 0}
        )

    validation = {
        "cohort": "GSE41169",
        "scope": "No fitting or tuning on this cohort. Retrospective reproducibility/error check, not independent clinical validation; donor overlap with original model development has not been audited.",
        "all_samples": len(samples),
        "eligible_adults": len(adult),
        "mae_years": round(mean(abs(e) for e in errors), 4),
        "median_absolute_error_years": round(median(abs(e) for e in errors), 4),
        "bias_years": round(mean(errors), 4),
        "biolearn_parity": {
            "samples": len(expected),
            "max_absolute_error_years": parity,
            "source": "https://github.com/bio-learn/biolearn/blob/0d714f5a0c0ad5743b6315f3edab1f86112d394f/biolearn/test/data/expected_model_outputs/Hannum.csv",
        },
        "by_sex": {
            g: metrics([s for s in adult if s["sex"] == g]) for g in sorted({s["sex"] for s in adult})
        },
        "by_cohort_group": {
            g: metrics([s for s in adult if s["cohort_group"] == g]) for g in ["control", "schizophrenia"]
        },
        "limitations": [
            "Single Dutch whole-blood cohort with limited age/population coverage.",
            "Raw intensities unavailable; no raw-array QC or cell-mixture adjustment.",
            "No longitudinal pairs or technical replicates; no personal interval or meaningful-change threshold is calibrated.",
            "Not evaluated on EPIC, saliva, children or customer laboratory pipelines.",
        ],
    }
    (ROOT / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    manifest = {
        "bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(),
        "matrix_sha256": hashlib.sha256(matrix.read_bytes()).hexdigest(),
        "source_url": SOURCE,
        "selection": "Only the exact 71 published Hannum CpGs; original beta values unchanged, all 95 GEO samples retained, with missing values omitted and incomplete samples excluded from score evaluation. Demo is first adult control in original source order.",
        "collection_date": "Not reported; submission/publication date is not used as collection date.",
        "retrieved_at": "2026-11-01",
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"demo": demo, "validation": validation}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    prepare(parser.parse_args().matrix)
