import { ExternalLink, FlaskConical } from "lucide-react";
import type { Evidence } from "../types";
import { EvidenceBadge, evidenceCategory } from "./EvidenceBadge";

export function EvidencePanel({
  evidence,
  activeId,
  onSelect,
}: {
  evidence: Evidence[];
  activeId?: string;
  onSelect: (id: string) => void;
}) {
  const active = evidence.find((item) => item.id === activeId) || evidence[0];
  const index = active ? evidence.indexOf(active) : 0;
  return (
    <aside className="evidence-panel" aria-label="Evidence drawer">
      <div className="eyebrow">EVIDENCE DRAWER</div>
      {active ? (
        <>
          <article className="evidence-card" key={active.id}>
            <div className="source-type">
              <span className="evidence-id">E{index + 1}</span>
              <EvidenceBadge category={evidenceCategory(active)} />
            </div>
            <h3>{active.title}</h3>
            <div className="evidence-provenance">
              {active.provenance === "synthetic"
                ? "Synthetic fixture"
                : active.provenance === "public_reference" &&
                    active.category === "measurement"
                  ? "Public source measurement"
                  : active.category.replaceAll("_", " ")}
            </div>
            <p>{active.summary}</p>
            {active.context && (
              <p className="source-context">{active.context}</p>
            )}
            {active.limitations && (
              <div className="evidence-limitation">
                <strong>Limitation.</strong> {active.limitations}
              </div>
            )}
            {active.url && (
              <a
                className="evidence-source-link"
                href={active.url}
                target="_blank"
                rel="noreferrer"
                aria-label={`${active.title} — Read original source`}
              >
                Read original source <ExternalLink size={12} />
              </a>
            )}
          </article>
          <div className="evidence-list" aria-label="Evidence sources">
            {evidence.map((item, i) => (
              <button
                key={item.id}
                className={`evidence-list-item ${item.id === active.id ? "selected" : ""}`}
                onClick={() => onSelect(item.id)}
                aria-pressed={item.id === active.id}
                title={item.title}
              >
                <span className="evidence-id">E{i + 1}</span>
                <span>{item.title}</span>
                <EvidenceBadge category={evidenceCategory(item)} compact />
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="evidence-empty">
          <FlaskConical size={24} />
          <h3>Start with a question.</h3>
          <p>
            The measurements and publications used in your answer will appear
            here. Select a source to inspect its limits.
          </p>
        </div>
      )}
    </aside>
  );
}
