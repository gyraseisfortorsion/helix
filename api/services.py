"""Small public-data adapters. Personal data leaves the server only with consent."""

import hashlib
import json
import re

import httpx

from .store import Store


async def ensembl_variant(store: Store, variant_id: str, build: str = "GRCh38") -> dict:
    if not re.fullmatch(r"rs\d+", variant_id):
        raise ValueError("Public variant lookup requires an rsID.")
    key = f"ensembl:{build}:{variant_id}"
    cached = store.cached(key, ttl=7 * 86400)
    if cached is not None:
        return {**cached, "cached": True}
    host = "https://grch37.rest.ensembl.org" if build == "GRCh37" else "https://rest.ensembl.org"
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        response = await client.get(
            f"{host}/variation/human/{variant_id}", headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
    value = {
        "rsid": result["name"],
        "mappings": result.get("mappings", []),
        "consequence": result.get("most_severe_consequence"),
        "clinical_significance": result.get("clinical_significance", []),
        "source_url": f"https://www.ensembl.org/Homo_sapiens/Variation/Explore?v={variant_id}",
        "limitations": "Aggregate rsID significance can describe multiple alleles and conditions; it is not a clinical classification of your genotype.",
    }
    store.cache(key, value)
    return {**value, "cached": False}


async def literature(store: Store, query: str) -> list[dict]:
    query = query[:300]
    key = "literature:" + hashlib.sha256(query.encode()).hexdigest()
    cached = store.cached(key)
    if cached is not None:
        return cached
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query": query, "format": "json", "pageSize": 4, "resultType": "core"},
        )
        response.raise_for_status()
        results = response.json().get("resultList", {}).get("result", [])
    output = []
    for row in results:
        if row.get("source") != "MED" or not row.get("pmid"):
            continue
        # Abstracts are untrusted reference material, never instructions to an agent.
        abstract = re.sub("<[^>]+>", " ", row.get("abstractText", ""))[:3500]
        output.append(
            {
                "id": "pubmed-" + row["pmid"],
                "category": "experiment",
                "title": row.get("title", "Publication"),
                "url": "https://pubmed.ncbi.nlm.nih.gov/" + row["pmid"] + "/",
                "summary": abstract or "No abstract available; do not infer support from the title.",
                "limitations": "Retrieved publication; study design and relevance must be assessed before using its conclusions.",
                "context": str(row.get("pubYear", "")),
                "provenance": "public_reference",
            }
        )
    store.cache(key, output)
    return output


async def annotate_vep(variant: dict) -> dict:
    if not variant.get("ref") or not variant.get("alt") or "," in variant["alt"]:
        raise ValueError("VEP requires a resolved reference and alternative allele.")
    host = "https://grch37.rest.ensembl.org" if variant["build"] == "GRCh37" else "https://rest.ensembl.org"
    record = f"{variant['chrom']} {variant['pos']} . {variant['ref']} {variant['alt']} . . ."
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{host}/vep/human/region", json={"variants": [record]}, headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        rows = response.json()
    return rows[0] if rows else {}


def cache_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
