"""Prepare additional measured public examples for the supported demo workflows."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pysam

from .knowledge import PANEL
from .trait_catalog import heart_snapshot

ROOT = Path(__file__).parent / "demo_cases"
CACHE = Path("data/public-sources/demo-cases")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def annotations(variants):
    async with httpx.AsyncClient(timeout=30) as client:
        for rsid in variants:
            path = CACHE / (rsid + ".json")
            if not path.exists():
                response = await client.get(
                    "https://rest.ensembl.org/variation/human/" + rsid, headers={"Accept": "application/json"}
                )
                response.raise_for_status()
                path.write_text(response.text)
            variants[rsid]["annotation"] = json.loads(path.read_text())


def prepare():
    CACHE.mkdir(parents=True, exist_ok=True)
    ROOT.mkdir(exist_ok=True)
    variants = {r["rsid"]: dict(r) for r in heart_snapshot()["associations"]}
    asyncio.run(annotations(variants))
    supplements = {}
    sources = []
    for sample, accession, relation in [
        ("HG002", "NA24385", "son"),
        ("HG003", "NA24149", "father"),
        ("HG004", "NA24143", "mother"),
    ]:
        url = f"https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/{sample}_{accession}_{relation}/NISTv4.2.1/GRCh38/{sample}_GRCh38_1_22_v4.2.1_benchmark.vcf.gz"
        path = CACHE / (sample + "-heart.vcf")
        if not path.exists():
            with (
                pysam.VariantFile(url) as source,
                pysam.VariantFile(str(path), "w", header=source.header) as output,
            ):
                for variant in variants.values():
                    for record in source.fetch("chr" + variant["chrom"], variant["pos"] - 1, variant["pos"]):
                        if (
                            record.pos == variant["pos"]
                            and "PASS" in record.filter
                            and len(record.ref) == 1
                            and record.alts
                            and len(record.alts) == 1
                            and len(record.alts[0]) == 1
                        ):
                            output.write(record)
        rows = []
        with pysam.VariantFile(str(path)) as source:
            assert list(source.header.samples) == [sample]
            for record in source:
                variant = next(
                    v
                    for v in variants.values()
                    if v["chrom"] == record.chrom.removeprefix("chr") and v["pos"] == record.pos
                )
                mappings = [
                    m
                    for m in variant["annotation"]["mappings"]
                    if m.get("assembly_name") == "GRCh38"
                    and m.get("seq_region_name") == variant["chrom"]
                    and m.get("start") == record.pos
                    and m.get("end") == record.pos
                    and m.get("strand") == 1
                    and set(record.alleles) <= set(m.get("allele_string", "").split("/"))
                ]
                assert len(mappings) == 1, variant["rsid"]
                gt = record.samples[sample]["GT"]
                assert len(gt) == 2 and None not in gt
                phased = record.samples[sample].phased
                rows.append(
                    {
                        "chrom": variant["chrom"],
                        "pos": record.pos,
                        "ref": record.ref,
                        "alt": record.alts[0],
                        "genotype": ("|" if phased else "/").join(map(str, gt)),
                        "allele1": record.alleles[gt[0]],
                        "allele2": record.alleles[gt[1]],
                        "rsid": variant["rsid"],
                        "phased": phased,
                        "quality": record.qual,
                        "build": "GRCh38",
                    }
                )
        assert rows
        supplements[sample.lower()] = {
            "kind": "genetics",
            "filename": sample + "-GIAB-heart-markers.vcf",
            "rows": rows,
            "metadata": {
                "build": "GRCh38",
                "provenance": "public_reference",
                "sample_id": sample,
                "demo_case_key": "giab-heart-v1-" + sample.lower(),
                "source_name": "NIST GIAB v4.2.1 · measured heart-rate loci",
                "source_url": url,
                "selection": "Exact sites from the dated GWAS heart-rate snapshot; only observed PASS biallelic SNVs. rsID/alleles checked against forward-strand GRCh38 Ensembl mappings. No absent calls are filled in.",
                "limitations": "Association loci only; no per-person bpm estimate, clinical classification or polygenic score. Source identity matches the existing GIAB DNA; wearable sources remain independent.",
            },
        }
        sources.append(
            {
                "sample": sample,
                "url": url,
                "sha256": sha(path),
                "hash_scope": "Extracted original VCF including original header",
                "rows": len(rows),
            }
        )
    pah = PANEL[1]
    path = CACHE / "rs5030858-sample-genotypes.json"
    if not path.exists():
        response = httpx.get(
            "https://rest.ensembl.org/variation/human/rs5030858",
            params={"genotypes": 1},
            headers={"Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        path.write_text(response.text)
    response = json.loads(path.read_text())
    mapping = [
        m
        for m in response["mappings"]
        if m.get("assembly_name") == "GRCh38"
        and m.get("seq_region_name") == pah["chrom"]
        and m.get("start") == pah["pos"]
        and m.get("end") == pah["pos"]
        and m.get("strand") == 1
        and m.get("allele_string") == "G/A"
    ]
    assert len(mapping) == 1
    profiles = []
    for sample in ["NA12043", "NA20332"]:
        observed = [r for r in response["genotypes"] if r["sample"] == "1000GENOMES:phase_3:" + sample]
        assert len(observed) == 1 and set(observed[0]["genotype"].split("|")) == {"G", "A"}
        a, b = observed[0]["genotype"].split("|")
        row = {
            "chrom": pah["chrom"],
            "pos": pah["pos"],
            "ref": "G",
            "alt": "A",
            "genotype": f"{int(a == 'A')}|{int(b == 'A')}",
            "allele1": a,
            "allele2": b,
            "phased": True,
            "quality": None,
            "rsid": pah["rsid"],
            "build": "GRCh38",
        }
        key = "family-" + sample.lower()
        partner = "family-" + ("na20332" if sample == "NA12043" else "na12043")
        url = "https://rest.ensembl.org/variation/human/rs5030858?genotypes=1"
        meta = {
            "build": "GRCh38",
            "provenance": "public_reference",
            "sample_id": sample,
            "source_name": "1000 Genomes Phase 3 · Ensembl sample genotypes",
            "source_url": url,
            "demo_case_key": key,
            "selection": "The original measured phase-3 sample genotype at rs5030858. The unique forward-strand GRCh38 mapping and G/A alleles were verified. No calls at CFTR/HEXA are inferred.",
            "limitations": "One measured PAH locus, not a genome or comprehensive carrier screen. The two selected samples are a hypothetical pairing, not a known couple. No symptoms, offspring outcomes, matched wearable or methylation data are supplied.",
        }
        profiles.append(
            {
                "key": key,
                "profile": {
                    "name": sample + " · PAH inheritance example",
                    "age": None,
                    "timezone": "UTC",
                    "goals": "Understand conditional inheritance for a measured PAH allele",
                    "history": "Public 1000 Genomes Phase 3 reference sample. Hypothetical comparison with another public sample; no actual couple or pregnancy is represented.",
                    "dietary_constraints": "",
                    "external_analysis_consent": True,
                    "provenance": "public_reference",
                    "source_name": meta["source_name"],
                    "source_url": url,
                    "data_notes": meta["limitations"],
                    "recommended_partner_key": partner,
                    "demo_scenario": "family",
                },
                "datasets": [
                    {
                        "kind": "genetics",
                        "filename": sample + "-measured-PAH.csv",
                        "rows": [row],
                        "metadata": meta,
                    }
                ],
            }
        )
    sources.append(
        {
            "url": "https://rest.ensembl.org/variation/human/rs5030858?genotypes=1",
            "sha256": sha(path),
            "samples": ["NA12043", "NA20332"],
            "hash_scope": "Original public Ensembl response with 2504 sample genotypes; only the two selected records are bundled",
        }
    )
    result = {"genetics_supplements": supplements, "family_profiles": profiles}
    p = ROOT / "bundle.json"
    p.write_text(json.dumps(result, indent=2) + "\n")
    manifest = {
        "bundle_sha256": sha(p),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "sources": sources,
        "annotations": [
            {
                "rsid": v["rsid"],
                "sha256": sha(CACHE / (v["rsid"] + ".json")),
                "url": "https://rest.ensembl.org/variation/human/" + v["rsid"],
            }
            for v in variants.values()
        ],
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "heart_calls": {k: len(v["rows"]) for k, v in supplements.items()},
                "family_samples": [p["key"] for p in profiles],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    prepare()
