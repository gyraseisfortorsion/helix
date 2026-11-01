import type { Evidence } from "../types";

export const EVIDENCE_CATEGORIES = {
  inherited: "Inherited",
  measured: "Measured",
  published: "Published",
  model: "Model prediction",
} as const;
export type EvidenceCategory = keyof typeof EVIDENCE_CATEGORIES;

export function evidenceCategory(evidence: Evidence): EvidenceCategory {
  if (evidence.category === "prediction") return "model";
  if (evidence.category === "measurement")
    return /genetic|genotype|variant call/i.test(evidence.title)
      ? "inherited"
      : "measured";
  return "published";
}

export function EvidenceBadge({
  category,
  compact = false,
}: {
  category: EvidenceCategory;
  compact?: boolean;
}) {
  return (
    <span
      className={`evidence-badge evidence-${category} ${compact ? "compact-badge" : ""}`}
      title={EVIDENCE_CATEGORIES[category]}
    >
      <i aria-hidden="true" />
      {!compact && EVIDENCE_CATEGORIES[category]}
    </span>
  );
}
