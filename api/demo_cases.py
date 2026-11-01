"""Source-checked examples that cover the supported product workflows."""

import hashlib
import json
from pathlib import Path

from .methylation_demo import ensure_blood_demo
from .public_demo import attach
from .store import Store

ROOT = Path(__file__).parent / "demo_cases"


def load_cases() -> dict:
    path = ROOT / "bundle.json"
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["bundle_sha256"]:
        raise ValueError("Public demo cases failed their provenance hash check.")
    return json.loads(path.read_text())


def ensure_demo_cases(store: Store, workspace: str) -> list[dict]:
    """Called under the combined-demo seed lock; never touches a private workspace."""
    bundle = load_cases()
    for profile in store.profiles(workspace):
        sample = profile.get("genetic_sample_key") or profile.get("public_dataset_key")
        supplement = bundle["genetics_supplements"].get(sample)
        if supplement and not any(
            d["metadata"].get("demo_case_key") == supplement["metadata"]["demo_case_key"]
            for d in store.datasets(workspace, profile["id"], "genetics")
        ):
            attach(store, workspace, profile["id"], supplement)
    for entry in bundle["family_profiles"]:
        profile = next(
            (p for p in store.profiles(workspace) if p.get("public_dataset_key") == entry["key"]), None
        )
        if profile is None:
            profile = store.create_profile(
                workspace, {**entry["profile"], "public_dataset_key": entry["key"]}
            )
        if not store.datasets(workspace, profile["id"], "genetics"):
            for dataset in entry["datasets"]:
                attach(store, workspace, profile["id"], dataset)
    ensure_blood_demo(store, workspace)
    repeat_root = Path(__file__).parent / "repeat_demo"
    path = repeat_root / "bundle.json"
    manifest = json.loads((repeat_root / "manifest.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["bundle_sha256"]:
        raise ValueError("Repeat methylation demo failed its provenance hash check.")
    repeat = json.loads(path.read_text())
    profile = next(
        (p for p in store.profiles(workspace) if p.get("public_dataset_key") == repeat["key"]), None
    )
    if profile is None:
        profile = store.create_profile(workspace, {**repeat["profile"], "public_dataset_key": repeat["key"]})
    existing = {
        d["metadata"].get("demo_case_key") for d in store.datasets(workspace, profile["id"], "methylation")
    }
    for dataset in repeat["datasets"]:
        if dataset["metadata"]["demo_case_key"] not in existing:
            attach(store, workspace, profile["id"], dataset)
    return store.profiles(workspace)


def profile_coverage(store: Store, workspace: str, profiles: list[dict]) -> list[dict]:
    result = []
    for profile in profiles:
        datasets = store.datasets(workspace, profile["id"])
        coverage = {
            "genetic_calls": sum(d["report"]["accepted"] for d in datasets if d["kind"] == "genetics"),
            "wearable_records": sum(d["report"]["accepted"] for d in datasets if d["kind"] == "wearables"),
            "methylation_samples": sum(d["kind"] == "methylation" for d in datasets),
        }
        result.append({**profile, "data_coverage": coverage})
    return result
