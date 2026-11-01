# Manual end-to-end checks

Open http://127.0.0.1:5173 and refresh after a backend restart. All example files in `examples/manual/` are fabricated test data, not actual people or biological measurements. Private uploads are labeled as uploaded by the app, so name test profiles **Synthetic A**, **Synthetic B**, etc. and write **Synthetic test data** in their history. AI wording may vary; assess the stated evidence and limits rather than an exact sentence.

## Default public-data demo

The default session uses real public subsets in explicitly fictional combined personas, with original source profiles also available. See [PUBLIC_DATA.md](PUBLIC_DATA.md) for sources, sample identity, transformations and licensing.

1. Refresh the app. **Alex Morgan · combined demo** and **Sam Chen · combined demo** appear first, including in an existing public session. Both have DNA and 90 wearable observations; source-profile chats remain available.
2. On Alex, ask **Could my knee pain be genetic? How does my activity fit in?** The answer should briefly frame Alex's demo scenario, use the G/A rs143383 call and relevant March 2020 activity measurements, and distinguish susceptibility from an explanation of pain. It should not dismiss the question with “this profile isn't you” or “no age/symptoms supplied.”
3. On Sam, ask **Why is my resting heart rate higher? Can my DNA explain it?** Expect actual latest/baseline values (52.56/50.62 bpm), without a claim that DNA explains or validates the difference. Both personas intentionally reuse p01, as disclosed; these are not two independent wearable histories.
4. Alex's methylation starts absent and can optionally load the HG002 sample. Sam cannot load that sample. The original source profiles below remain unchanged.

### Original source profiles

1. Refresh the app. Default profiles are HG002 (18 observed SNVs), HG003 (19), HG004 (13), and PMData p01 (wearables only). Source links should be visible. Ages and clinical histories are not invented.
2. On HG002, search Genetic findings for `rs143383`: the actual public call is G/A. Run AlphaGenome or Evo 2 as before. HG003 also has G/A; HG004 has A/A.
3. Ask about the GDF5 result. The answer should identify a public cell-line reference genotype, not diagnose a donor's or user's knees.
4. HG002 has no wearable records. Switch to PMData p01 for three real wearable charts. Latest RHR is about 52.56 bpm; historical median is 50.62 bpm across 27 prior dates. Dates remain in March 2020.
5. On HG002, methylation starts empty. Choose **Explore HG002 public methylation**: 407 measured sites should appear with the cell-line, assay, coverage filter and source. Other public profiles cannot receive this sample.
6. Compare HG003/HG004 in Family planning. The three assessed rare variants are not present in the limited public subsets, so the result must remain unknown/unassessed. Do not expect the synthetic fixture's 25% example.
7. Ask **Do these profiles describe one person's genome, methylation and wearables?** The answer should explain that PMData is a different participant and that HG002 methylation is a separate cell-line experiment.

## Synthetic fixture flows

The following Alex/Sam checks use deliberately fabricated software fixtures, selected explicitly through `POST /api/session` with `{"demo":true,"demo_source":"synthetic"}`. The automated browser suite uses that fixture for these deterministic cases. It is no longer the default audience demo.


| Check | Actions | Expected result |
| --- | --- | --- |
| Startup | Open the app and Workspace settings. | Chat, AlphaGenome and Evo 2 are configured. This status reflects configuration; each provider's actual execution is checked below. Demo profiles are labeled synthetic. |
| DNA without methylation | Select Alex Morgan; open Methylation before adding a sample. | Four genetic calls are available. Methylation is empty/optional and no feature requires buying a test. |
| Genetic question | Ask **Could my knee pain be genetic?** | Activity events progress through specialists, synthesis and review. A Reviewed AI answer has sources and uncertainty. GDF5 association does not diagnose the cause of pain. |
| Conversation context | Follow with **Which variant did you just mention, and what can't it tell us?** | The answer uses the earlier discussion and the active profile. It does not invent a new genotype or personal methylation result. |
| Lifestyle | Ask **What lifestyle changes are supported by my available measurements?** | Suggestions distinguish general guidance from measured personalization, cite evidence, and avoid unsupported genotype-specific diets or supplement doses. |
| Wearable baseline | Open Health trends for Alex; ask **Does my DNA prove my higher resting heart rate is harmless?** | Three charts appear. Historical resting-HR median is about 80.5 bpm over 28 days. The answer distinguishes personal baseline from safety and does not apply a genetic fitness correction. |
| AlphaGenome | Genetic findings → rs143383 → Investigate → AlphaGenome → HepG2 → Run. | Six real reference/alternative tracks render, labeled live or cached. HepG2 is a reference liver-cell context, not the user's cartilage or measured methylation. |
| Evo 2 | Investigate rs143383 again, choose Evo 2, then Run. | A live or cached finite sequence-likelihood difference appears. It is not a percentage disease risk or an expression-direction prediction. This can take longer than AlphaGenome. |
| Explain molecular results | Return to Ask Strand: **Explain my completed rs143383 investigations. What did they actually measure or predict?** | The answer cites completed runs, distinguishes models/contexts and their limits, and does not invent cellular simulations. |
| Family | Family planning → compare Alex Morgan with Sam Chen. | CFTR shows a conditional 25% chance of two assessed alleles per pregnancy. Scope is three named alleles, not comprehensive screening; other cases are not shown as zero overall risk. |
| Optional methylation | Methylation → Explore a synthetic sample. | Twenty-four fictional probes and beta values appear with synthetic labels. No biological age, disease score or treatment claim is generated. |
| Export | Download an evidence report from a completed chat answer. | JSON contains the answer, evidence, recommendations, unknowns and mode. No API key appears. |
| Mobile | Narrow the browser to roughly 390 px or use phone emulation. | Navigation remains accessible, the composer works, and the page has no horizontal overflow. Variant tables may scroll within their own container. |

## Imports and failure cases

Perform these in a private workspace so demo samples stay separate. Use **Use my data → Create private workspace**. The local access key can be empty unless `DNA_ACCESS_KEY` was configured. Create **Synthetic A** with external-analysis consent initially off.

| Check | Actions | Expected result |
| --- | --- | --- |
| DNA-only upload | Add data → Genetic data → GRCh38 → upload `examples/manual/person-a.vcf`. | Import completes; two G/A calls appear at rs75527207 and rs143383. Methylation stays optional. |
| Consent off | Ask about knee genetics, then try a molecular investigation. | Chat uses the evidence-library mode. The molecular job refuses external analysis with an explicit consent message; it does not substitute predictions. |
| Consent on | Workspace settings → enable sending selected variants and summaries to providers. Ask again. | Live agents execute. A molecular run can execute after consent is enabled. |
| Known wearable calculation | Add data → Wearable measurements → upload `examples/manual/wearables.csv`; open Health trends. | Nine observations, latest 90 bpm, historical median 70 bpm over eight days, difference +20 bpm. These are synthetic observations, not a diagnosis. |
| Second parent | Create Synthetic B and upload `examples/manual/person-b.vcf` as GRCh38. Compare A and B in Family planning. | Conditional CFTR result is 25%. Missing PAH/HEXA calls remain unknown. |
| Missing genotype | Create Synthetic Unknown and upload `examples/manual/missing-carrier-call.vcf`. Compare with A. | The missing CFTR genotype is reported as unknown; no 25% or zero overall-risk result is calculated. |
| Wrong assembly | On a fresh test profile, import `person-a.vcf` with GRCh37 selected. | The declared GRCh38 header conflicts with the selection; the job fails explicitly and no genetic dataset is added. |
| Valid optional methylation | Upload `examples/manual/methylation.csv` with GRCh38, tissue **Synthetic blood**, assay **Synthetic processed table**, and collection date **2026-10-30**. | Three beta values appear: 0.2, 0.5 and 0.8, with the supplied metadata. They are fictional probe IDs. |
| Invalid beta | Repeat with `examples/manual/invalid-methylation.csv` using the same metadata. | Import rejects beta 1.2 and attaches no new dataset. Existing valid data remains usable. |
| Profile separation | Switch between A, B and Unknown after runs complete. | Each displays its own genotype calls, wearable measurements and chat turns. One profile's measurements must not appear as another's. |
| Workspace separation | Open the app in an incognito window. | The other window's private profiles/data are not visible. It gets its own session and demo workspace. |

If a check fails, record the action, selected profile/variant/model/context, visible error and approximate time. Never include API keys. A provider's outage or refusal should appear as a failed run, not fabricated scientific output.

## Saved chats, retry and allele eligibility

1. Ask a knee question, then choose **New chat** and ask about methylation. Both conversation titles should appear under **Your chats** for the active profile.
2. Reopen the knee chat, refresh, and confirm its messages and answers return. The methylation conversation must remain separate.
3. Use the suggested prompt chips above the composer; the new question should append to the active conversation.
4. Switch profiles and back. History is scoped to each profile. On mobile, use **Chats** in the top bar.
5. Open an old failed answer and choose **Retry answer** if it is the last message. The answer should rerun in place with one saved question. A controlled evidence-library fallback must show its notice and must not be labeled Reviewed AI.
6. In the explicit synthetic fixture, open PAH rs5030858 (G/G, reference G). The table should say **Reference only**, explain the call before submission, and disable **Run molecular investigation**. No model job should be queued. Use GDF5 rs143383 G/A for an eligible example; a measured A/A alternative is also valid.

## Coordinate variants and investigation navigation

1. In a combined public demo profile, open Investigate. Calls without rsIDs show chromosome, position and REF>ALT, with a missing-annotation note. They are not labeled novel variants.
2. Choose chr20:35,430,145 C>G. The investigation panel should scroll into view and receive focus. Choose Evo 2 and run to compare the measured alleles. The service must check the GRCh38 reference before inference.
3. GRCh37 calls without an rsID, unresolved reference alleles, no-calls and incompatible alleles remain blocked with a specific explanation. A made-up alternative cannot be run merely by editing the request.
4. In optional Methylation, beta values use a neutral measurement color. Read the explanation, then select Explain this sample to ask about the actual sample and missing requirements. No age or health score is manufactured.
