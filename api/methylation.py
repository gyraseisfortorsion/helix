"""Deterministic, versioned research reports for processed methylation exports.

No imputation, raw-array QC, cell-mixture correction or clinical inference.
"""

import csv
import hashlib
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).parent / "methylation_models"
VERSION = "biolearn-0d714f5a0c0ad5743b6315f3edab1f86112d394f"
PAPER = "https://www.sciencedirect.com/science/article/pii/S1097276512008933"
RELIABILITY = "https://www.nature.com/articles/s43587-022-00248-2"


@lru_cache
def coefficients() -> dict[str, float]:
    path = ROOT / "Hannum.csv"
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["coefficients_sha256"]:
        raise ValueError("Methylation model failed its integrity check.")
    with path.open() as handle:
        rows = list(csv.DictReader(handle))
    result = {row["CpGmarker"]: float(row["CoefficientTraining"]) for row in rows}
    if len(result) != 71 or not all(math.isfinite(x) for x in result.values()):
        raise ValueError("Invalid Hannum coefficient table.")
    return result


def validate_metadata(metadata: dict) -> None:
    """Optional report fields must not silently coerce invalid numeric metadata."""
    try:
        when = date.fromisoformat(metadata.get("collected_at", ""))
        if when > date.today():
            raise ValueError()
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Collection date must be an actual date in YYYY-MM-DD format, not in the future."
        ) from exc
    age = metadata.get("age_at_collection")
    if age not in (None, ""):
        if isinstance(age, bool):
            raise ValueError("Age at collection must be a finite number between 0 and 120.")
        try:
            number = float(age)
        except (TypeError, ValueError) as exc:
            raise ValueError("Age at collection must be numeric.") from exc
        if not math.isfinite(number) or not 0 <= number <= 120:
            raise ValueError("Age at collection must be a finite number between 0 and 120.")
        metadata["age_at_collection"] = number
    for key in ["preprocessing", "subject_id", "qc_reference", "comparability_group"]:
        if metadata.get(key) is not None and not isinstance(metadata[key], str):
            raise ValueError(f"{key} must be text.")
        if isinstance(metadata.get(key), str):
            metadata[key] = metadata[key].strip()[:500]


def clock_report(values: dict[str, float], metadata: dict) -> dict:
    weights = coefficients()
    present = sorted(set(values) & weights.keys())
    missing = sorted(weights.keys() - values.keys())
    checks = []

    def check(key, passed, message):
        checks.append({"key": key, "passed": bool(passed), "message": message})

    check(
        "coverage",
        not missing,
        f"{len(present)} of 71 required Hannum CpGs are present. No missing sites are filled in.",
    )
    valid = all(math.isfinite(values[p]) and 0 <= values[p] <= 1 for p in present)
    check("values", valid, "Required beta values must be finite and between 0 and 1.")
    tissue = str(metadata.get("tissue", "")).strip().lower()
    check(
        "tissue",
        tissue in {"whole blood", "blood"},
        "This report supports human whole blood; cell lines, saliva and other tissues are outside scope.",
    )
    assay = str(metadata.get("assay", "")).strip().lower()
    check(
        "assay",
        assay in {"illumina 450k", "illumina humanmethylation450", "450k"},
        "Use an Illumina 450K processed beta export. EPIC versions are not yet evaluated in this adapter.",
    )
    check(
        "preprocessing",
        bool(metadata.get("preprocessing")),
        "Document the laboratory's normalization/preprocessing method.",
    )
    public_qc = (
        metadata.get("provenance") == "public_reference" and metadata.get("qc_status") == "public_processed"
    )
    lab_qc = metadata.get("qc_status") == "lab_reported_pass" and bool(metadata.get("qc_reference"))
    check(
        "qc",
        public_qc or lab_qc,
        "Provide a passing laboratory QC report reference. Public research samples use documented processed data with limited QC.",
    )
    try:
        age = float(metadata["age_at_collection"])
        if not math.isfinite(age):
            age = None
    except (KeyError, TypeError, ValueError):
        age = None
    age_range = metadata.get("age_range_at_collection")
    range_supported = (
        age is None
        and metadata.get("provenance") == "public_reference"
        and bool(metadata.get("age_range_source"))
        and isinstance(age_range, list)
        and len(age_range) == 2
        and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in age_range
        )
        and 19 <= age_range[0] <= age_range[1] <= 101
    )
    check(
        "age",
        (age is not None and 19 <= age <= 101) or range_supported,
        f"Published cohort age range {age_range[0]}–{age_range[1]} is within the adult model scope; individual age is not supplied."
        if range_supported
        else "Record age at collection; this adult model was developed using ages 19–101.",
    )
    ready = all(c["passed"] for c in checks)
    score = math.fsum(weights[p] * values[p] for p in present) if ready else None
    return {
        "status": "ready" if ready else "needs_data",
        "model": "Hannum 2013 · whole-blood methylation age",
        "model_version": VERSION,
        "coefficients_sha256": hashlib.sha256((ROOT / "Hannum.csv").read_bytes()).hexdigest(),
        "required_sites": 71,
        "present_sites": len(present),
        "missing_sites": missing,
        "checks": checks,
        "estimate_years": round(score, 6) if score is not None else None,
        "age_at_collection": age,
        "age_range_at_collection": age_range if range_supported else None,
        "age_range_source": metadata.get("age_range_source") if range_supported else None,
        "calendar_age_difference_years": round(score - age, 6)
        if score is not None and age is not None
        else None,
        "title": "Your sample supports a research age estimate"
        if ready
        else "This sample needs more information for an age report",
        "meaning": "This model combines 71 measured methylation values into an estimate of chronological age. A difference from your calendar age does not measure how healthy you are or how fast you are aging.",
        "next_steps": [c["message"] for c in checks if not c["passed"]]
        if not ready
        else [
            "Keep this report and its laboratory QC documentation as a baseline.",
            "Use the same tissue and a laboratory-confirmed comparable protocol for a repeat test. Small changes may be technical noise.",
            "Track sleep, activity and symptoms for their own value. This score does not identify a diet, supplement or treatment that will help you.",
        ],
        "qc_scope": "Public processed-data research demonstration; raw control probes and detection p-values were not rechecked."
        if public_qc
        else "Laboratory QC is user-reported, not independently verified. Processed betas cannot reproduce raw IDAT QC.",
        "uncertainty": "No personal confidence interval or meaningful-change threshold is calibrated. Cell composition, normalization and technical batches can affect the result.",
        "sources": [PAPER, RELIABILITY],
        "input_fingerprint": hashlib.sha256(
            json.dumps([(p, values[p]) for p in present], separators=(",", ":")).encode()
        ).hexdigest(),
    }


def repeat_comparisons(samples: list[dict]) -> list[dict]:
    """One comparison for each consecutive dated sample, with explicit pairing checks."""
    dated = []
    for sample in samples:
        precision = "date"
        try:
            when = date.fromisoformat(sample["metadata"].get("collected_at", ""))
        except (TypeError, ValueError):
            # Preserve the reported year without inventing a day or month.
            year = sample["metadata"].get("collection_year")
            if (
                sample["metadata"].get("provenance") != "public_reference"
                or not isinstance(year, int)
                or not 1900 <= year <= date.today().year
            ):
                continue
            when = date(year, 1, 1)  # Internal ordering only; never exposed as an observed date.
            precision = "year"
        dated.append((when, sample, precision))
    dated.sort(key=lambda x: (x[0], x[1]["dataset_id"]))
    results = []
    for (before_date, before, before_precision), (after_date, after, after_precision) in zip(
        dated, dated[1:], strict=False
    ):
        a, b = before["metadata"], after["metadata"]
        reasons = []
        if not all(s["age_report"]["status"] == "ready" for s in [before, after]):
            reasons.append("Both samples must pass the report input checks.")
        for field, label in [
            ("subject_id", "confirmed subject ID"),
            ("tissue", "tissue"),
            ("assay", "assay"),
            ("preprocessing", "preprocessing"),
            ("comparability_group", "laboratory comparability group"),
        ]:
            if not a.get(field) or str(a[field]).strip().lower() != str(b.get(field, "")).strip().lower():
                reasons.append(f"The samples need the same {label}.")
        elapsed = (
            float(after_date.year - before_date.year)
            if before_precision == after_precision == "year"
            else (after_date - before_date).days / 365.2425
        )
        if before_precision != after_precision:
            reasons.append("Collection-time precision differs; an exact date is not inferred from a year.")
        if elapsed <= 0:
            reasons.append("Separate collection dates are required.")
        if before["age_report"]["input_fingerprint"] == after["age_report"]["input_fingerprint"]:
            reasons.append(
                "Identical model inputs may be a duplicate export; they are not treated as a repeat measurement."
            )
        age_a, age_b = before["age_report"]["age_at_collection"], after["age_report"]["age_at_collection"]
        if age_a is not None and age_b is not None and abs(age_b - age_a - elapsed) > 1.1:
            reasons.append("Ages at collection do not agree with elapsed calendar time.")
        delta = (
            None
            if reasons
            else after["age_report"]["estimate_years"] - before["age_report"]["estimate_years"]
        )
        results.append(
            {
                "before_id": before["dataset_id"],
                "after_id": after["dataset_id"],
                "from": str(before_date.year) if before_precision == "year" else before_date.isoformat(),
                "to": str(after_date.year) if after_precision == "year" else after_date.isoformat(),
                "time_precision": before_precision if before_precision == after_precision else "mixed",
                "comparability_basis": a.get(
                    "comparability_basis",
                    "User-reported laboratory comparability group; not independently verified.",
                ),
                "status": "blocked" if reasons else "descriptive_only",
                "reasons": reasons,
                "elapsed_years": round(elapsed, 3),
                "estimate_change_years": round(delta, 3) if delta is not None else None,
                "interpretation": "A descriptive model-score difference. Technical variability has not been calibrated; this cannot establish rejuvenation, faster aging or an intervention effect.",
            }
        )
    return results
