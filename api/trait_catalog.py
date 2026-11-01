"""Bounded public GWAS discovery and local genotype matching, without a PRS.

Only trait terms/rsIDs leave the server. Uploaded genotypes stay local to this tool.
"""

import asyncio
import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx

from .store import Store

BASE = "https://www.ebi.ac.uk/gwas/rest/api/v2"
ROOT = Path(__file__).parent / "trait_catalog_data"
MAX_ASSOCIATIONS = 200
MAX_CANDIDATES = 100


def canonical_trait(trait: str) -> str:
    term = " ".join(trait.strip().lower().split())
    if not term or len(term) > 80 or not re.fullmatch(r"[a-z0-9 ()/'-]+", term):
        raise ValueError("Use a short trait name without personal details.")
    return "heart rate" if term in {"resting heart rate", "heart rate", "pulse", "resting pulse"} else term


def relevant_associations(rows: list[dict], trait: str) -> list[dict]:
    selected = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("multi_snp_haplotype") or row.get("snp_interaction"):
            continue
        if trait == "heart rate" and not any(
            isinstance(t, str) and t.strip().lower() in {"heart rate", "resting heart rate"}
            for t in row.get("reported_trait", [])
        ):
            continue  # Do not silently substitute exercise, fetal HR or transformed min/max HR.
        p = row.get("p_value")
        if not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 5e-8:
            continue
        alleles = row.get("snp_allele", [])
        if len(alleles) != 1 or not re.fullmatch(r"rs\d+", alleles[0].get("rs_id", "")):
            continue
        if len(row.get("locations", [])) != 1:
            continue
        location = re.fullmatch(r"([1-9]|1[0-9]|2[0-2]|X|Y):([1-9]\d*)", row["locations"][0])
        if not location:
            continue
        selected.append(
            {
                "rsid": alleles[0]["rs_id"],
                "effect_allele": alleles[0].get("effect_allele"),
                "chrom": location[1],
                "pos": int(location[2]),
                "build": "GRCh38",
                "association_id": str(row["association_id"]),
                "reported_traits": row.get("reported_trait", []),
                "mapped_genes": row.get("mapped_genes", []),
                "p_value": p,
                "reported_effect": row.get("beta") or row.get("or_value"),
                "pubmed_id": row.get("pubmed_id"),
                "study": row.get("accession_id"),
                "source_url": f"{BASE}/associations/{row['association_id']}",
            }
        )
    return selected


def heart_snapshot() -> dict:
    path = ROOT / "heart_rate.json"
    manifest = json.loads((ROOT / "manifest.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Heart-rate catalogue failed its integrity check.")
    return {**json.loads(path.read_text()), "retrieval": "bundled_public_snapshot"}


async def discover_catalog(store: Store, trait: str, *, live: bool) -> dict:
    trait = canonical_trait(trait)
    cache_key = "gwas:v2:trait:2026-11-01.2:" + trait
    cached = store.cached(cache_key, ttl=7 * 86400)
    if cached:
        return {**cached, "retrieval": "cached_public_catalog"}
    if not live:
        return (
            heart_snapshot()
            if trait == "heart rate"
            else {
                "status": "unavailable",
                "reason": "Live public-catalogue access is not enabled for this question.",
                "trait": trait,
            }
        )
    try:
        async with asyncio.timeout(22), httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
            response = await client.get(BASE + "/efo-traits", params={"efo_trait": trait, "size": 20})
            response.raise_for_status()
            choices = response.json().get("_embedded", {}).get("efo_traits", [])
            exact = [t for t in choices if t.get("efo_trait", "").lower() == trait]
            if len(exact) != 1:
                return {
                    "status": "needs_trait_selection",
                    "trait": trait,
                    "choices": [{"name": t.get("efo_trait"), "id": t.get("efo_id")} for t in choices[:10]],
                    "reason": "No unique exact trait match; related traits are not substituted automatically.",
                }
            response = await client.get(
                BASE + "/associations",
                params={
                    "efo_id": exact[0]["efo_id"],
                    "direction": "asc",
                    "show_child_trait": "false",
                    "page": 0,
                    "size": MAX_ASSOCIATIONS,
                    "sort": "p_value",
                },
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("_embedded", {}).get("associations", [])
            total = payload.get("page", {}).get("totalElements")
            if not isinstance(total, int) or (total > 0 and not rows):
                raise ValueError(
                    "The catalogue did not return the association records advertised by its page metadata."
                )
            result = {
                "status": "available",
                "trait": trait,
                "ontology_id": exact[0]["efo_id"],
                "associations": relevant_associations(rows[:MAX_ASSOCIATIONS], trait),
                "associations_retrieved": len(rows[:MAX_ASSOCIATIONS]),
                "catalog_association_count": total,
                "truncated": total > len(rows),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "source_url": str(response.url),
            }
            store.cache(cache_key, result)
            return {**result, "retrieval": "live_public_catalog"}
    except (httpx.HTTPError, TimeoutError, ValueError, KeyError, TypeError):
        if trait == "heart rate":
            return {
                **heart_snapshot(),
                "live_notice": "The live catalogue could not be retrieved; the dated bundled public snapshot was checked instead.",
            }
        return {
            "status": "unavailable",
            "trait": trait,
            "reason": "The public catalogue could not be retrieved. No negative genetic finding can be inferred.",
        }


def match_calls(store: Store, workspace: str, profile_id: str, candidates: list[dict]) -> dict:
    """One local join across full Parquet inputs, not a frontend preview or whole-genome score."""
    paths = [d["path"] for d in store.datasets(workspace, profile_id, "genetics")]
    if not paths:
        return {"calls": [], "builds": [], "total_calls": 0, "truncated": False}
    with duckdb.connect() as conn:
        conn.register("calls", conn.from_parquet(paths))
        counts = conn.execute(
            "SELECT build,count(*) FROM (SELECT DISTINCT * FROM calls) GROUP BY build"
        ).fetchall()
        if not candidates:
            return {
                "calls": [],
                "builds": [b for b, _ in counts],
                "total_calls": sum(n for _, n in counts),
                "truncated": False,
            }
        conn.execute("CREATE TEMP TABLE wanted(rsid VARCHAR,chrom VARCHAR,pos BIGINT)")
        conn.executemany(
            "INSERT INTO wanted VALUES (?,?,?)", [(c["rsid"], c["chrom"], c["pos"]) for c in candidates]
        )
        cur = conn.execute(
            "SELECT DISTINCT w.rsid AS candidate_rsid,c.* FROM calls c JOIN wanted w ON c.rsid=w.rsid OR (c.build='GRCh38' AND c.chrom=w.chrom AND c.pos=w.pos) ORDER BY candidate_rsid,build,chrom,pos LIMIT 501"
        )
        names = [c[0] for c in cur.description]
        rows = [dict(zip(names, r, strict=True)) for r in cur.fetchall()]
        return {
            "calls": rows[:500],
            "builds": [b for b, _ in counts],
            "total_calls": sum(n for _, n in counts),
            "truncated": len(rows) > 500,
        }


def assess_trait(store: Store, workspace: str, profile_id: str, catalog: dict) -> dict:
    if catalog.get("status") != "available":
        return catalog
    unique = {}
    for row in catalog["associations"]:
        unique.setdefault(row["rsid"], row)
    candidates = list(unique.values())[:MAX_CANDIDATES]
    joined = match_calls(store, workspace, profile_id, candidates)
    findings = []
    for candidate in candidates:
        calls = [c for c in joined["calls"] if c["candidate_rsid"] == candidate["rsid"]]
        if not calls:
            continue
        genotypes = {tuple(sorted([c.get("allele1") or "?", c.get("allele2") or "?"])) for c in calls}
        valid_alleles = all(
            c.get("allele1") in {"A", "C", "G", "T"} and c.get("allele2") in {"A", "C", "G", "T"}
            for c in calls
        )
        coordinate_agreement = all(
            c["build"] == "GRCh38" and c["chrom"] == candidate["chrom"] and c["pos"] == candidate["pos"]
            for c in calls
        )
        status = (
            "observed" if valid_alleles and len(genotypes) == 1 and coordinate_agreement else "unresolved"
        )
        findings.append(
            {
                **candidate,
                "status": status,
                "genotype": "/".join(next(iter(genotypes))) if status == "observed" else None,
                "calls": calls[:3],
                "interpretation": "A measured genotype at a published association locus. Study effect-allele/strand alignment is not established here; no individual heart-rate direction, bpm shift, disease risk or pathogenicity is calculated."
                if status == "observed"
                else "The locus was found, but missing/conflicting alleles or assembly/coordinate differences prevent a resolved observation.",
            }
        )
    return {
        "status": "checked",
        "trait": catalog["trait"],
        "ontology_id": catalog.get("ontology_id"),
        "retrieval": catalog["retrieval"],
        "retrieved_at": catalog["retrieved_at"],
        "source_url": catalog["source_url"],
        "associations_retrieved": catalog["associations_retrieved"],
        "catalog_association_count": catalog["catalog_association_count"],
        "variants_checked": len(candidates),
        "observed_count": sum(f["status"] == "observed" for f in findings),
        "unresolved_count": sum(f["status"] == "unresolved" for f in findings),
        "not_observed_count": len(candidates) - len(findings),
        "uploaded_call_count": joined["total_calls"],
        "findings": findings[:12],
        "findings_truncated": len(findings) > 12 or joined["truncated"],
        "live_notice": catalog.get("live_notice"),
        "scope": "Bounded GWAS association-locus lookup, not a whole-genome interpretation, PRS, rare disease screen, molecular simulation or explanation of an individual's heart rate. Unlisted/absent variants are unknown, not reference or negative.",
        "coverage_limitations": [
            "Only up to 200 strongest catalogue associations and 100 unique supported SNV loci are checked. Reported phenotypes are retained; exercise/fetal/minimum/maximum/transformed HR are not substituted for resting HR.",
            "Coordinate matching supports GRCh38. GRCh37 rsID matches remain unresolved pending remapping; GRCh37 coordinate-only loci are not assessed.",
            "No LD proxies, imputation, effect-allele/strand alignment, ancestry calibration or polygenic score is performed.",
        ],
    }
