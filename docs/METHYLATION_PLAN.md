# Optional methylation report: implemented scope

Strand now turns a compatible processed beta export into a reproducible **research methylation-age report**. It explains incomplete samples rather than inventing a score. DNA sequencing remains sufficient for the rest of the app.

## Customer experience

1. Upload measured methylation with tissue, assay, assembly, collection date, age at collection, preprocessing and a laboratory QC reference.
2. See a readiness checklist and the exact missing CpG identifiers. Unsupported samples retain their measured-site explorer.
3. When all checks pass, see a Hannum age estimate, recorded age and their descriptive difference, with sources, uncertainty and useful next steps.
4. Export the report as JSON, including metadata and coefficient version/hash, or discuss it with the agents.
5. Add comparable repeat samples to see descriptive score differences. No improving/worsening labels or intervention effects are inferred.

The actionable value is understanding what a laboratory result can support, keeping an inspectable baseline and deciding what additional evidence is needed. A clock difference does not select a diet, supplement, exercise or treatment. Wearables remain a separate source of observed sleep/activity trends; they cannot explain the cause of a methylation change.

## Supported model and inputs

- **Hannum 2013**, adult human whole blood, Illumina 450K processed beta exports. All **71 required CpGs** must be present and finite in `[0,1]`. No imputation.
- Record age at collection within the development range of **19–101**, rather than using today's profile age for an older specimen.
- Document preprocessing and a passing laboratory QC report reference. This is user-reported information, not independently verified laboratory QC. Public research demos explicitly use a separate limited-QC status.
- Other tissues, cell lines, EPIC versions, incomplete panels or missing metadata receive an explanatory readiness report without an age estimate. Data can still be explored.
- Raw IDAT preprocessing, detection-p-value/control-probe checks and cell-mixture correction are **not implemented**. This MVP uses the processed-export path from the original plan. A full raw-array path would require a separately validated `minfi` workflow.

The deterministic Python adapter uses pinned Biolearn coefficients at commit `0d714f5a0c0ad5743b6315f3edab1f86112d394f`. It sums `coefficient × beta` across the 71 model sites, with identity transform and no intercept. The BSD-3-Clause attribution is retained. Runtime checks the coefficient hash. Scoring reads all required sites from Parquet independently of the 2,000-row chart preview.

Files: `api/methylation.py`, `api/methylation_models/manifest.json`, `api/methylation_models/Hannum.csv`, `api/methylation_models/LICENSE.biolearn`.

## Repeat-test checks

Two samples must pass the report checks and have matching subject ID, tissue, assay, preprocessing and a laboratory-confirmed comparability group. Both need distinct actual collection dates, with ages consistent with elapsed time. Identical model inputs are flagged as a possible duplicate export. Missing/unknown dates do not form a timeline; incompatible dated pairs show the reasons comparison is blocked.

The output is elapsed calendar time and a **descriptive score change**. No personal confidence interval or meaningful-change threshold has been calibrated. Technical replicates and batch bridging are needed before interpreting small changes; different scores alone do not establish faster aging, rejuvenation or an intervention effect.

## Real public example and evaluation

The **Explore a public blood report** button opens **GSM1009666**, a documented control in **GSE41169**, in its own profile. Its 71 original beta values are unchanged. Recorded age is 21; the pinned model gives approximately 25.8 years. This difference is not a health rating. Collection date is unreported and remains unknown; submission/publication dates are not substituted. No repeat sample, symptoms, raw QC or matched DNA/wearables are invented.

The original HG002/GM24385 sample remains a regional research explorer: 407 measured cytosine positions in a roughly 10 kb GDF5 region from a lymphoblastoid cell line. It contains zero named Hannum model probes and cannot support this clock. A fictional persona does not change those biological limits.

`api/methylation_demo/validation.json` records the retrospective evaluation:

- All 95 cohort samples retained; four lack required model values and two additional samples fall outside the adult scope, leaving 89 eligible complete samples.
- MAE against recorded age: **2.9759 years**; median absolute error **1.9518**; mean signed error **+0.3533**.
- Exact reference parity for 10 upstream Biolearn samples, maximum absolute arithmetic difference approximately `3.55e-15` years before API rounding.
- Sex and cohort-group errors are reported with sample counts. These are limited descriptive subgroups, not a fairness or generalizability claim.

No parameters were fitted or tuned on this cohort. This is a reproducibility/error check, **not independent clinical validation**; overlap with original development donors has not been audited. Raw intensities are unavailable, and there are no technical replicates or longitudinal pairs in this snapshot. No individual error interval is derived from the cohort MAE. Customer laboratory pipelines, EPIC, saliva and clinical outcomes remain unevaluated.

To rebuild after downloading the original matrix:

```bash
.venv/bin/python -m api.prepare_methylation_demo --matrix /path/to/GSE41169_series_matrix.txt.gz
```

The manifest records the original source URL, compressed matrix hash, selection rules and output hash. Startup uses the checked-in bounded snapshot without downloads.

## Agents and molecular tools

The genomics agent reads the deterministic report and sample metadata; the coordinator/evidence reviewer explain scope and next steps. The evidence-only fallback also uses the actual report. Numeric scores do not come from LLM arithmetic. AlphaGenome/Evo 2 investigate sequence effects separately and do not substitute for measured methylation. No H100 or foundation-model training is needed for this report.

## Primary references

- [Hannum et al., Molecular Cell 2013](https://www.sciencedirect.com/science/article/pii/S1097276512008933).
- [Pinned Biolearn implementation and coefficients](https://github.com/bio-learn/biolearn/tree/0d714f5a0c0ad5743b6315f3edab1f86112d394f).
- [GEO GSE41169](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE41169) and [GSM1009666](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM1009666).
- [minfi user guide](https://www.bioconductor.org/packages/release/bioc/vignettes/minfi/inst/doc/minfi.html).
- [Higgins-Chen et al., Nature Aging 2022](https://www.nature.com/articles/s43587-022-00248-2): technical reliability of methylation clocks.

## Additional measured repeat example (2026-11-01)

The covered demo also includes GSE73115 Individual 1, GSM1886929 (1997) and GSM1886935 (2007), with all 71 model sites. The primary study provides cohort age ranges (73–82 at baseline, 83–92 at follow-up), not individual ages. Public-source reports can establish adult model scope from a cited cohort range while leaving individual age and calendar-age difference null. Year-only collection times are retained as years, and the comparison reports ten calendar years without inventing collection days. Shared published protocol is disclosed; raw QC and batch equivalence are not independently validated. See [the demo guide](DEMO_GUIDE.md) for provenance and limits. The output is descriptive and does not imply a biological aging rate.
