from typing import Any, Literal

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    age: int | None = Field(default=None, ge=0, le=120)
    timezone: str = "America/New_York"
    goals: str = Field(default="", max_length=2000)
    history: str = Field(default="", max_length=4000)
    dietary_constraints: str = Field(default="", max_length=2000)
    external_analysis_consent: bool = False


class SessionCreate(BaseModel):
    access_key: str = ""
    demo: bool = True
    demo_source: Literal["public", "synthetic"] = "public"


class VariantCall(BaseModel):
    build: Literal["GRCh37", "GRCh38"]
    chrom: str
    pos: int = Field(ge=1)
    ref: str
    alt: str
    genotype: str
    phased: bool = False
    quality: float | None = None
    rsid: str | None = None
    source_dataset: str = ""


class EvidenceRecord(BaseModel):
    id: str
    category: Literal["measurement", "association", "experiment", "prediction", "guideline"]
    title: str
    url: str | None = None
    summary: str
    limitations: str = ""
    context: str = ""
    provenance: Literal["synthetic", "uploaded", "public_reference", "model"] = "public_reference"


class Recommendation(BaseModel):
    action: str
    reason: str
    evidence_ids: list[str]
    personalization_basis: Literal["measurements", "genetics", "goals", "general_guidance"]
    outcome_to_track: str


class Claim(BaseModel):
    text: str
    evidence_ids: list[str]


class Answer(BaseModel):
    title: str
    response: str
    claims: list[Claim] = []
    recommendations: list[Recommendation] = []
    unknowns: list[str] = []
    followups: list[str] = []
    evidence: list[EvidenceRecord] = []
    visualizations: list[str] = []
    mode: Literal["live", "evidence_only"] = "evidence_only"
    notice: str | None = None


class ConversationCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=80)


class MessageCreate(BaseModel):
    profile_id: str
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class InvestigationCreate(BaseModel):
    profile_id: str
    variant_id: str = Field(min_length=1, max_length=100)
    context: str = Field(default="EFO:0001187", max_length=100)
    model: Literal["alphagenome", "evo2"] = "alphagenome"
    mutagenesis: bool = False


class FamilyCreate(BaseModel):
    profile_a: str
    profile_b: str


class RunEvent(BaseModel):
    id: int
    kind: str
    agent: str
    message: str
    data: dict[str, Any] = {}
