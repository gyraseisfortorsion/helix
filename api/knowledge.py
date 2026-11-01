"""Small, explicit evidence catalogue. No inferred disease probabilities."""

from .models import EvidenceRecord

SOURCES = {
    "hannum": EvidenceRecord(
        id="hannum",
        category="experiment",
        title="Hannum et al. 2013: blood methylation age",
        url="https://www.sciencedirect.com/science/article/pii/S1097276512008933",
        summary="A published 71-CpG whole-blood model estimates chronological age. Strand uses pinned Biolearn coefficients without imputation.",
        limitations="Research age estimate, not a clinical health score. Adult whole-blood/450K adapter only; laboratory preprocessing and cell composition affect outputs.",
    ),
    "clock_reliability": EvidenceRecord(
        id="clock_reliability",
        category="experiment",
        title="Technical reliability of epigenetic clocks",
        url="https://www.nature.com/articles/s43587-022-00248-2",
        summary="Higgins-Chen et al. studied technical noise in methylation clocks and methods to improve reliability.",
        limitations="A score change alone cannot establish an intervention effect. Strand has no calibrated personal confidence interval or significant-change threshold.",
    ),
    "gdf5": EvidenceRecord(
        id="gdf5",
        category="experiment",
        title="GDF5 regulation and cartilage methylation",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC4099533/",
        summary="Experiments found allele- and methylation-dependent regulation at GDF5 rs143383 in cartilage.",
        context="Cartilage and experimental cell systems; published 2014",
        limitations="An established mechanism is not evidence that a person's current knee pain has a genetic cause. Blood methylation does not measure cartilage methylation.",
    ),
    "osteoarthritis": EvidenceRecord(
        id="osteoarthritis",
        category="guideline",
        title="NIAMS: osteoarthritis",
        url="https://www.niams.nih.gov/health-topics/osteoarthritis",
        summary="Joint symptoms and osteoarthritis have multiple contributing factors, including injury, joint loading and genetics.",
        limitations="A DNA association cannot diagnose the cause of new joint pain.",
    ),
    "heart_rate": EvidenceRecord(
        id="heart_rate",
        category="guideline",
        title="American Heart Association: heart-rate context",
        url="https://www.heart.org/en/healthy-living/exercise-and-physical-activity/fitness-basics/target-heart-rates",
        summary="Heart rate varies with activity, stress, medication and other factors. Population exercise targets are general guides.",
        limitations="A genetic association cannot establish that an elevated heart rate is harmless or validate a fitness-score correction.",
    ),
    "heart_genetics": EvidenceRecord(
        id="heart_genetics",
        category="association",
        title="Genetics of resting heart rate",
        url="https://www.nature.com/articles/s41467-023-39521-2",
        summary="A large GWAS identified many variants associated with resting heart rate.",
        limitations="Population associations do not explain an individual's heart rate or replace clinical assessment.",
    ),
    "dietfits": EvidenceRecord(
        id="dietfits",
        category="experiment",
        title="DIETFITS randomized clinical trial",
        url="https://jamanetwork.com/journals/jama/fullarticle/2673150",
        summary="The tested genotype patterns did not identify differential weight-loss success between healthy low-fat and low-carbohydrate diets.",
        limitations="This trial does not exclude every gene–diet interaction; it limits claims about the patterns and diets tested.",
    ),
    "activity": EvidenceRecord(
        id="activity",
        category="guideline",
        title="Physical activity: evidence-based guidance",
        url="https://www.cdc.gov/physical-activity-basics/guidelines/adults.html",
        summary="Regular physical activity has established health benefits. Plans should consider current ability, symptoms and health context.",
        limitations="Generic guidance is not a DNA-derived exercise prescription.",
    ),
    "sleep": EvidenceRecord(
        id="sleep",
        category="guideline",
        title="CDC: sleep habits",
        url="https://www.cdc.gov/sleep/about/index.html",
        summary="Consistent sleep routines and adequate sleep support health.",
        limitations="Wearable estimates are observations, not sleep-disorder diagnoses.",
    ),
    "inheritance": EvidenceRecord(
        id="inheritance",
        category="guideline",
        title="MedlinePlus: inheritance probabilities",
        url="https://medlineplus.gov/genetics/understanding/inheritance/riskassessment/",
        summary="Two heterozygous carriers of compatible disease-causing alleles for the same autosomal recessive condition have a 25% affected-genotype probability per pregnancy.",
        limitations="Conditional on valid calls, compatible variants and the stated inheritance model. Negative limited screening leaves residual risk.",
    ),
    "epigenome": EvidenceRecord(
        id="epigenome",
        category="guideline",
        title="NHGRI: epigenomics",
        url="https://www.genome.gov/about-genomics/fact-sheets/Epigenomics-Fact-Sheet",
        summary="Epigenetic marks differ between tissues and can change with development, exposures and disease.",
        limitations="DNA sequence alone does not measure current personal methylation. An optional blood sample does not describe every tissue.",
    ),
    "cftr": EvidenceRecord(
        id="cftr",
        category="experiment",
        title="ClinVar: CFTR p.Gly551Asp",
        url="https://www.ncbi.nlm.nih.gov/clinvar/variation/7120/",
        summary="CFTR c.1652G>A (p.Gly551Asp), rs75527207, is a documented cystic-fibrosis-causing allele.",
        limitations="This application assesses the named allele; it is not comprehensive CFTR carrier screening.",
    ),
    "pah": EvidenceRecord(
        id="pah",
        category="experiment",
        title="ClinVar: PAH p.Arg408Trp",
        url="https://www.ncbi.nlm.nih.gov/clinvar/variation/577/",
        summary="PAH c.1222C>T (p.Arg408Trp), rs5030858, is a documented phenylketonuria-associated allele.",
        limitations="PAH is on the reverse strand. Forward-genome G>A corresponds to transcript C>T. Other variants are not excluded.",
    ),
    "hexa": EvidenceRecord(
        id="hexa",
        category="experiment",
        title="ClinVar: HEXA p.Gly269Ser",
        url="https://www.ncbi.nlm.nih.gov/clinvar/variation/3898/",
        summary="HEXA c.805G>A (p.Gly269Ser), rs121907954, is associated with the Tay–Sachs disease spectrum.",
        limitations="Disease severity is genotype-dependent. This limited comparison does not predict an individual child's phenotype.",
    ),
}

# Curated, allele-specific forward-strand GRCh38 entries. Review date: 2026-10-31.
PANEL = [
    {
        "gene": "CFTR",
        "condition": "Cystic fibrosis",
        "rsid": "rs75527207",
        "chrom": "7",
        "pos": 117587806,
        "ref": "G",
        "alt": "A",
        "evidence": "cftr",
    },
    {
        "gene": "PAH",
        "condition": "Phenylketonuria",
        "rsid": "rs5030858",
        "chrom": "12",
        "pos": 102840493,
        "ref": "G",
        "alt": "A",
        "evidence": "pah",
    },
    {
        "gene": "HEXA",
        "condition": "Tay–Sachs spectrum",
        "rsid": "rs121907954",
        "chrom": "15",
        "pos": 72350518,
        "ref": "C",
        "alt": "T",
        "evidence": "hexa",
    },
]

TOPICS = {
    "joint": {
        "words": ["knee", "joint", "cartilage", "arthritis", "gdf5"],
        "evidence": ["gdf5", "osteoarthritis"],
        "variants": ["rs143383"],
    },
    "heart": {
        "words": ["heart", "pulse", "fitness", "recovery", "bpm", "running", "bradycard", "tachycard", "rhr"],
        "evidence": ["heart_rate", "heart_genetics", "activity"],
        "variants": [],
    },
    "diet": {
        "words": ["diet", "food", "nutrition", "weight", "eat", "lifestyle", "dairy"],
        "evidence": ["dietfits", "activity", "sleep"],
        "variants": [],
    },
    "sleep": {"words": ["sleep", "tired", "fatigue"], "evidence": ["sleep", "heart_rate"], "variants": []},
    "family": {
        "words": ["partner", "child", "baby", "offspring", "carrier", "family planning"],
        "evidence": ["inheritance", "cftr", "pah", "hexa"],
        "variants": [v["rsid"] for v in PANEL],
    },
    "epigenetics": {
        "words": ["methyl", "epigen", "gene expression"],
        "evidence": ["epigenome", "gdf5"],
        "variants": [],
    },
}


def topics_for(question: str) -> list[str]:
    q = question.lower()
    return [name for name, topic in TOPICS.items() if any(word in q for word in topic["words"])]
