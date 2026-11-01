# Covered public-data demo

Open **Explore covered demo examples** at the top of the workspace. Existing public demo sessions receive these examples on refresh; private workspaces are unchanged.

| Example | What to show | Actual supplied data |
| --- | --- | --- |
| Joint & molecular | Select rs143383, run AlphaGenome or Evo 2, discuss its interpretation | Alex: original HG002 GDF5 G/A call plus source-verified GIAB heart loci, 22 total DNA calls |
| Heart rate & wearables | Ask “Could my genes help explain my resting heart rate?” | Sam: 26 actual HG003 calls, including seven covered published heart-rate loci; 90 public Fitbit observations from PMData p01 |
| Family inheritance | Compare NA12043 with the preselected NA20332 | Both have measured G/A at PAH rs5030858 in 1000 Genomes Phase 3, surfaced through Ensembl; conditional 25% two-assessed-allele probability |
| Methylation report | Explain/export the research age estimate | GSM1009666: 71 unchanged whole-blood methylation values and recorded age 21 |
| Repeat methylation | Show the time chart and sample reports | GSM1886929 / GSM1886935: the same GSE73115 Individual 1 in 1997 and 2007, all 71 clock sites in each sample |

## Why the previous family view was unknown

PMData is a wearable dataset, with no genotypes. Alex/Sam's original small GIAB subsets did not report the three specific clinical alleles in the family panel. A missing row in a variant-only VCF is not evidence of a reference genotype. These were missing data, not negative carrier tests.

The selector now disables profiles with no genetic data. Completely uncovered conditions are summarized in a disclosure instead of displayed as large “Unknown” cards. The **Use measured carrier example** shortcut opens the real PAH example. CFTR and HEXA remain unmeasured for that pair; those genotypes are not manufactured. This is one allele per condition, not comprehensive carrier screening.

The two public PAH samples are a hypothetical pairing, not a known couple. Both raw genotype observations require clinical confirmation before reproductive decisions. No pregnancy outcome, disease severity or compatibility score is predicted.

## Sources and transformations

- Original GIAB v4.2.1 genotype subsets are preserved. Additional measured PASS SNVs were extracted at the nine supported loci in the dated GWAS heart-rate catalogue: HG002 adds 4, HG003 adds 7, HG004 adds 3. Missing sites remain missing. Each added rsID was checked against a forward-strand GRCh38 Ensembl mapping with compatible alleles. Source VCF values and quality are retained.
- PAH calls come from the original Ensembl response for `rs5030858?genotypes=1`: NA12043 `G|A`, NA20332 `G|A`. The unique forward-strand GRCh38 `G/A` mapping at chr12:102840493 was verified. No CFTR/HEXA calls or quality scores are invented.
- PMData dates and observations remain unchanged. Both fictional Alex/Sam personas still use p01's independent wearable series; a real-person genotype–wearable association is not established.
- The single blood-age example retains its original source identity. It is separate from the DNA and wearable donors.
- The repeat source is **GSE73115**, Individual 1: **GSM1886929 (1997)** and **GSM1886935 (2007)**. All 71 model-site values are unchanged, and their reported detection p-values are zero. The study reports a baseline cohort age range of 73–82 and a ten-year follow-up; individual age and exact collection days are not supplied. The report therefore shows cohort ranges and no individual calendar-age difference. The timeline uses the actual reported years, without invented days or birthdays.
- The two samples share the published tissue, array and processing protocol. Raw QC and cross-batch equivalence were not independently validated. Their model outputs (approximately 78.7 and 79.0 years) are descriptive, not evidence that ten calendar years produced only 0.3 years of biological aging. No meaningful-change threshold or intervention effect is calibrated.

Reproducible snapshots and hashes:

- `api/demo_cases/bundle.json` and `manifest.json`; prepare with `.venv/bin/python -m api.prepare_demo_cases`. Source caches are in ignored `data/public-sources/demo-cases/`.
- `api/repeat_demo/bundle.json` and `manifest.json`; prepare with `.venv/bin/python -m api.prepare_repeat_demo --source-folder /path/to/original-GEO-SOFT-files` containing `GSM1886929.soft` and `GSM1886935.soft`.
- Existing genotype, wearable and single-blood snapshots retain their original manifests. Startup does not download data or silently replace it with synthetic values.

The public samples collectively exercise the current workflows. They are not one real person's combined genome, wearables and methylation history. Saved chats and original source profiles are preserved during the idempotent demo upgrade.

## Primary links

- [GIAB release](https://www.nist.gov/programs-projects/genome-bottle).
- [Ensembl sample genotypes for the measured PAH allele](https://rest.ensembl.org/variation/human/rs5030858?genotypes=1&content-type=application/json).
- [PMData](https://datasets.simula.no/pmdata/).
- [GSM1009666 blood sample](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM1009666).
- [GSE73115 longitudinal source](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE73115), [1997 sample](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM1886929), [2007 sample](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM1886935).
- [Primary study describing the cohort and age range](https://pmc.ncbi.nlm.nih.gov/articles/PMC5557932/).
