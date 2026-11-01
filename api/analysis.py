from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median
from zoneinfo import ZoneInfo

from .datasets import find_variant, records
from .knowledge import PANEL, SOURCES
from .methylation import clock_report, coefficients, repeat_comparisons
from .store import Store


def wearable_summary(store: Store, workspace: str, profile_id: str) -> dict:
    # DISTINCT collapses repeat exports; the summary is deliberately bounded.
    limit = 250_000
    rows = records(store, workspace, profile_id, "wearables", limit=limit)
    profile = store.profile(workspace, profile_id)
    zone = ZoneInfo(profile.get("timezone", "UTC"))
    grouped = defaultdict(list)
    observations = defaultdict(list)
    for row in rows:
        key = (row["timestamp"], row["metric"], row["source"], row["context"])
        observations[key].append(row)
    conflicts = 0
    for observations_at_time in observations.values():
        if len({row["value"] for row in observations_at_time}) > 1:
            conflicts += 1
            continue
        row = observations_at_time[0]
        metric = row["metric"]
        if metric == "heart_rate" and row["context"].lower() in {"rest", "resting"}:
            metric = "resting_heart_rate"
        day = datetime.fromisoformat(row["timestamp"]).astimezone(zone).date().isoformat()
        grouped[(metric, day, row["source"])].append(row)
    by_day = defaultdict(list)
    for (metric, day, _source), source_rows in grouped.items():
        totals = [r for r in source_rows if r["context"].lower() in {"daily_total", "nightly_total"}]
        if metric in {"steps", "sleep_duration"}:
            # Re-exported cumulative totals describe one day, not additive intervals.
            value = (
                max(totals, key=lambda r: r["timestamp"])["value"]
                if totals
                else sum(r["value"] for r in source_rows)
            )
        else:
            value = median(r["value"] for r in source_rows)
        by_day[(metric, day)].append(value)
    daily = []
    for (metric, day), values in sorted(by_day.items(), key=lambda pair: pair[0][1]):
        # Different devices can observe the same activity; never sum across sources.
        value = median(values)
        daily.append({"day": day, "metric": metric, "value": round(value, 2)})
    summaries = {}
    for metric in sorted({row["metric"] for row in daily}):
        points = [r for r in daily if r["metric"] == metric]
        last_date = datetime.fromisoformat(points[-1]["day"]).date()
        # Historical baseline excludes the current day; no future observations.
        history = [
            r["value"]
            for r in points
            if last_date - timedelta(days=28) <= datetime.fromisoformat(r["day"]).date() < last_date
        ]
        baseline = median(history) if len(history) >= 7 else None
        mad = median([abs(v - baseline) for v in history]) if baseline is not None else None
        summaries[metric] = {
            "latest": points[-1]["value"],
            "baseline": baseline,
            "baseline_days": len(history),
            "mad": mad,
            "delta": round(points[-1]["value"] - baseline, 2) if baseline is not None else None,
        }
    return {
        "daily": daily,
        "metrics": summaries,
        "record_count": len(rows),
        "limitations": [
            "Observational patterns do not establish cause.",
            "Resting and exercise measurements are kept separate.",
            "No DNA-based fitness correction is applied.",
            "Latest daily/nightly totals take precedence over intervals; multiple sources use their daily median.",
            f"Conflicting observations excluded: {conflicts}.",
            *(
                [f"Summary is limited to the most recent {limit} distinct records."]
                if len(rows) == limit
                else []
            ),
        ],
    }


def panel_calls(store: Store, workspace: str, profile_id: str, item: dict) -> dict:
    calls = find_variant(store, workspace, profile_id, chrom=item["chrom"], pos=item["pos"], build="GRCh38")
    # An rsID alone is not sufficient: multiallelic IDs can describe different clinical alleles.
    valid = [
        r
        for r in calls
        if r["allele1"] in {item["ref"], item["alt"]}
        and r["allele2"] in {item["ref"], item["alt"]}
        and r["ref"] in {None, item["ref"]}
    ]
    genotypes = {(r["allele1"], r["allele2"]) for r in valid}
    counts = {sum(allele == item["alt"] for allele in pair) for pair in genotypes}
    if len(counts) > 1:
        return {"status": "conflicting_calls", "count": None, "genotype": None}
    if not counts:
        return {"status": "unknown", "count": None, "genotype": None}
    count = counts.pop()
    return {
        "status": {0: "assessed_allele_not_observed", 1: "unconfirmed_carrier", 2: "two_copies_detected"}[
            count
        ],
        "count": count,
        "genotype": "/".join(next(iter(genotypes))),
    }


def family_comparison(store: Store, workspace: str, profile_a: str, profile_b: str) -> dict:
    if profile_a == profile_b:
        raise ValueError("Select two different profiles.")
    profiles = [store.profile(workspace, p) for p in [profile_a, profile_b]]
    if not all(profiles):
        raise ValueError("Profile not found.")
    if not all(store.datasets(workspace, p, "genetics") for p in [profile_a, profile_b]):
        raise ValueError(
            "Both profiles need genetic data. Wearable-only or methylation-only samples cannot be used for this comparison."
        )
    conditions = []
    for item in PANEL:
        a, b = [panel_calls(store, workspace, p, item) for p in [profile_a, profile_b]]
        probability = 0.25 if a["count"] == b["count"] == 1 else None
        conditions.append(
            {
                **item,
                "parent_a": a,
                "parent_b": b,
                "affected_genotype_probability": probability,
                "inheritance": {
                    "two_reference": 0.25,
                    "one_assessed_allele": 0.5,
                    "two_assessed_alleles": 0.25,
                }
                if probability is not None
                else None,
                "explanation": "Conditional 25% probability per pregnancy under the stated recessive model; raw calls require clinical confirmation."
                if probability is not None
                else "No affected-child probability is calculated from incomplete or non-carrier-pair findings. Other variants and residual risk remain unassessed.",
            }
        )
    return {
        "profiles": [{"id": p["id"], "name": p["name"]} for p in profiles],
        "conditions": conditions,
        "scope": "Three explicitly supported alleles across three conditions; not a clinical carrier screen or a compatibility score.",
        "review_date": "2026-10-31",
        "evidence": [SOURCES[k].model_dump() for k in ["inheritance", "cftr", "pah", "hexa"]],
    }


def methylation_summary(store: Store, workspace: str, profile_id: str) -> dict:
    datasets = store.datasets(workspace, profile_id, "methylation")
    samples = []
    for dataset in datasets:
        import duckdb

        with duckdb.connect() as conn:
            cur = conn.execute(
                "SELECT cpg_id,beta,chrom,pos FROM read_parquet(?) ORDER BY cpg_id LIMIT 2000",
                [dataset["path"]],
            )
            rows = [dict(zip([c[0] for c in cur.description], row, strict=True)) for row in cur.fetchall()]
            # Scoring must query the full dataset, not the bounded chart preview.
            model_rows = conn.execute(
                "SELECT cpg_id,beta FROM read_parquet(?) WHERE cpg_id IN (SELECT unnest(?))",
                [dataset["path"], list(coefficients())],
            ).fetchall()
        samples.append(
            {
                "dataset_id": dataset["id"],
                "metadata": dataset["metadata"],
                "report": dataset["report"],
                "probes": rows,
                "display_limit": 2000,
                "age_report": clock_report(dict(model_rows), dataset["metadata"]),
            }
        )
    return {
        "optional": True,
        "samples": samples,
        "comparisons": repeat_comparisons(samples),
        "evidence": [SOURCES[k].model_dump() for k in ["epigenome", "hannum", "clock_reliability"]],
        "limitations": [
            "Hannum estimates chronological age from measured blood methylation; it is not a biological-health score or pace-of-aging measure.",
            "Cell mixtures and batch effects are not corrected from a processed beta table.",
            "Samples from different tissues or assays should not be interpreted as longitudinal change.",
        ],
    }
