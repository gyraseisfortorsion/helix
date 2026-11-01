"""Explicitly refresh the bounded public heart-rate snapshot; review data changes before sharing."""

import hashlib
import json
from datetime import UTC, datetime

import httpx

from .trait_catalog import BASE, MAX_ASSOCIATIONS, ROOT, relevant_associations


def prepare():
    response = httpx.get(
        BASE + "/associations",
        params={
            "efo_id": "OBA_1001087",
            "direction": "asc",
            "show_child_trait": "false",
            "page": 0,
            "size": MAX_ASSOCIATIONS,
            "sort": "p_value",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload["_embedded"]["associations"]
    total = payload["page"]["totalElements"]
    if not rows:
        raise ValueError("Refusing to replace the snapshot with an empty response.")
    value = {
        "status": "available",
        "trait": "heart rate",
        "ontology_id": "OBA_1001087",
        "associations": relevant_associations(rows, "heart rate"),
        "associations_retrieved": len(rows),
        "catalog_association_count": total,
        "truncated": total > len(rows),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source_url": str(response.url),
    }
    ROOT.mkdir(exist_ok=True)
    body = (json.dumps(value, indent=2) + "\n").encode()
    manifest = {
        "sha256": hashlib.sha256(body).hexdigest(),
        "source_response_sha256": hashlib.sha256(response.content).hexdigest(),
        "source_url": value["source_url"],
        "retrieved_at": value["retrieved_at"],
        "selection": "First 200 associations by ascending p_value for exact heart-rate ontology. Keep reported Heart rate or Resting heart rate, genome-wide significance, single rsID and one GRCh38 location; exclude haplotypes/interactions. No individual effect or PRS.",
    }
    (ROOT / "heart_rate.json").write_bytes(body)
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"Retained {len(value['associations'])} supported associations. Review the updated manifest and values."
    )


if __name__ == "__main__":
    prepare()
