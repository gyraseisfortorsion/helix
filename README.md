# Strand — your biology, in context

A research workspace for genetic questions, evidence-linked lifestyle guidance, wearable trends, and a limited paired-profile inheritance comparison. **DNA is the starting input. Methylation is entirely optional.**

The interface follows the supplied [Figma Make source](<figma mockup/src/App.tsx>), including its Strand branding, paper palette and evidence drawer. Existing Helix API commands and workspace identifiers are retained. See [design integration](docs/DESIGN.md).

## Run locally

Requires Python 3.12, `uv`, and Node 22.12+.

```bash
cp .env.example .env
uv sync --all-extras
uv run --all-extras helix-api
```

In a second terminal:

```bash
cd web
npm ci
npm run dev
```

Open **http://localhost:5173**. The API is at http://127.0.0.1:8000; interactive API documentation is at `/docs`.

The default demo opens fictional **Alex/Sam combined profiles**, each with public-source DNA and wearable measurements. Alex uses HG002 DNA, Sam uses HG003 DNA, and both reuse the PMData p01 wearable series. Names, ages and symptom scenarios are invented; source values and March 2020 dates are preserved. These are product demonstrations, not matched observations from one real person. The original GIAB (HG002/HG003/HG004) and independent PMData profiles remain available. HG002 and the Alex persona can optionally load the matching HG002 methylation subset; it starts absent. See [public data provenance](docs/PUBLIC_DATA.md). The earlier fully synthetic fixtures remain only for explicit test sessions.

Use **Use my data** to create a private workspace, then a profile and upload. Local private-workspace creation permits an empty access key only from loopback. Set `DNA_ACCESS_KEY` and `DNA_ALLOW_LOCAL_WORKSPACES=false` before exposing the backend to a network. Sessions last eight hours and are scoped to the browser tab. This is a research prototype, not a production identity/account system.

## What works without provider keys

- DNA-only profiles and streaming VCF/VCF.gz, Ancestry, and 23andMe imports.
- Curated, deterministic evidence-library answers, explicitly labeled as such.
- Wearable CSV ingestion, daily summaries, historical baselines, and charts.
- Conditional paired-profile calculations for three specified alleles in CFTR, PAH, and HEXA.
- Optional processed methylation reports: published Hannum clock with strict input checks, source-labeled blood demo, export, chat interpretation and guarded repeat comparison.
- Workspace isolation, import reports, run events, and JSON evidence exports.

No live AI, reference model predictions, or simulated molecular results are presented when a provider is unavailable.

## Connect live providers

Set credentials only in the root `.env` or backend environment:

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Enables PydanticAI genomic, health-trend, synthesis and evidence-review agents |
| `DNA_LLM_MODEL` | Defaults to `anthropic:claude-sonnet-5-5`; set to a model available in your funded account |
| `ALPHAGENOME_API_KEY` | Enables regulatory predictions and live supported-context discovery; separate from AI Studio |
| `EVO2_FORWARD_URL` | Complete hosted forward URL; takes precedence over `EVO2_BASE_URL` |
| `EVO2_BASE_URL` | Origin of your self-hosted Evo 2 NIM service supporting `/biology/arc/evo2/forward` |
| `EVO2_ACCESS_TOKEN` | NVIDIA API key for hosted forward calls, or optional gateway bearer token for self-hosting |
| `DNA_REFERENCE_GRCH37`, `DNA_REFERENCE_GRCH38` | Optional indexed reference FASTA paths for native VCF normalization and allele validation |

Also enable **external analysis** in the profile settings. Only selected calls and relevant context are sent to providers; whole genotype files remain on the backend. Treat rare variant queries and health summaries as sensitive even when the full file stays local.

With no consent or no Anthropic key, the chat uses the evidence library. It does not impersonate live agents. Molecular actions require a configured provider, consent, resolvable alleles, and a valid reference mapping.

### Evo 2 / BioNeMo

See the [Evo 2 setup guide](docs/EVO2_SETUP.md) for both options. NVIDIA's current API reference documents a hosted **7B forward** endpoint; try it with a model-enabled NVIDIA API key before provisioning a GPU. The installed skill's older hosted-generation-only guidance does not cover that endpoint. Authenticated hosted access and a complete 8,192-base reference/alternative investigation have been verified through the browser using synthetic data. The hosted server uses the native `unembed` layer and `[batch, sequence, 512]` logits; the adapter handles this separately from self-hosted NIM 2.x `output_layer` tensors. For self-hosting, select **7B** explicitly for one H100 80GB; the default 40B variant needs more GPU memory. Keep the raw NIM private behind a tunnel or authenticated gateway. `NGC_API_KEY` and `LOCAL_NIM_CACHE` belong on the GPU host.

The score is mean autoregressive sequence log-likelihood, averaged over forward and reverse-complement sequences. Local tests check token shifting, vocabulary indices, both hosted/self-hosted tensor layouts, rejection of non-finite outputs, and reference coordinate/assembly validation. Evo 2 sequence windows are fetched from UCSC hg38, with the selected allele validated against the reference base. **Live hosted inference is available; parity with the corresponding official scorer/checkpoint and self-hosted GPU execution remain unverified.** It is not an expression direction or disease probability.

### AlphaGenome

Uses the official SDK, explicit `ALL_FOLDS` model selection, reference/alternative predictions and the service's supported-context metadata. RNA/accessibility plots show normalized model signals for that context, not measurements of the user. Live inference and all six returned tracks were verified using the synthetic GDF5 demo call in HepG2. That liver-cell check verifies integration; it does not establish relevance to knee symptoms. Completed investigations are available as prediction evidence in subsequent chat answers.

## Input formats

Format examples are downloadable from the upload dialog or `/api/templates/{genetics,wearables,methylation}`.

**Genetics:** single-sample VCF or supported genotype text, with the provider's actual GRCh37/GRCh38 assembly selected. No-calls stay unknown. Missing records in a variant-only VCF are never considered confirmed reference calls. Structural variants and unresolved array indels are excluded. Without a configured reference FASTA, indel normalization is explicitly pending; molecular SNVs undergo separate reference validation before scoring.

**Wearables:** CSV columns `timestamp,metric,value,unit,source,context`. Supported metrics: `heart_rate`/`resting_heart_rate` in `bpm`, `steps` in `count`, and `sleep_duration` in `minutes` or `hours`. Include explicit offsets where possible. Resting and exercise observations are separated. The latest `daily_total`/`nightly_total` takes precedence over interval counts for that source/day; daily values from multiple sources use their median. Conflicting simultaneous values are excluded and reported. The baseline requires seven historical days and excludes the latest day.

**Optional methylation:** CSV columns `cpg_id,beta`, optionally `chrom,position`. Enter tissue, assay, assembly and collection date. Beta values must be finite and within `[0,1]`; duplicate probes are rejected. A pinned Hannum 71-CpG research age estimator supports adult whole blood on Illumina 450K when all required sites, age at collection, preprocessing and laboratory-reported QC are supplied. Additional metadata: `age_at_collection`, `preprocessing`, `qc_status=lab_reported_pass`, `qc_reference`; repeat comparisons also need `subject_id` and `comparability_group`. Unsupported inputs remain explorable without a score. Raw IDAT processing, cell-mixture correction and treatment inference are not implemented.

## Family comparison limits

The current catalogue assesses **three named GRCh38 alleles**, not three complete genes: CFTR rs75527207 G>A; PAH rs5030858 G>A; HEXA rs121907954 C>T. Clinical references are linked in the UI. Only a compatible pair of observed heterozygous calls produces the conditional 25% affected-genotype illustration. Other cases remain unresolved rather than showing zero overall risk. The module does not predict severity, rank partners, handle all inheritance patterns, or replace clinical confirmation and genetic counseling.

## Verification

```bash
uv run --all-extras pytest -q
uv run --all-extras ruff check api tests
cd web
npm run build
npm exec playwright install chromium
# Starts separate test servers with provider keys disabled:
npm run test:e2e
```

The suite currently has 101 backend checks and twenty browser journeys. It covers no-calls, multiallelic records, assembly mismatches, indel normalization, methylation bounds, conditional inheritance, cross-workspace access, deletion, missing-provider behavior, the review/revision gate and Evo 2 tensor handling. Browser checks cover chat, trends, family comparison, actual file upload without methylation, optional sample exploration, and mobile layout. Live Anthropic specialist/synthesis/review execution and live AlphaGenome predictions were checked separately using synthetic data, including browser rendering of reviewed answers and all six molecular tracks. The MPRA scoring/evaluation adapter also completed a four-public-variant integration check. The public-data demo was also checked with a live reviewed chat answer grounded in the actual HG002 genotype and measured methylation. These are integration checks, not clinical validation.

Manual checks, exact expected outcomes and fabricated upload files are in [MANUAL_TESTS.md](docs/MANUAL_TESTS.md).

## Conversations and reliability

Each profile has separate saved conversations. **New chat** starts an independent conversation; the sidebar or **Chats** button reopens previous messages. Suggestions sit above the composer. Questions, answers, run state and events are stored in SQLite and restored after refresh. Existing chat jobs are migrated into conversations without deleting their messages. History remains scoped to the authenticated workspace; the prototype still uses eight-hour, browser-tab sessions rather than production accounts.

The live pipeline uses bounded history, only cited prior evidence, limited literature calls and a bounded token budget. Invalid citation IDs trigger one correction attempt. A budget, timeout or evidence-review failure returns an explicitly labeled, limited evidence-library answer with a notice; it never publishes the rejected draft as reviewed AI. The latest failed/fallback answer can be retried without duplicating the question. Interrupted worker runs are marked retryable after restart.

Measured calls without an rsID are labeled by genomic position and REF/ALT alleles. Supported GRCh38 SNVs can be investigated by coordinate identity; the uploaded reference is checked against hg38 before model inference. Clicking Investigate brings the controls into view and focuses the selected variant.

Molecular investigation eligibility is shown before submission. A reference-only call such as G/G with reference G has no observed alternative to compare. Missing calls, multiple different alternatives and unsupported indels are explained; homozygous alternative calls such as A/A with reference G remain eligible. Conflicting imports are not resolved by arbitrarily picking the first record.

See [the optional methylation implementation and limits](docs/METHYLATION_PLAN.md) for supported inputs, published model, provenance, retrospective evaluation and the remaining raw-QC/clinical-validation work. In Methylation, **Explore a public blood report** opens a separate real GEO sample; it is not attached to a fictional persona or matched to its DNA/wearables.

## Retrospective molecular benchmark

```bash
uv run --all-extras python -m api.benchmark prepare
# Requires ALPHAGENOME_API_KEY; reads test inputs, not the label file:
uv run --all-extras python -m api.benchmark predict
uv run --all-extras python -m api.benchmark evaluate
```

Preparation downloads the Kircher et al. 2019 saturation-mutagenesis dataset, checks its hash in the manifest, and selects 30 covered GRCh38 SNVs per element with seed 42. LDLR is development; F9 and SORT1 are evaluation. Inputs and labels are separate files. The fixed model baseline uses the median matching HepG2 RNA GeneMaskLFC score. Evaluation reports coverage, Spearman correlation and directional agreement.

This is a retrospective reporter-assay benchmark, not a clinical endpoint or evidence of novel generalization. Full benchmark accuracy and single-/multi-agent comparative effectiveness have not been established. Never describe reduced hallucination or improved accuracy as established solely from software or provider integration checks.

Source: [Kircher et al. data portal](https://kircherlab.bihealth.org/satMutMPRA/), doi:10.1038/s41467-019-11526-w. Cite the original work if sharing benchmark artifacts.

## Deployability

For the ready-to-run **VPS backend + Vercel frontend** setup, follow [VPS deployment](docs/VPS_DEPLOYMENT.md). On a fresh VPS, clone this repository, copy `deploy/vps.env.example` to `.env`, set the backend hostname and provider keys, and run `docker compose --profile https up -d --build --wait`. This starts FastAPI with its worker, persistent storage, and Caddy for HTTPS.

The frontend is static (`web/dist`) and can deploy independently to Vercel or GCP. Set `VITE_API_BASE_URL` at build time to the HTTPS backend origin; no provider secret belongs in a `VITE_` variable. Do not proxy large genomic uploads through frontend functions.

The backend Dockerfile targets an always-on host with a persistent `/data` volume. `compose.yaml` supplies a local example. Set a private workspace access key, exact CORS origins, and turn off loopback workspace creation for hosting. The default API includes one background worker. To use a separate `helix-worker`, set `DNA_EMBEDDED_WORKER=false` on the API and run exactly one worker against the same data volume. SQLite is intentionally single-host; horizontal scaling requires a different persistence design.

The `helix` Vercel project is connected to this repository with `web` as its root directory. Its current `/api/*` rewrite targets the deployed VPS at `http://34.31.166.71`; leave `VITE_API_BASE_URL` empty for this mode. The browser talks HTTPS to Vercel while Vercel forwards to the HTTP backend. For direct HTTPS access, set `VITE_API_BASE_URL` to a trusted HTTPS backend origin and redeploy. Provider credentials belong on the backend host; the older encrypted values in Vercel do not configure the VPS and are never exposed through `VITE_` variables.

### Question-driven genetic lookup

Heart-rate questions now run a required GWAS Catalog association lookup and local genotype check before the answer is composed. The genomics agent also has an `investigate_trait` tool for other exact trait names. Results report observed loci, unresolved calls and missing coverage, with source dates and an explicit public-snapshot fallback. This is a bounded association lookup, not a PRS or a diagnosis. Chat uses direct I/you voice. See [trait lookup design and limits](docs/TRAIT_LOOKUP.md).

### Covered public demo examples

The public demo now includes four additional HG002 heart-rate calls (22 total for Alex), seven HG003 heart-rate calls (26 total for Sam), two actual 1000 Genomes PAH heterozygotes for conditional inheritance, the existing single-blood methylation report and a genuine 1997/2007 same-person methylation pair. **Explore covered demo examples** switches to the appropriate source/profile. Wearable-only partners are disabled; uncovered family conditions remain unassessed in a compact disclosure. See [demo walkthrough and provenance](docs/DEMO_GUIDE.md).
