# BoltzFix — Hackathon Technical Proposal

> Can an agent improve protein–ligand structure predictions under a fixed compute budget?

**Status:** Proposal for team discussion. Improvements must be demonstrated through evaluation.

## 1. What it does

BoltzFix takes a protein sequence and a small molecule, predicts their 3D complex with Boltz-2, checks the result, and decides how to spend the remaining computational budget to improve its final prediction.

A **pose** is the position, orientation, and shape of the molecule relative to the protein. BoltzFix investigates issues such as overlapping atoms, distorted ligand geometry, low confidence, and disagreement between candidate poses.

The intended user is a researcher evaluating a predicted protein–ligand complex. The product delivers a selected structure, an explanation of the investigation, and inspectable evidence.

## 2. Inputs

| Input | Purpose |
| --- | --- |
| Protein amino-acid sequence, pasted or uploaded as FASTA | Defines the protein to model |
| Ligand SMILES string | Defines the small molecule, including specified stereochemistry |
| Compute budget | Limits the work available for prediction and refinement |
| Optional precomputed multiple sequence alignment (MSA) | Supplies evolutionary information to Boltz-2 |

**Benchmark-only input:** an experimentally determined reference complex, accessible exclusively to the evaluator. The agents cannot inspect or retrieve its ligand pose.

Initial scope: one protein and one ordinary, noncovalent small-molecule ligand. Complex metal coordination and covalent ligands can be excluded from the first benchmark.

## 3. Workflow

1. **Predict:** generate an initial Boltz-2 structure and collect available confidence metrics.
2. **Diagnose:** run chemistry and geometry checks; identify specific problems and uncertainty.
3. **Choose an action:** decide whether to generate alternative candidates, change supported sampling settings, apply physical guidance, or perform local energy minimization.
4. **Recheck:** evaluate each new candidate using the same checks and record the cost.
5. **Select:** return one final candidate before the budget expires, with an explanation and remaining concerns.

The protein sequence and ligand identity stay fixed. Any binding-site information must be independently supplied upfront and equally available to all benchmark methods.

## 4. Agent responsibilities

| Role | Responsibility |
| --- | --- |
| Diagnostic agent | Interprets numerical validation results and identifies what might be wrong |
| Experiment-planning agent | Chooses the next permitted computation based on the diagnosis and remaining budget |
| Review and selection agent | Compares candidates, challenges unsupported conclusions, and selects the final pose |

Scientific software calculates metrics and performs refinement. The agents interpret those results and coordinate actions. A shared run history records structures, settings, measurements, decisions, and costs.

## 5. Checking and simulations

**PoseBusters + RDKit:** check ligand identity, stereochemistry, bond lengths, bond angles, ring geometry, internal clashes, and overlap with the protein. These are numerical checks against chemical and geometric criteria.

**Boltz confidence:** use available confidence and predicted-error metrics as supporting signals. Confidence and agreement between samples do not establish accuracy.

**OpenMM energy minimization:** an optional action that adjusts coordinates toward a nearby lower-energy configuration under a molecular-mechanics force field. Suitable protein and ligand preparation is required. Minimized candidates are rechecked.

**Molecular dynamics:** a stretch goal for examining motion and contact persistence over short trajectories. It is optional because preparation and runtime add complexity. Short-term stability does not prove that a pose is correct.

Boltz diffusion sampling generates candidate structures; its steps do not represent physical simulation time. Energy minimization is also distinct from time-evolving molecular dynamics.

## 6. Outputs and demo experience

- **Selected complex:** downloadable mmCIF structure, with the ligand also exportable as SDF.
- **Before/after comparison:** initial versus selected pose in an interactive 3D viewer, with problematic contacts highlighted.
- **Quality report:** chemistry checks, confidence signals, remaining problems, and budget consumed.
- **Investigation timeline:** what each agent diagnosed, which actions were attempted, and why the final pose was selected.
- **Reproducible run artifacts:** candidate structures, settings, raw metrics, and decision history.
- **Benchmark report:** experimental pose error and validity results, shown only after final selection.

Demo flow: **enter protein + ligand → watch the investigation → inspect the selected structure → reveal benchmark accuracy.**

## 7. Proposed technologies

| Component | Suggested technology |
| --- | --- |
| Structure prediction | **Boltz-2**, preferably local open-source inference for parameter access and compute accounting; **NVIDIA BioNeMo Boltz2 NIM** is an alternative, subject to exposed controls |
| Chemistry and physical validation | **RDKit + PoseBusters** |
| Energy minimization; optional dynamics | **OpenMM**, with suitable ligand parameterization |
| Agent coordination | A tool-calling LLM coordinating the three roles through constrained Python tools; framework choice can remain open |
| Scientific backend | **Python**, with a lightweight API such as **FastAPI** |
| Interface | **React + TypeScript + 3Dmol.js** |
| Execution environment | **Docker** and the available **H100**, with runtime measured for each action |

## 8. How we demonstrate scientific value

Use a curated set of experimentally resolved complexes, separating development cases from final evaluation cases. Avoid splitting closely related targets or ligands across those groups where feasible.

After aligning the predicted and experimental proteins, calculate symmetry-aware ligand heavy-atom RMSD: the error in the ligand's placement. Do not independently align the ligand, which would conceal placement errors.

**Proposed primary endpoint:** fraction of cases where the single selected pose has ligand RMSD below 2 Å and passes the predefined physical-validity checks.

Compare against:

1. Boltz-2 defaults.
2. A fixed settings configuration selected on development cases.
3. Multiple samples ranked by a predefined confidence/validity rule.
4. A strategy that always applies minimization.
5. A fixed rule-based controller using the same diagnostics and permitted actions.

Apply the same per-complex compute cap; include all reruns and refinement, and separately report LLM usage and end-to-end runtime. Experimental reference poses never influence agent decisions or candidate selection.

**Main uncertainty:** the agent may fail to beat these simpler strategies. Fewer clashes or higher confidence alone would support a narrower claim than improved pose accuracy. The evaluation tests whether adaptive decisions actually help.

## 9. MVP scope

Deliver the prediction–diagnosis–action loop, one refinement option, a visual investigation history, and a small reproducible benchmark. Molecular dynamics and additional prediction models are extensions. Drug discovery, clinical efficacy, and binding-affinity optimization are outside the initial task.

## References

- [Boltz-2 prediction documentation](https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md)
- [NVIDIA BioNeMo Agent Toolkit](https://github.com/NVIDIA-BioNeMo/bionemo-agent-toolkit)
- [PoseBusters](https://github.com/maabuu/posebusters)
- [OpenMM: minimization and simulation](https://docs.openmm.org/latest/userguide/application/02_running_sims.html)
- [3Dmol.js molecular visualization](https://3dmol.org/)
