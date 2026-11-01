import { MessageSquare } from "lucide-react";
import type { MolecularResult } from "../types";
import { Button } from "./Button";

export function MolecularExplanation({
  result,
  onAsk,
}: {
  result: MolecularResult;
  onAsk: (question: string) => void;
}) {
  const report = result.explanation;
  if (!report) return null;
  return (
    <section
      className="interpretation-card"
      aria-label="What your molecular result means"
    >
      <span className="eyebrow">THE RESULT, EXPLAINED</span>
      <h2>{report.headline}</h2>
      <p>{report.summary}</p>
      <p className="notice">{report.context_note}</p>
      <div className="methylation-meaning">
        <div>
          <span className="eyebrow">WHAT THE EVIDENCE ADDS</span>
          <p>
            {report.published_context}{" "}
            {report.published_url && (
              <a href={report.published_url} target="_blank" rel="noreferrer">
                Read the study ↗
              </a>
            )}
          </p>
        </div>
        <div>
          <span className="eyebrow">WHAT YOU CAN DO WITH THIS</span>
          <p>{report.takeaway}</p>
        </div>
      </div>
      {report.findings.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Model readout</th>
                <th>In plain language</th>
                <th>Largest plotted difference</th>
              </tr>
            </thead>
            <tbody>
              {report.findings.map((finding, index) => (
                <tr key={index}>
                  <td>{finding.modality}</td>
                  <td>{finding.meaning}</td>
                  <td>
                    {finding.largest_absolute_difference.toPrecision(3)}
                    <br />
                    <span className="small muted">
                      {finding.units} · at{" "}
                      {finding.largest_difference_position.toLocaleString()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="small muted">{report.metric_scope}</p>
      <h3>Next steps</h3>
      <ul>
        {report.next_steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
      <Button
        variant="secondary"
        onClick={() =>
          onAsk(
            `Explain my completed ${result.provider} investigation for ${result.variant.rsid || result.variant.id}. What does it add to my health question, is the cell context relevant, and what should I do next based on the evidence?`,
          )
        }
      >
        <MessageSquare size={14} /> Discuss this result
      </Button>
    </section>
  );
}
