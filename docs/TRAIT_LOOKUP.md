# Question-driven genetic association lookup

The genomics workflow can discover GWAS associations for a short trait name and match them to the full uploaded call tables locally. It no longer depends only on the hand-written `TOPICS[trait].variants` list. Heart-rate questions run this lookup as a required workflow step before specialist synthesis, including evidence-only mode.

## What happens

1. Normalize the question's trait. For resting heart rate, discover the exact `heart rate` ontology entry in GWAS Catalog v2, currently `OBA_1001087`.
2. Retrieve up to 200 associations ordered by ascending p-value. Keep supported, genome-wide-significant single-variant records with one rsID and GRCh38 location. Retain the reported phenotype: exercise, fetal, transformed minimum/maximum and other heart-rate phenotypes are not substituted for resting heart rate.
3. Check up to 100 unique supported loci against all Parquet genetic inputs in one local DuckDB join. This is independent of frontend preview limits. Match by rsID or GRCh38 coordinate, allowing calls without an rsID.
4. Resolve only complete, nonconflicting A/C/G/T genotypes with matching GRCh38 coordinates. Conflicts, no-calls, rsID/location disagreements and GRCh37 matches stay unresolved. GRCh37 coordinate-only matching requires a future explicit remapping adapter.
5. Record the actual numbers checked, observed, unresolved and not observed, with sources, retrieval date and limitations. The findings reach specialists, coordinator and evidence reviewer. Genomics activity appears in chat.

The `investigate_trait` agent tool supports other exact catalogue trait names; ambiguous ontology searches return choices rather than silently switching phenotype. At most two distinct traits are investigated per question, and repeated requests reuse the same local result. The automatic heart-rate step prevents the model from skipping the lookup and saying merely that it was not evaluated.

## Data boundaries and interpretation

Only a short trait term is sent to the public catalogue. The genotype matching in this tool runs locally; uploaded genotype values and personal history are not sent to GWAS Catalog. External lookup follows the active profile's external-analysis consent. Public responses can be cached for seven days; personal results are recomputed from the active profile. The rest of the existing consented chat pipeline still sends its bounded supplied context to the configured language-model provider.

A matched association locus is not a clinical classification or evidence that a measured heart rate is genetic. Study effect alleles are not strand/allele harmonized here: **no personal direction, bpm shift, disease probability or PRS is calculated**. Nearby/overlapping mapped genes are not necessarily causal. LD proxies, rare-disease screening, imputation and ancestry calibration remain outside scope. Missing calls are unknown, never manufactured reference or negative results.

## Demo and failure behavior

Alex's expanded demo contains 22 actual GIAB calls, including four measured heart-rate loci; Sam has 26 calls including seven. The original regional subsets are preserved and supplemented with additional measured PASS calls from the same GIAB identities. The dated catalogue has nine supported unique loci. A lookup reports the actual observed and unmeasured counts, in direct I/you voice. Missing calls are never filled in to create a positive result. See [covered demo examples](DEMO_GUIDE.md).

When live retrieval fails, heart-rate questions use the explicitly dated public snapshot in `api/trait_catalog_data/heart_rate.json`, with a visible disclosure. Evidence-only mode also uses this snapshot locally. Its manifest records the source URL, original response hash, filtered snapshot hash, date and selection rules. Other traits without an available catalogue return an unavailable/ambiguous result; a service failure is not a negative genetic result.

Refresh deliberately with:

```bash
.venv/bin/python -m api.prepare_trait_catalog
```

Review the changed source records and manifest before distributing an updated snapshot. This command performs no fitting and uses no synthetic participant data.

## Answer voice

The shared prompts now require **I/you** voice. Demo identity remains in the UI and source evidence; opening every answer with a persona's name or referring to the assistant as “this app” is discouraged. Biological source separation is still enforced: the assistant must not claim that independent public DNA/wearable donors are one real person or establish a causal link between them. New answers use this policy; saved historical answers remain the original records.

## Primary documentation

- [GWAS Catalog v2 overview](https://www.ebi.ac.uk/gwas/rest/api/v2/docs).
- [Official API schema](https://www.ebi.ac.uk/gwas/rest/api/v2/rest-api-doc.yaml).
- [GWAS Catalog FAQ: genome assembly and association interpretation](https://www.ebi.ac.uk/gwas/docs/faq/).
