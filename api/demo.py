import csv
import io
import random
from datetime import UTC, datetime, timedelta

import pyarrow as pa
import pyarrow.parquet as pq

from .datasets import GENETIC_SCHEMA, METHYLATION_SCHEMA, WEARABLE_SCHEMA
from .knowledge import PANEL
from .store import Store, identifier


def seed_demo(store: Store, workspace: str) -> list[dict]:
    if store.profiles(workspace):
        return store.profiles(workspace)
    profiles = []
    for name, age, index in [("Alex Morgan", 31, 0), ("Sam Chen", 30, 1)]:
        profile = store.create_profile(
            workspace,
            {
                "name": name,
                "age": age,
                "timezone": "America/New_York",
                "goals": "Understand recovery, joint health and nutrition",
                "history": "Synthetic demonstration profile",
                "dietary_constraints": "",
                "external_analysis_consent": True,
                "provenance": "synthetic",
            },
        )
        profiles.append(profile)
        rows = []
        entries = [*PANEL, {"rsid": "rs143383", "chrom": "20", "pos": 35438203, "ref": "G", "alt": "A"}]
        for item in entries:
            gt = "0/1" if item.get("gene") == "CFTR" or "gene" not in item else "0/0"
            # Keep panel findings explicit; this fixture is not a real person's genome.
            if item.get("gene") == "HEXA" and index == 1:
                gt = "0/1"
            rows.append(
                {
                    "chrom": item["chrom"],
                    "pos": item["pos"],
                    "ref": item["ref"],
                    "alt": item["alt"],
                    "genotype": gt,
                    "allele1": item["ref"],
                    "allele2": item["alt"] if gt == "0/1" else item["ref"],
                    "phased": False,
                    "quality": 99.0,
                    "rsid": item["rsid"],
                    "build": "GRCh38",
                }
            )
        add_rows(
            store,
            workspace,
            profile["id"],
            "genetics",
            rows,
            GENETIC_SCHEMA,
            {"build": "GRCh38", "provenance": "synthetic"},
        )
        rng = random.Random(42 + index)
        observations = []
        start = datetime(2026, 10, 1, 12, tzinfo=UTC)
        for day in range(30):
            timestamp = (start + timedelta(days=day)).isoformat()
            values = [
                ("resting_heart_rate", 81 + rng.uniform(-3, 3) + (5 if day > 25 else 0), "bpm", "resting"),
                ("steps", rng.randint(4500, 11500), "count", "daily_total"),
                ("sleep_duration", rng.uniform(360, 480), "minutes", "nightly_total"),
            ]
            for metric, value, unit, context in values:
                observations.append(
                    {
                        "timestamp": timestamp,
                        "metric": metric,
                        "value": round(value, 2),
                        "unit": unit,
                        "source": "Synthetic wearable",
                        "context": context,
                    }
                )
        add_rows(
            store,
            workspace,
            profile["id"],
            "wearables",
            observations,
            WEARABLE_SCHEMA,
            {"provenance": "synthetic"},
        )
    return profiles


def add_rows(store: Store, workspace: str, profile: str, kind: str, rows: list, schema, metadata: dict):
    dataset = identifier()
    folder = store.root / workspace / profile
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{dataset}.parquet"
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    store.add_dataset(
        workspace,
        profile,
        kind,
        f"synthetic-{kind}.csv",
        path,
        metadata,
        {
            "accepted": len(rows),
            "missing": 0,
            "excluded": 0,
            "warnings": ["Synthetic demo data; not a real person."],
            "provenance": "synthetic",
        },
        dataset,
    )


def add_demo_methylation(store: Store, workspace: str, profile: str):
    rng = random.Random(7)
    rows = [
        {"cpg_id": f"DEMO_CPG_{i:03}", "beta": round(rng.uniform(0.05, 0.95), 3), "chrom": None, "pos": None}
        for i in range(24)
    ]
    add_rows(
        store,
        workspace,
        profile,
        "methylation",
        rows,
        METHYLATION_SCHEMA,
        {
            "build": "GRCh38",
            "tissue": "Synthetic blood sample",
            "assay": "Synthetic beta table",
            "collected_at": "2026-10-30",
            "provenance": "synthetic",
        },
    )


def template_file(kind: str) -> tuple[str, str]:
    if kind == "genetics":
        content = "##fileformat=VCFv4.2\n##reference=GRCh38\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n7\t117587806\trs75527207\tG\tA\t99\tPASS\t.\tGT\t0/1\n"
        return "synthetic-example.vcf", content
    if kind == "methylation":
        return "methylation-template.csv", "cpg_id,beta\nEXAMPLE_PROBE_1,0.45\nEXAMPLE_PROBE_2,0.72\n"
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp", "metric", "value", "unit", "source", "context"])
    writer.writerow(
        ["2026-10-30T08:00:00-04:00", "resting_heart_rate", 80, "bpm", "Example export", "resting"]
    )
    return "wearables-template.csv", buffer.getvalue()
