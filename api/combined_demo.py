"""Fictional people for the product demo, with traceable public source measurements."""

from copy import deepcopy
from threading import Lock

from .public_demo import attach, load_bundle
from .store import Store

_seed_lock = Lock()
PERSONAS = (
    {
        "demo_persona_key": "alex-v1",
        "name": "Alex Morgan · combined demo",
        "age": 31,
        "genetic_sample_key": "hg002",
        "goals": "Understand knee discomfort, activity, recovery and nutrition",
        "history": "Fictional demo scenario as of 2020-03-31: knee discomfort after increasing running. No examination or diagnosis has been supplied. Wants to understand inherited susceptibility alongside activity and recovery.",
    },
    {
        "demo_persona_key": "sam-v1",
        "name": "Sam Chen · combined demo",
        "age": 30,
        "genetic_sample_key": "hg003",
        "goals": "Understand resting heart rate, sleep, activity and genetic context",
        "history": "Fictional demo scenario as of 2020-03-31: asks how resting heart rate compares with their own baseline and whether DNA can explain it. No clinical diagnosis or medication history has been supplied.",
    },
)


def demo_profile_order(profiles: list[dict]) -> list[dict]:
    return sorted(
        profiles, key=lambda p: (not bool(p.get("demo_persona_key")), p.get("demo_persona_key", ""))
    )


def ensure_combined_demo(store: Store, workspace: str) -> list[dict]:
    """Add missing personas without changing original samples, chats or measurements."""
    with _seed_lock:
        bundle, manifest = load_bundle()
        sources = {entry["key"]: entry for entry in bundle["profiles"]}
        profiles = store.profiles(workspace)
        for persona in PERSONAS:
            profile = next(
                (p for p in profiles if p.get("demo_persona_key") == persona["demo_persona_key"]), None
            )
            if not profile:
                profile = store.create_profile(
                    workspace,
                    {
                        **persona,
                        "timezone": "UTC",
                        "dietary_constraints": "",
                        "external_analysis_consent": True,
                        "provenance": "composite_demo",
                        "wearable_sample_key": "pmdata_p01",
                        "demo_scenario_date": "2020-03-31",
                        "demo_bundle_sha256": manifest["bundle_sha256"],
                        "source_name": "Combined demo · public DNA + wearables",
                        "source_url": "https://www.nist.gov/programs-projects/genome-bottle",
                        "data_notes": f"Fictional person: {persona['genetic_sample_key'].upper()} DNA + PMData p01 wearables from March 2020. Source participants differ; both demo users reuse p01. Age and symptom history are invented.",
                    },
                )
                profiles.append(profile)
            existing = {d["kind"] for d in store.datasets(workspace, profile["id"])}
            for source_key in (persona["genetic_sample_key"], "pmdata_p01"):
                for source in sources[source_key]["datasets"]:
                    if source["kind"] in existing:
                        continue
                    dataset = deepcopy(source)
                    dataset["metadata"]["demo_usage"] = "composite_demo"
                    dataset["metadata"]["limitations"] += (
                        " Used in a fictional combined persona; the DNA and wearable sources are different participants. No real-person genotype–wearable association is established."
                    )
                    attach(store, workspace, profile["id"], dataset)
        from .demo_cases import ensure_demo_cases

        return demo_profile_order(ensure_demo_cases(store, workspace))
