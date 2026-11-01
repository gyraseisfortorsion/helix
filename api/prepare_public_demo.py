"""Build the bounded public demo from attributed primary data; never impute genotypes."""

import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import httpx
import pysam

from .knowledge import PANEL

ROOT = Path(__file__).parent / "public_demo"
CACHE = Path("data/public-sources")
REGIONS = [
    ("chr20", 35430000, 35445000),
    ("chr7", 117587300, 117588300),
    ("chr12", 102840000, 102841000),
    ("chr15", 72350000, 72351000),
]
GIAB = "https://ftp-trace.ncbi.nlm.nih.gov/ReferenceSamples/giab/release/AshkenazimTrio/"
PMDATA = "https://datasets.simula.no/pmdata/"
PMDATA_LICENSE = "https://creativecommons.org/licenses/by-nc/4.0/"
ONT = "https://epi2me.nanoporetech.com/gm24385-5mc/"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url: str, path: Path):
    if path.exists():
        return
    temporary = path.with_suffix(path.suffix + ".partial")
    with httpx.Client(timeout=90, follow_redirects=True) as client, client.stream("GET", url) as response:
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("Expected a complete source file.")
        size = 0
        with temporary.open("wb") as output:
            for chunk in response.iter_bytes(1024 * 1024):
                size += len(chunk)
                if size > 200 * 1024 * 1024:
                    raise ValueError("Public demo source exceeds the download limit.")
                output.write(chunk)
    temporary.replace(path)


def prepare() -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    old_manifest = (
        json.loads((ROOT / "manifest.json").read_text()) if (ROOT / "manifest.json").exists() else {}
    )
    sources, profiles = [], []

    def source(key, path, url, **metadata):
        sha = digest(path)
        old = next((s for s in old_manifest.get("sources", []) if s["id"] == key), None)
        if old and old["sha256"] != sha:
            raise ValueError(f"Source changed: {key}. Review the data before updating the pinned manifest.")
        sources.append({"id": key, "url": url, "sha256": sha, "bytes": path.stat().st_size, **metadata})

    known = [*PANEL, {"chrom": "20", "pos": 35438203, "ref": "G", "alt": "A", "rsid": "rs143383"}]
    for sample, accession, relation in [
        ("HG002", "NA24385", "son"),
        ("HG003", "NA24149", "father"),
        ("HG004", "NA24143", "mother"),
    ]:
        url = (
            GIAB
            + f"{sample}_{accession}_{relation}/NISTv4.2.1/GRCh38/{sample}_GRCh38_1_22_v4.2.1_benchmark.vcf.gz"
        )
        path = CACHE / (sample + "-subset.vcf")
        if not path.exists():
            with (
                pysam.VariantFile(url) as variants,
                pysam.VariantFile(str(path), "w", header=variants.header) as output,
            ):
                for chrom, start, end in REGIONS:
                    for record in variants.fetch(chrom, start, end):
                        if (
                            "PASS" in record.filter
                            and len(record.ref) == 1
                            and record.alts
                            and len(record.alts) == 1
                            and len(record.alts[0]) == 1
                        ):
                            output.write(record)
        source(
            sample,
            path,
            url,
            hash_scope="Exact extracted VCF including original header; not the complete upstream VCF",
            release="NIST GIAB v4.2.1",
            selection=REGIONS,
        )
        rows = []
        with pysam.VariantFile(str(path)) as variants:
            if list(variants.header.samples) != [sample]:
                raise ValueError("Unexpected public sample identity.")
            for record in variants:
                call = record.samples[sample]
                gt = call["GT"]
                if len(gt) != 2 or any(g is None for g in gt):
                    raise ValueError("Unexpected incomplete public genotype.")
                chrom = record.chrom.removeprefix("chr")
                rsid = next(
                    (
                        k["rsid"]
                        for k in known
                        if (chrom, record.pos, record.ref, record.alts[0])
                        == (k["chrom"], k["pos"], k["ref"], k["alt"])
                    ),
                    record.id,
                )
                rows.append(
                    {
                        "chrom": chrom,
                        "pos": record.pos,
                        "ref": record.ref,
                        "alt": record.alts[0],
                        "genotype": ("|" if call.phased else "/").join(map(str, gt)),
                        "allele1": record.alleles[gt[0]],
                        "allele2": record.alleles[gt[1]],
                        "phased": call.phased,
                        "quality": record.qual,
                        "rsid": rsid,
                        "build": "GRCh38",
                    }
                )
        metadata = {
            "build": "GRCh38",
            "provenance": "public_reference",
            "sample_id": sample,
            "source_name": "NIST Genome in a Bottle v4.2.1",
            "source_url": url,
            "selection": "PASS biallelic SNVs in four stated regions; rsIDs annotated only on exact matching known alleles.",
            "limitations": "Small variant-only subset, not a whole genome. Missing records are unknown, not reference calls. No clinical phenotype is provided.",
        }
        profiles.append(
            {
                "key": sample.lower(),
                "profile": {
                    "name": f"{sample} · GIAB {relation}",
                    "age": None,
                    "timezone": "UTC",
                    "goals": "Explore public reference genotypes and molecular predictions",
                    "history": f"Public reference cell-line sample {sample}/{accession}, the {relation} in the GIAB trio. No personal symptoms, lifestyle or clinical outcomes are supplied.",
                    "dietary_constraints": "",
                    "external_analysis_consent": True,
                    "provenance": "public_reference",
                    "source_name": metadata["source_name"],
                    "source_url": "https://www.nist.gov/programs-projects/genome-bottle",
                    "data_notes": f"{len(rows)} observed SNVs from a bounded GRCh38 subset. Cell-line reference data; no wearable data or current health history.",
                },
                "datasets": [
                    {
                        "kind": "genetics",
                        "filename": f"{sample}-GIAB-v4.2.1-subset.vcf",
                        "rows": rows,
                        "metadata": metadata,
                    }
                ],
            }
        )

    # Public Bismark BED is explicitly zero-based in the provider's tutorial.
    methyl_url = "https://ont-exd-int-s3-euwst1-epi2me-labs.s3-eu-west-1.amazonaws.com/modbase_tutorial/chr20.bismark.bed.gz?download=1"
    methyl_path = CACHE / "hg002-chr20-bismark.bed.gz"
    download(methyl_url, methyl_path)
    source(
        "hg002_methylation",
        methyl_path,
        methyl_url,
        release="ONT GM24385 modified-base tutorial",
        sample_id="HG002/GM24385",
        license="Public research release; no separate redistribution license stated on the release page",
    )
    methylation = []
    with gzip.open(methyl_path, "rt") as handle:
        for line in handle:
            chrom, start, end, percent, methylated, unmethylated = line.strip().split("\t")
            start, end, m, u = int(start), int(end), int(methylated), int(unmethylated)
            if chrom != "chr20" or not 35433000 <= start < 35443000 or m + u < 10:
                continue
            if end != start + 1 or abs(float(percent) / 100 - m / (m + u)) > 0.000001:
                raise ValueError("Unexpected Bismark coordinate or percentage convention.")
            methylation.append(
                {
                    "cpg_id": f"chr20:{start + 1}",
                    "beta": m / (m + u),
                    "chrom": "20",
                    "pos": start + 1,
                    "methylated_reads": m,
                    "unmethylated_reads": u,
                    "coverage": m + u,
                }
            )
    methylation = methylation[:500]
    if not methylation:
        raise ValueError("No measured CpG sites met the public sample filters.")
    optional_methylation = {
        "kind": "methylation",
        "filename": "HG002-Bismark-GDF5-region.csv",
        "rows": methylation,
        "metadata": {
            "build": "GRCh38",
            "provenance": "public_reference",
            "sample_id": "HG002/GM24385",
            "tissue": "HG002 lymphoblastoid cell line",
            "assay": "Whole-genome bisulfite sequencing · Bismark",
            "collected_at": "Not reported",
            "source_name": "Oxford Nanopore GM24385 public methylation release",
            "source_url": ONT,
            "selection": "chr20:35433000–35443000, coverage ≥10 reads, at most 500 cytosine sites; beta = methylated/(methylated+unmethylated).",
            "limitations": "Same public cell-line identity as HG002, separate experiments/batches. Not cartilage, blood from the app user or a health score. Site IDs are genomic coordinates, not array probes.",
        },
    }

    pm_paths = {}
    for name, url in [
        ("resting_heart_rate.json", "https://osf.io/download/pckyn/"),
        ("steps.json", "https://osf.io/download/gjpz5/"),
        ("sleep.json", "https://osf.io/download/5jyae/"),
    ]:
        path = CACHE / ("pmdata-p01-" + name)
        download(url, path)
        source("pmdata_" + name, path, url, sample_id="PMData p01", license=PMDATA_LICENSE)
        pm_paths[name] = path
    resting = {
        r["dateTime"][:10]: float(r["value"]["value"])
        for r in json.loads(pm_paths["resting_heart_rate.json"].read_text())
    }
    steps, sleep = defaultdict(float), defaultdict(float)
    for row in json.loads(pm_paths["steps.json"].read_text()):
        steps[row["dateTime"][:10]] += float(row["value"])
    seen_logs = set()
    for row in json.loads(pm_paths["sleep.json"].read_text()):
        if row["logId"] not in seen_logs:
            sleep[row["dateOfSleep"]] += float(row["minutesAsleep"])
            seen_logs.add(row["logId"])
    days = sorted(set(resting) & set(steps) & set(sleep))[-30:]
    wearables = []
    for day in days:
        for metric, value, unit, context in [
            ("resting_heart_rate", resting[day], "bpm", "resting"),
            ("steps", steps[day], "count", "daily_total"),
            ("sleep_duration", sleep[day], "minutes", "daily_total"),
        ]:
            wearables.append(
                {
                    "timestamp": day + "T12:00:00+00:00",
                    "metric": metric,
                    "value": value,
                    "unit": unit,
                    "source": "PMData p01 · Fitbit Versa 2",
                    "context": context,
                }
            )
    pm_meta = {
        "provenance": "public_reference",
        "sample_id": "PMData p01",
        "source_name": "PMData · Thambawita et al. 2020",
        "source_url": PMDATA,
        "license": PMDATA_LICENSE,
        "date_range": days[0] + " to " + days[-1],
        "selection": "Last 30 dates with all three metrics. Resting HR retained; steps sum available minute records; sleep sums minutesAsleep from distinct logs. Missing observations not imputed.",
        "timestamp_interpretation": "Original calendar dates retained. UTC noon is a display convention; original sensor timezone is unspecified.",
        "limitations": "Independent participant, not a GIAB donor. Historical observations, not current health; device estimates are not clinical measurements.",
    }
    profiles.append(
        {
            "key": "pmdata_p01",
            "profile": {
                "name": "PMData · participant p01",
                "age": None,
                "timezone": "UTC",
                "goals": "Explore real historical wearable trends",
                "history": "Public PMData research participant p01. No DNA or methylation is supplied. No connection to the GIAB family.",
                "dietary_constraints": "",
                "external_analysis_consent": True,
                "provenance": "public_reference",
                "source_name": pm_meta["source_name"],
                "source_url": PMDATA,
                "data_notes": pm_meta["date_range"]
                + ". Separate participant; DNA absent. CC BY-NC 4.0; derived daily summaries.",
            },
            "datasets": [
                {
                    "kind": "wearables",
                    "filename": "PMData-p01-daily-subset.csv",
                    "rows": wearables,
                    "metadata": pm_meta,
                }
            ],
        }
    )
    bundle = {"version": 1, "profiles": profiles, "optional_methylation": optional_methylation}
    bundle_path = ROOT / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2, allow_nan=False) + "\n")
    manifest = {
        "version": 1,
        "bundle_sha256": digest(bundle_path),
        "sources": sources,
        "citations": [
            "Wagner et al. 2022, doi:10.1038/s41587-021-01191-w",
            "Oxford Nanopore GM24385 modified-base data release/tutorial",
            "Thambawita et al. 2020, doi:10.1145/3339825.3394926",
        ],
        "sample_matching": "GIAB HG002/HG003/HG004 are a documented trio. Methylation is the HG002/GM24385 cell line, a separate experiment. PMData p01 is an independent wearable participant. No cross-person merging.",
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return {
        "profiles": [(p["profile"]["name"], sum(len(d["rows"]) for d in p["datasets"])) for p in profiles],
        "optional_methylation_sites": len(methylation),
        "bundle_sha256": manifest["bundle_sha256"],
    }


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
