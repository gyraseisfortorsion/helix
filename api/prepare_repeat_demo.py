"""Extract an actual 1997/2007 same-donor whole-blood pair, without invented exact ages or dates."""

import argparse
import hashlib
import json
from pathlib import Path

from .methylation import coefficients

ROOT = Path(__file__).parent / "repeat_demo"
AGE_SOURCE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5557932/"


def prepare(folder: Path):
    weights = coefficients()
    datasets = []
    sources = []
    for accession, year, age_range in [("GSM1886929", 1997, [73, 82]), ("GSM1886935", 2007, [83, 92])]:
        path = folder / (accession + ".soft")
        text = path.read_text()
        values = {}
        pvals = {}
        assert f"Individual_1_{year}" in text and "individual id: 1" in text and "Whole blood" in text
        for line in text.splitlines():
            cells = line.split("\t")
            if cells[0] in weights:
                values[cells[0]] = float(cells[1])
                pvals[cells[0]] = float(cells[2])
        assert set(values) == set(weights)
        assert all(0 <= v <= 1 for v in values.values())
        assert max(pvals.values()) <= 0.05
        url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}"
        meta = {
            "build": "GRCh37",
            "tissue": "whole blood",
            "assay": "Illumina 450K",
            "collected_at": "Not reported",
            "collection_year": year,
            "age_range_at_collection": age_range,
            "age_range_source": AGE_SOURCE,
            "subject_id": "GSE73115:Individual_1",
            "preprocessing": "BeadStudio software v3.2 (as reported by GEO)",
            "qc_status": "public_processed",
            "qc_max_model_probe_detection_pvalue": max(pvals.values()),
            "comparability_group": "GSE73115-BeadStudio-v3.2",
            "comparability_basis": "Same published study, participant, tissue, platform and processing. Raw QC/batch equivalence were not independently validated.",
            "provenance": "public_reference",
            "demo_case_key": "repeat-" + accession,
            "source_name": "GEO GSE73115 · " + accession,
            "source_url": url,
            "selection": "All 71 Hannum model sites, beta values unchanged from the original sample table. Required-site detection p-values are <=0.05. Collection year is reported; day/month are not invented.",
            "limitations": "Same real participant in 1997 and 2007. Only cohort age ranges are published, not individual calendar age. Processed research data with limited QC; no calibrated meaningful-change threshold. No matched DNA/wearables or intervention benefit is established.",
        }
        datasets.append(
            {
                "kind": "methylation",
                "filename": accession + "-71-measured-clock-sites.csv",
                "rows": [
                    {"cpg_id": p, "beta": v, "chrom": None, "pos": None} for p, v in sorted(values.items())
                ],
                "metadata": meta,
            }
        )
        sources.append(
            {
                "accession": accession,
                "year": year,
                "url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={accession}&targ=self&form=text&view=full",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "max_model_probe_detection_pvalue": max(pvals.values()),
            }
        )
    payload = {
        "key": "gse73115-individual-1",
        "profile": {
            "name": "GSE73115 · ten-year methylation follow-up",
            "age": None,
            "timezone": "UTC",
            "goals": "Understand a same-person repeat methylation comparison",
            "history": "Public whole-blood samples from the same participant, Individual 1, in 1997 and 2007. Individual calendar age and exact collection dates are not published; no birthday or collection day is inferred.",
            "dietary_constraints": "",
            "external_analysis_consent": True,
            "provenance": "public_reference",
            "source_name": "GEO GSE73115 · same-person whole-blood follow-up",
            "source_url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE73115",
            "data_notes": "Two real samples from the same donor, ten calendar years apart. Cohort age range was 73–82 in 1997 and 83–92 in 2007. No exact personal age, collection day, matched DNA or wearable data is supplied.",
            "demo_scenario": "repeat_methylation",
        },
        "datasets": datasets,
    }
    ROOT.mkdir(exist_ok=True)
    p = ROOT / "bundle.json"
    p.write_text(json.dumps(payload, indent=2) + "\n")
    (ROOT / "manifest.json").write_text(
        json.dumps(
            {
                "bundle_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "sources": sources,
                "age_range_source": AGE_SOURCE,
                "selection": "Exact 71 published model-site beta values from each original GEO sample; no imputation, no invented dates, no individual calendar-age difference calculated.",
                "retrieved_at": "2026-11-01",
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "pair": [s["accession"] for s in sources],
                "sites_per_sample": 71,
                "source_detection_pvalues": [s["max_model_probe_detection_pvalue"] for s in sources],
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source-folder", type=Path, required=True)
    prepare(p.parse_args().source_folder)
