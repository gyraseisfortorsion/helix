# Public demo data and provenance

The initial Alex/Sam demo was generated in `api/demo.py`: genotype combinations were chosen by code, wearable values were seeded random numbers, and methylation used fictional probe IDs. It was a software test fixture. Its variant IDs/coordinates and supporting literature were real public references, and the AlphaGenome/Evo 2 predictions were real model executions. The fixture measurements were not evidence of biological accuracy.

**The default demo uses bounded subsets of public research datasets, with two explicitly fictional combined personas shown first.** The original synthetic Alex/Sam fixtures remain available only through explicit `demo_source: "synthetic"` sessions and automated/manual software tests. New/default sessions use `demo_source: "public"`. Existing private workspaces are preserved.

## Combined personas for the product demo

- **Alex Morgan · combined demo**: HG002 genotypes plus PMData p01 wearables. Fictional age 31 and a knee-discomfort scenario.
- **Sam Chen · combined demo**: HG003 genotypes plus the same PMData p01 wearable series. Fictional age 30 and a resting-heart-rate question.

Both names, ages and histories are invented. Both personas deliberately reuse p01's 90 observations; they are not two independently measured wearable participants. Source genotype values, wearable values and March 2020 dates are retained exactly. The fictional scenario is set on March 31, 2020, to avoid presenting historical wearable records as current measurements. This composition demonstrates the interface and agent workflow; it does not establish a real person's combined health history or a genotype–wearable association.

The chat interprets first-person questions as referring to the selected persona, uses its scenario and available measurements, and states the demo context briefly. Source disclosures remain visible in the profile and evidence cards. Genetic susceptibility and observed activity/recovery remain separate forms of evidence, with no inferred causal link. Alex can optionally load the HG002 methylation sample; no methylation is required.

The four original source profiles below remain unchanged and separate. Existing public demo sessions receive the two personas on reload through an idempotent authenticated upgrade; source-profile chats are preserved. No private workspace is modified.

## Genotypes: NIST Genome in a Bottle v4.2.1

| Profile | Public sample | Role | Included observed SNVs |
| --- | --- | --- | --- |
| HG002 | HG002 / NA24385 / GM24385 | Son | 18 |
| HG003 | HG003 / NA24149 / GM24149 | Father | 19 |
| HG004 | HG004 / NA24143 / GM24143 | Mother | 13 |

Source: [NIST GIAB](https://www.nist.gov/programs-projects/genome-bottle), [sample identities and pedigree](https://catalog.coriell.org/1/NIGMS/Collections/NIST-Reference-Materials), [GIAB publication/use FAQ](https://www.nist.gov/programs-projects/faqs-genome-bottle).

Extraction uses original GRCh38 v4.2.1 benchmark VCFs. The selected zero-based, half-open windows are chr20:35430000–35445000, chr7:117587300–117588300, chr12:102840000–102841000 and chr15:72350000–72351000. Only PASS biallelic SNVs are retained. Actual genotype, phasing and QUAL are preserved; rs143383 is annotated by exact assembly/coordinate/reference/alternate match.

These are **small variant-only subsets**, not complete genomes or clinical carrier screens. No 0/0 calls are manufactured for absent variants. The three rare alleles in the current family panel are not observed in these subsets, so the public family demo reports unknown/unassessed rather than inventing a positive 25% result. The explicit synthetic fixture remains useful for testing that conditional inheritance calculation.

The source data genuinely contain G/A at rs143383 in HG002 and HG003, and A/A in HG004. No personal knee symptoms, age, lifestyle, diet or clinical outcomes are assigned to these reference samples. They are research cell-line genomes.

## Optional methylation: HG002/GM24385

Source: Oxford Nanopore's [GM24385 modified-base data release](https://epi2me.nanoporetech.com/gm24385-5mc/) and its [modified-base tutorial](https://epi2me.nanoporetech.com/notebooks/Modified_Base_Tutorial.html). The tutorial publishes chromosome-20 Bismark bisulfite sequencing measurements.

The bundled optional sample contains **407 measured cytosine sites** in the zero-based chr20:35433000–35443000 window around GDF5. Sites require at least ten reads. Beta is calculated from the published methylated and unmethylated read counts:

`beta = methylated_reads / (methylated_reads + unmethylated_reads)`

BED coordinates are converted to one-based site labels. The labels are genomic cytosine positions, not invented Illumina probe IDs. Zero-depth sites are excluded. The original counts are retained in the compact source bundle.

This is the same public **cell-line identity** as the HG002 genome, from a separate experiment/batch. It is not paired cartilage data, a measurement from the app user, or a basis for a health/biological-age score. Collection date is not reported and is not invented. The optional sample attaches only to the HG002 profile and starts absent.

The provider makes these measurements publicly accessible for research. The cited release does not state a separate dataset redistribution license; no blanket CC license is asserted here.

## Wearables: PMData p01

Source: [PMData dataset](https://datasets.simula.no/pmdata/), [original OSF repository](https://osf.io/vx4bk/), Thambawita et al. 2020, [doi:10.1145/3339825.3394926](https://doi.org/10.1145/3339825.3394926).

The bundled profile contains **90 daily observations**: resting HR, steps and sleep for the latest 30 dates with all three metrics present in p01's original files. The retained range spans **March 1–31, 2020**, including a missing day. Dates are not moved to the present.

- Resting HR comes directly from `resting_heart_rate.json`.
- Steps sum the available minute records from `steps.json`; missing minutes are not filled in.
- Sleep sums `minutesAsleep` from distinct sleep-log IDs per recorded date.
- Original calendar dates are retained. UTC noon is a display convention, because the source records do not establish a sensor timezone.

The displayed latest resting HR is about **52.56 bpm**, with a **50.62 bpm** historical median across **27** prior dates in the 28-day window. These values reflect the transformed public data, not fabricated fitness scenarios.

PMData p01 is an **independent participant with no supplied DNA**. The original PMData profile stays separate from the original GIAB profiles. Copies are used in the explicitly fictional combined personas described above; the app does not claim those unrelated records are measurements from one real person.

The downloaded [dataset license file](https://osf.io/download/ywdvx/) states **CC BY-NC 4.0**. The publisher page/OSF project-level metadata currently list CC BY 4.0, so this snapshot follows the more restrictive file-level terms and preserves attribution. Changes made: daily aggregation and bounded date selection. License: https://creativecommons.org/licenses/by-nc/4.0/.

## Reproduce and inspect

Run from the repository root:

```bash
uv run --all-extras python -m api.prepare_public_demo
```

This explicitly downloads/retrieves the original public sources and creates the bounded snapshot. Normal app startup reads the committed snapshot offline; it never silently substitutes synthetic data.

- `api/public_demo/bundle.json`: retained actual values, source metadata and transformations.
- `api/public_demo/manifest.json`: exact upstream URLs, versions, SHA-256 hashes and citations.
- `data/public-sources/`: ignored download/cache directory.

GIAB hashes cover the exact extracted VCF/header, not the full upstream VCF. Other hashes cover the downloaded source files. Preparation checks existing source hashes before rebuilding; the runtime verifies the compact bundle hash. No model performance or clinical accuracy is established by these provenance checks.

## Optional blood methylation report: GSE41169

The separate **GSM1009666 · public blood sample** profile is created on demand by **Explore a public blood report**. It uses the first adult control in original GEO source order, with its recorded age (21) and 71 original Hannum model beta values. It is not HG002, an app user or the PMData participant. No collection date or repeat sample is available.

Source: [GEO GSE41169](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE41169). Original matrix: `https://ftp.ncbi.nlm.nih.gov/geo/series/GSE41nnn/GSE41169/matrix/GSE41169_series_matrix.txt.gz`. The series documents BeadStudio v3.2 processing and the unavailability of raw methylated/unmethylated intensities. The report explicitly identifies this limited-QC processed research source. No raw QC pass is invented.

`api/methylation_demo/bundle.json` preserves model-site values for all 95 samples; absent values stay absent. `manifest.json` records the original matrix hash and snapshot hash. `validation.json` records 89 complete eligible adult samples, error metrics, limited subgroups and parity with ten upstream Biolearn reference outputs. See [implemented scope and evaluation](METHYLATION_PLAN.md).

Reproduce with `.venv/bin/python -m api.prepare_methylation_demo --matrix /path/to/GSE41169_series_matrix.txt.gz`. The app reads the bounded snapshot offline. No special redistribution license beyond the public GEO source is asserted. Pinned Biolearn coefficient licensing/attribution is preserved separately in `api/methylation_models/LICENSE.biolearn`.

## Expanded covered examples (2026-11-01)

The original source subsets above remain intact. A separate checked snapshot adds 4/7/3 actual GIAB heart-rate-locus calls to HG002/HG003/HG004 respectively, two measured PAH heterozygotes from 1000 Genomes Phase 3, and a same-donor 1997/2007 whole-blood methylation follow-up from GSE73115. Public sessions are upgraded idempotently; source identities and saved chats are preserved. See [the complete demo guide](DEMO_GUIDE.md) for exact samples, site selection, transformations, limitations and reproduction commands.
