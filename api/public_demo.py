"""Load the verified, bounded public-data snapshot without runtime downloads."""

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .datasets import GENETIC_SCHEMA, METHYLATION_SCHEMA, WEARABLE_SCHEMA
from .store import Store, identifier

ROOT = Path(__file__).parent / "public_demo"


def load_bundle() -> tuple[dict, dict]:
    path = ROOT / "bundle.json"
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["bundle_sha256"]:
        raise ValueError("Public demo snapshot failed its provenance hash check.")
    return json.loads(path.read_text()), manifest


def attach(store: Store, workspace: str, profile_id: str, dataset: dict):
    schemas = {"genetics": GENETIC_SCHEMA, "wearables": WEARABLE_SCHEMA, "methylation": METHYLATION_SCHEMA}
    dataset_id = identifier()
    folder = store.root / workspace / profile_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (dataset_id + ".parquet")
    rows, meta = dataset["rows"], dataset["metadata"]
    pq.write_table(pa.Table.from_pylist(rows, schema=schemas[dataset["kind"]]), path)
    store.add_dataset(
        workspace,
        profile_id,
        dataset["kind"],
        dataset["filename"],
        path,
        meta,
        {
            "accepted": len(rows),
            "missing": 0,
            "excluded": 0,
            "provenance": "public_reference",
            "warnings": [meta["selection"], meta["limitations"]],
        },
        dataset_id,
    )


def seed_public_demo(store: Store, workspace: str) -> list[dict]:
    if store.profiles(workspace):
        return store.profiles(workspace)
    bundle, manifest = load_bundle()
    result = []
    for entry in bundle["profiles"]:
        profile = store.create_profile(
            workspace,
            {
                **entry["profile"],
                "public_dataset_key": entry["key"],
                "demo_bundle_sha256": manifest["bundle_sha256"],
            },
        )
        for dataset in entry["datasets"]:
            attach(store, workspace, profile["id"], dataset)
        result.append(profile)
    return result


def attach_public_methylation(store: Store, workspace: str, profile_id: str):
    profile = store.profile(workspace, profile_id)
    if not profile or (profile.get("public_dataset_key") or profile.get("genetic_sample_key")) != "hg002":
        raise ValueError("The public methylation sample belongs only to HG002/GM24385.")
    bundle, _ = load_bundle()
    attach(store, workspace, profile_id, bundle["optional_methylation"])
