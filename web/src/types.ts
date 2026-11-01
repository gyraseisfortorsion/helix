export type Profile = {
  id: string;
  name: string;
  age?: number;
  timezone: string;
  goals: string;
  history: string;
  dietary_constraints: string;
  external_analysis_consent: boolean;
  provenance: "synthetic" | "uploaded" | "public_reference" | "composite_demo";
  demo_persona_key?: string;
  genetic_sample_key?: string;
  public_dataset_key?: string;
  source_name?: string;
  source_url?: string;
  data_notes?: string;
  recommended_partner_key?: string;
  demo_scenario?: string;
  data_coverage?: {
    genetic_calls: number;
    wearable_records: number;
    methylation_samples: number;
  };
};
export type Dataset = {
  id: string;
  kind: "genetics" | "wearables" | "methylation";
  filename: string;
  metadata: Record<string, string>;
  report: {
    accepted: number;
    missing: number;
    excluded: number;
    warnings: string[];
    provenance: string;
  };
};
export type Variant = {
  chrom: string;
  pos: number;
  ref: string | null;
  alt: string | null;
  allele1: string | null;
  allele2: string | null;
  genotype: string;
  rsid: string | null;
  build: string;
  investigation_id?: string | null;
  investigation?: {
    eligible: boolean;
    status: string;
    label: string;
    reason: string;
  };
};
export type Evidence = {
  id: string;
  category: string;
  title: string;
  url: string | null;
  summary: string;
  limitations: string;
  context: string;
  provenance: string;
};
export type Recommendation = {
  action: string;
  reason: string;
  evidence_ids: string[];
  personalization_basis: string;
  outcome_to_track: string;
};
export type Answer = {
  title: string;
  response: string;
  claims: { text: string; evidence_ids: string[] }[];
  recommendations: Recommendation[];
  unknowns: string[];
  followups: string[];
  evidence: Evidence[];
  mode: "live" | "evidence_only";
  notice?: string | null;
};
export type Conversation = {
  id: string;
  profile: string;
  title: string;
  created: number;
  updated: number;
  message_count?: number;
};
export type ChatMessage = {
  id: string;
  question: string;
  answer: Answer | null;
  error: string | null;
  status: "queued" | "running" | "completed" | "failed";
  created: number;
  events: RunEvent[];
};
export type ConversationDetail = {
  conversation: Conversation;
  messages: ChatMessage[];
  has_more: boolean;
};
export type RunEvent = {
  id: number;
  kind: string;
  agent: string;
  message: string;
};
export type Job<T = Record<string, unknown>> = {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  result: T | null;
  error: string | null;
};
export type Health = {
  providers: { chat: boolean; alphagenome: boolean; evo2: boolean };
  methylation_required: boolean;
};
export type Trends = {
  daily: { day: string; metric: string; value: number }[];
  metrics: Record<
    string,
    {
      latest: number;
      baseline: number | null;
      delta: number | null;
      baseline_days: number;
    }
  >;
  record_count: number;
  limitations: string[];
};
export type ParentCall = { status: string; genotype: string | null };
export type FamilyResult = {
  scope: string;
  conditions: {
    gene: string;
    condition: string;
    rsid: string;
    parent_a: ParentCall;
    parent_b: ParentCall;
    affected_genotype_probability: number | null;
    explanation: string;
  }[];
  evidence: Evidence[];
};
export type Methylation = {
  optional: boolean;
  comparisons: {
    before_id: string;
    after_id: string;
    from: string;
    to: string;
    status: string;
    reasons: string[];
    elapsed_years: number;
    estimate_change_years: number | null;
    interpretation: string;
    time_precision?: string;
    comparability_basis?: string;
  }[];
  samples: {
    dataset_id: string;
    metadata: Record<string, string>;
    probes: {
      cpg_id: string;
      beta: number;
      chrom?: string | null;
      pos?: number | null;
    }[];
    report: { accepted: number };
    age_report?: {
      status: string;
      title: string;
      model: string;
      model_version: string;
      coefficients_sha256: string;
      required_sites: number;
      present_sites: number;
      missing_sites: string[];
      checks: { key: string; passed: boolean; message: string }[];
      estimate_years: number | null;
      age_at_collection: number | null;
      age_range_at_collection?: [number, number] | null;
      age_range_source?: string | null;
      calendar_age_difference_years: number | null;
      meaning: string;
      next_steps: string[];
      qc_scope: string;
      uncertainty: string;
      sources: string[];
    };
  }[];
  limitations: string[];
  evidence: Evidence[];
};
export type MolecularResult = {
  explanation?: {
    headline: string;
    summary: string;
    context_note: string;
    published_context: string;
    published_url: string | null;
    takeaway: string;
    next_steps: string[];
    metric_scope: string;
    findings: {
      modality: string;
      meaning: string;
      largest_absolute_difference: number;
      largest_difference_position: number;
      units: string;
    }[];
  };
  provider: string;
  execution: string;
  context_name?: string;
  context?: string;
  elapsed_seconds: number;
  limitations: string[];
  delta?: number;
  tracks?: {
    name: string;
    modality: string;
    x: number[];
    reference: number[];
    alternate: number[];
    units: string;
  }[];
  heatmap?: { position: number; base: string; delta: number }[];
  variant: {
    id?: string;
    rsid: string | null;
    ref: string;
    alt: string;
    pos?: number;
  };
};
