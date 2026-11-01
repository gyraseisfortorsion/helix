"""Bounded, streaming imports. Missing genotypes never become reference calls."""

import csv
import gzip
import math
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .store import Store, identifier

GENETIC_SCHEMA = pa.schema(
    [
        ("chrom", pa.string()),
        ("pos", pa.int64()),
        ("ref", pa.string()),
        ("alt", pa.string()),
        ("genotype", pa.string()),
        ("allele1", pa.string()),
        ("allele2", pa.string()),
        ("phased", pa.bool_()),
        ("quality", pa.float64()),
        ("rsid", pa.string()),
        ("build", pa.string()),
    ]
)
WEARABLE_SCHEMA = pa.schema(
    [
        ("timestamp", pa.string()),
        ("metric", pa.string()),
        ("value", pa.float64()),
        ("unit", pa.string()),
        ("source", pa.string()),
        ("context", pa.string()),
    ]
)
METHYLATION_SCHEMA = pa.schema(
    [
        ("cpg_id", pa.string()),
        ("beta", pa.float64()),
        ("chrom", pa.string()),
        ("pos", pa.int64()),
    ]
)


def chrom_name(value: str) -> str:
    value = value.strip().removeprefix("chr")
    return {"23": "X", "24": "Y", "26": "MT", "M": "MT"}.get(value, value)


def text_stream(path: Path, max_bytes: int):
    opener = gzip.open if path.name.endswith(".gz") else open
    count = 0
    with opener(path, "rt", encoding="utf-8-sig") as stream:
        for line in stream:
            count += len(line.encode())
            if count > max_bytes:
                raise ValueError("The decompressed file exceeds the 2 GiB limit.")
            yield line


def _vcf(lines, build: str):
    sample_seen = False
    for line in lines:
        if line.startswith("##reference"):
            hint = line.lower()
            declared = (
                "GRCh38"
                if any(s in hint for s in ["grch38", "hg38"])
                else ("GRCh37" if any(s in hint for s in ["grch37", "hg19", "hs37"]) else None)
            )
            if declared and declared != build:
                raise ValueError("Selected assembly conflicts with the VCF reference header.")
        if line.startswith("#CHROM"):
            if len(line.rstrip().split("\t")) != 10:
                raise ValueError("Upload a single-sample VCF with one genotype column.")
            sample_seen = True
            continue
        if line.startswith("#") or not line.strip():
            continue
        if not sample_seen:
            raise ValueError("VCF is missing its #CHROM header.")
        fields = line.rstrip().split("\t")
        if len(fields) != 10:
            raise ValueError("Malformed VCF record.")
        chrom, pos, rsid, ref, alts, quality, filter_value, _, fmt, sample = fields
        if filter_value not in {"PASS", "."}:
            yield None
            continue
        alleles = [ref, *alts.split(",")]
        if any(a.startswith("<") or a == "*" or len(a) > 100 for a in alleles):
            yield None
            continue
        if any(set(a.upper()) - set("ACGT") for a in alleles):
            raise ValueError("Only A/C/G/T small-variant alleles are supported.")
        values = dict(zip(fmt.split(":"), sample.split(":"), strict=False))
        gt = values.get("GT", "./.")
        indices = gt.replace("|", "/").split("/")
        if len(indices) != 2 or any(i == "." for i in indices):
            yield {
                "chrom": chrom_name(chrom),
                "pos": int(pos),
                "ref": ref,
                "alt": alts,
                "genotype": "./.",
                "allele1": None,
                "allele2": None,
                "phased": "|" in gt,
                "quality": None,
                "rsid": None if rsid == "." else rsid,
                "build": build,
            }
            continue
        try:
            a1, a2 = [alleles[int(index)].upper() for index in indices]
        except (ValueError, IndexError):
            raise ValueError("Genotype index does not match the VCF alleles.") from None
        q = None if quality == "." else float(quality)
        if q is not None and not math.isfinite(q):
            raise ValueError("Non-finite genotype quality.")
        yield {
            "chrom": chrom_name(chrom),
            "pos": int(pos),
            "ref": ref.upper(),
            "alt": alts.upper(),
            "genotype": gt,
            "allele1": a1,
            "allele2": a2,
            "phased": "|" in gt,
            "quality": q,
            "rsid": None if rsid == "." else rsid,
            "build": build,
        }


def _array(lines, build: str):
    for line in lines:
        if line.startswith("#"):
            hint = line.lower()
            declared = (
                "GRCh38"
                if any(s in hint for s in ["grch38", "build 38", "hg38"])
                else ("GRCh37" if any(s in hint for s in ["grch37", "build 37", "hg19"]) else None)
            )
            if declared and declared != build:
                raise ValueError("Selected assembly conflicts with the genotype file header.")
        if line.startswith("#") or not line.strip():
            continue
        fields = line.strip().split()
        if fields[0].lower() in {"rsid", "rs_id"}:
            continue
        if len(fields) not in {4, 5}:
            raise ValueError("Expected 23andMe or Ancestry tab-separated genotype records.")
        rsid, chrom, pos = fields[:3]
        genotype = fields[3] if len(fields) == 4 else fields[3] + fields[4]
        if genotype in {"--", "00", "NN", "0", "N"}:
            a1 = a2 = None
        elif len(genotype) == 2 and not (set(genotype.upper()) - set("ACGT")):
            a1, a2 = genotype.upper()
        else:
            yield None
            continue
        yield {
            "chrom": chrom_name(chrom),
            "pos": int(pos),
            "ref": None,
            "alt": None,
            "genotype": genotype,
            "allele1": a1,
            "allele2": a2,
            "phased": False,
            "quality": None,
            "rsid": rsid,
            "build": build,
        }


def _wearables(lines, timezone: str):
    reader = csv.DictReader(lines)
    required = {"timestamp", "metric", "value", "unit", "source", "context"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Wearable CSV requires timestamp, metric, value, unit, source, context.")
    units = {"heart_rate": "bpm", "resting_heart_rate": "bpm", "steps": "count", "sleep_duration": "minutes"}
    for row in reader:
        metric, unit = row["metric"].strip(), row["unit"].strip()
        if metric not in units:
            raise ValueError(f"Unsupported metric: {metric}.")
        value = float(row["value"])
        if metric == "sleep_duration" and unit == "hours":
            value *= 60
            unit = "minutes"
        if unit != units[metric] or not math.isfinite(value) or value < 0:
            raise ValueError(f"Invalid value or unit for {metric}.")
        dt = datetime.fromisoformat(row["timestamp"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(timezone))
        yield {
            "timestamp": dt.astimezone(UTC).isoformat(),
            "metric": metric,
            "value": value,
            "unit": unit,
            "source": row["source"].strip()[:80],
            "context": row["context"].strip()[:80],
        }


def _methylation(lines):
    reader = csv.DictReader(lines)
    if not {"cpg_id", "beta"}.issubset(reader.fieldnames or []):
        raise ValueError("Methylation CSV requires cpg_id and beta columns.")
    seen = set()
    for row in reader:
        probe = row["cpg_id"].strip()
        if not probe or probe in seen:
            raise ValueError("Methylation probe IDs must be non-empty and unique per sample.")
        seen.add(probe)
        beta = float(row["beta"])
        if not math.isfinite(beta) or not 0 <= beta <= 1:
            raise ValueError("Methylation beta values must be finite and between 0 and 1.")
        pos = int(row["position"]) if row.get("position") else None
        if pos is not None and pos < 1:
            raise ValueError("Genomic positions must be positive.")
        yield {
            "cpg_id": probe,
            "beta": beta,
            "chrom": chrom_name(row["chrom"]) if row.get("chrom") else None,
            "pos": pos,
        }


def import_dataset(
    store: Store, workspace: str, profile_id: str, source: Path, kind: str, metadata: dict, filename: str
) -> dict:
    profile = store.profile(workspace, profile_id)
    if not profile:
        raise ValueError("Profile not found.")
    build = metadata.get("build")
    if kind in {"genetics", "methylation"} and build not in {"GRCh37", "GRCh38"}:
        raise ValueError("Choose GRCh37 or GRCh38; assembly is never inferred.")
    if kind == "methylation" and not all(metadata.get(k) for k in ["tissue", "assay", "collected_at"]):
        raise ValueError("Optional methylation uploads require tissue, assay and collection date.")
    if kind == "methylation":
        from .methylation import validate_metadata

        validate_metadata(metadata)
    dataset_id = identifier()
    folder = store.root / workspace / profile_id
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{dataset_id}.parquet"
    lines = text_stream(source, store.config.max_uncompressed_bytes)
    normalized_source = None
    reference = store.config.dna_reference_grch37 if build == "GRCh37" else store.config.dna_reference_grch38
    if kind == "genetics":
        if ".vcf" in filename.lower() and reference:
            if not Path(reference).is_file():
                raise ValueError("Configured reference FASTA is missing.")
            # Apply the decompression limit before passing input to native code.
            for _line in text_stream(source, store.config.max_uncompressed_bytes):
                pass
            normalized_source = source.with_name(source.name + ".normalized.vcf")
            try:
                with normalized_source.open("wb") as output:
                    subprocess.run(
                        [sys.executable, "-m", "api.normalize", reference, str(source)],
                        stdout=output,
                        stderr=subprocess.PIPE,
                        check=True,
                        timeout=300,
                    )
            except Exception as exc:
                normalized_source.unlink(missing_ok=True)
                raise ValueError(
                    "Reference validation/normalization failed. Check assembly and reference alleles."
                ) from exc
            lines = text_stream(normalized_source, store.config.max_uncompressed_bytes)
        iterator = _vcf(lines, build) if ".vcf" in filename.lower() else _array(lines, build)
        schema = GENETIC_SCHEMA
    elif kind == "wearables":
        iterator, schema = _wearables(lines, profile.get("timezone", "UTC")), WEARABLE_SCHEMA
    elif kind == "methylation":
        iterator, schema = _methylation(lines), METHYLATION_SCHEMA
    else:
        raise ValueError("Unsupported dataset type.")
    count = missing = excluded = 0
    buffer = []
    try:
        with pq.ParquetWriter(destination, schema) as writer:
            for row in iterator:
                if row is None:
                    excluded += 1
                    continue
                if kind == "genetics" and row["pos"] < 1:
                    raise ValueError("Genomic positions must be positive.")
                count += 1
                if count + excluded > store.config.max_records:
                    raise ValueError("Record limit exceeded.")
                if kind == "genetics" and row["allele1"] is None:
                    missing += 1
                buffer.append(row)
                if len(buffer) == 50_000:
                    writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
                    buffer.clear()
            if buffer:
                writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
        if not count:
            raise ValueError("No supported records found.")
        warnings = []
        if kind == "genetics":
            warnings.append(
                "Absent records are unknown. This file is not a comprehensive negative clinical screen."
            )
            warnings.append(
                "Array strand and all variant alleles must be reference-validated before molecular interpretation."
            )
            if not (
                store.config.dna_reference_grch37 if build == "GRCh37" else store.config.dna_reference_grch38
            ):
                warnings.append(
                    "No local reference FASTA configured; indel left-alignment and reference validation are pending."
                )
        report = {
            "accepted": count,
            "missing": missing,
            "excluded": excluded,
            "warnings": warnings,
            "reference_normalized": normalized_source is not None,
            "provenance": metadata.get("provenance", "uploaded"),
        }
        store.add_dataset(workspace, profile_id, kind, filename, destination, metadata, report, dataset_id)
        return {"dataset_id": dataset_id, **report}
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if normalized_source:
            normalized_source.unlink(missing_ok=True)


def records(
    store: Store, workspace: str, profile_id: str, kind: str, limit: int = 200, search: str = ""
) -> list[dict]:
    datasets = store.datasets(workspace, profile_id, kind)
    if not datasets:
        return []
    paths = [d["path"] for d in datasets]
    with duckdb.connect() as conn:
        relation = conn.from_parquet(paths, union_by_name=True)
        conn.register("dataset_rows", relation)
        order = {
            "genetics": "chrom,pos,rsid",
            "wearables": "timestamp DESC,metric,source",
            "methylation": "cpg_id",
        }[kind]
        if kind == "genetics" and search:
            value = f"%{search}%"
            cur = conn.execute(
                "SELECT DISTINCT * FROM dataset_rows WHERE rsid ILIKE ? OR "
                f"(chrom || ':' || pos::VARCHAR) ILIKE ? ORDER BY {order} LIMIT ?",
                [value, value, limit],
            )
        else:
            cur = conn.execute(f"SELECT DISTINCT * FROM dataset_rows ORDER BY {order} LIMIT ?", [limit])
        names = [d[0] for d in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]


def find_variant(
    store: Store,
    workspace: str,
    profile_id: str,
    *,
    rsid: str | None = None,
    chrom: str | None = None,
    pos: int | None = None,
    build: str | None = None,
) -> list[dict]:
    paths = [d["path"] for d in store.datasets(workspace, profile_id, "genetics")]
    if not paths:
        return []
    with duckdb.connect() as conn:
        conn.register("calls", conn.from_parquet(paths))
        if rsid:
            cur = conn.execute("SELECT DISTINCT * FROM calls WHERE rsid=? LIMIT 20", [rsid])
        else:
            cur = conn.execute(
                "SELECT DISTINCT * FROM calls WHERE chrom=? AND pos=? AND build=? LIMIT 20",
                [chrom, pos, build],
            )
        columns = [v[0] for v in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def investigation_calls(store: Store, workspace: str, profile_id: str, variant_id: str) -> list[dict]:
    if re.fullmatch(r"rs\d+", variant_id):
        return find_variant(store, workspace, profile_id, rsid=variant_id)
    match = re.fullmatch(r"GRCh38:([1-9]|1[0-9]|2[0-2]|X|Y):([1-9]\d*):([ACGT]):([ACGT])", variant_id)
    if not match:
        raise ValueError("Select an uploaded rsID or a supported GRCh38 single-nucleotide variant.")
    chrom, pos, ref, alt = match.groups()
    calls = find_variant(store, workspace, profile_id, chrom=chrom, pos=int(pos), build="GRCh38")
    if ref == alt or not any(
        c.get("ref") == ref and alt in {c.get("allele1"), c.get("allele2")} - {ref} for c in calls
    ):
        return []
    # Retain other calls at the locus so conflicting imports cannot be hidden by the selected allele.
    return calls
