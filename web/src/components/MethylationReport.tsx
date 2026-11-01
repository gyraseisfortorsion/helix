import { ArrowDownToLine, MessageSquare } from "lucide-react";
import type { Methylation } from "../types";
import { Button } from "./Button";
import { Chart } from "./Chart";

export function MethylationReport({
  sample,
  onAsk,
}: {
  sample: Methylation["samples"][number];
  onAsk: (q: string) => void;
}) {
  const report = sample.age_report;
  if (!report) return null;
  const ready = report.status === "ready";
  function download() {
    const url = URL.createObjectURL(
      new Blob(
        [
          JSON.stringify(
            {
              dataset_id: sample.dataset_id,
              metadata: sample.metadata,
              age_report: report,
            },
            null,
            2,
          ),
        ],
        { type: "application/json" },
      ),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `strand-methylation-${sample.dataset_id}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <section
      className="interpretation-card"
      aria-label="Methylation age report"
    >
      <div className="panel-header">
        <span className="eyebrow">
          {ready ? "RESEARCH AGE REPORT" : "REPORT READINESS"}
        </span>
        <span className="badge">
          {report.present_sites} / {report.required_sites} model sites
        </span>
      </div>
      <h2>{report.title}</h2>
      <p>{report.meaning}</p>
      {ready && (
        <div className="sample-metadata age-metrics">
          <div>
            <span className="eyebrow">METHYLATION AGE ESTIMATE</span>
            <strong>
              {report.estimate_years?.toFixed(1)} <small>years</small>
            </strong>
          </div>
          <div>
            <span className="eyebrow">
              {report.age_at_collection !== null
                ? "AGE AT COLLECTION"
                : "PUBLISHED COHORT AGE RANGE"}
            </span>
            <strong>
              {report.age_at_collection ??
                report.age_range_at_collection?.join("–") ??
                "Not reported"}{" "}
              <small>years</small>
            </strong>
          </div>
          <div>
            <span className="eyebrow">DIFFERENCE FROM CALENDAR AGE</span>
            <strong>
              {report.calendar_age_difference_years !== null ? (
                <>
                  {report.calendar_age_difference_years >= 0 ? "+" : ""}
                  {report.calendar_age_difference_years.toFixed(1)}{" "}
                  <small>years</small>
                </>
              ) : (
                <small>
                  Individual age not reported; no difference calculated.
                </small>
              )}
            </strong>
          </div>
        </div>
      )}
      {ready && (
        <p className="notice">
          {report.calendar_age_difference_years !== null
            ? "A positive or negative difference is not a good/bad health rating. It does not measure your rate of aging."
            : "The study reports a cohort age range, not your individual calendar age. The estimate is not a health rating or a measurement of aging speed."}
        </p>
      )}
      {report.age_range_source && (
        <p className="small">
          <a href={report.age_range_source} target="_blank" rel="noreferrer">
            Read the source for the published cohort age range ↗
          </a>
        </p>
      )}
      <details open={!ready}>
        <summary>
          Input checks · {report.checks.filter((c) => c.passed).length} of{" "}
          {report.checks.length} passed
        </summary>
        <ul className="report-checks">
          {report.checks.map((check) => (
            <li key={check.key}>
              <span aria-label={check.passed ? "Passed" : "Needs information"}>
                {check.passed ? "✓" : "○"}
              </span>{" "}
              {check.message}
            </li>
          ))}
        </ul>
        {report.missing_sites.length > 0 && (
          <details>
            <summary>Missing model CpG identifiers</summary>
            <p className="small missing-sites">
              {report.missing_sites.join(", ")}
            </p>
          </details>
        )}
      </details>
      <h3>
        {ready ? "How to use this report" : "How to unlock a useful report"}
      </h3>
      <ul>
        {report.next_steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ul>
      <p className="small muted">
        {report.qc_scope} {report.uncertainty}
      </p>
      <div className="inline-actions">
        <Button
          variant="secondary"
          onClick={() =>
            onAsk(
              "Explain my methylation age report and its input checks. What can I learn, how reliable is it, and what data would make a repeat comparison useful? Do not infer a lifestyle prescription from the clock score.",
            )
          }
        >
          <MessageSquare size={14} /> Discuss this report
        </Button>
        <Button variant="ghost" onClick={download}>
          <ArrowDownToLine size={14} /> Export report
        </Button>
      </div>
      <p className="small muted">
        {report.model} ·{" "}
        <a href={report.sources[0]} target="_blank" rel="noreferrer">
          Published model ↗
        </a>{" "}
        ·{" "}
        <a href={report.sources[1]} target="_blank" rel="noreferrer">
          Why repeat-test noise matters ↗
        </a>
      </p>
      <details>
        <summary>Reproducibility</summary>
        <p className="small missing-sites">
          Version: {report.model_version}
          <br />
          Coefficients SHA-256: {report.coefficients_sha256}
          <br />
          No imputation. No personal uncertainty interval. No raw IDAT
          processing.
        </p>
      </details>
    </section>
  );
}

export function MethylationTimeline({
  comparisons,
  samples,
}: {
  comparisons: Methylation["comparisons"];
  samples: Methylation["samples"];
}) {
  const byId = new Map(samples.map((s) => [s.dataset_id, s]));
  const timeline = new Map<string, number>();
  for (const pair of comparisons) {
    if (pair.status !== "descriptive_only") continue;
    const before = byId.get(pair.before_id)?.age_report?.estimate_years;
    const after = byId.get(pair.after_id)?.age_report?.estimate_years;
    if (before !== null && before !== undefined)
      timeline.set(pair.from, before);
    if (after !== null && after !== undefined) timeline.set(pair.to, after);
  }
  return (
    <section className="panel" aria-label="Repeat methylation tests">
      <span className="eyebrow">REPEAT MEASUREMENTS</span>
      <h2>What changed between tests?</h2>
      {timeline.size > 1 && (
        <Chart
          label="Research methylation-age estimates across reported collection times"
          data={[
            {
              type: "scatter",
              mode: "lines+markers",
              x: [...timeline.keys()],
              y: [...timeline.values()],
              line: { color: "#be185d", width: 2 },
              marker: { size: 9 },
            },
          ]}
          layout={{
            xaxis: {
              type: "category",
              title: { text: "Reported collection time" },
            },
            yaxis: {
              title: { text: "Research methylation-age estimate (years)" },
            },
          }}
        />
      )}
      {!comparisons.length ? (
        <p>
          Add two dated samples from the same person, using the same tissue,
          assay and preprocessing. Ask the laboratory for a comparability group
          covering both batches. Unknown dates and unmatched samples cannot form
          a timeline.
        </p>
      ) : (
        comparisons.map((pair) => (
          <div
            key={`${pair.before_id}-${pair.after_id}`}
            className="notice report-intro"
          >
            <strong>
              {pair.from} → {pair.to}
            </strong>
            {pair.status === "blocked" ? (
              <>
                <p>These tests cannot yet be compared.</p>
                <ul>
                  {pair.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p>
                Estimate change:{" "}
                {(pair.estimate_change_years ?? 0) >= 0 ? "+" : ""}
                {pair.estimate_change_years?.toFixed(1)} years over{" "}
                {pair.elapsed_years.toFixed(2)} calendar years.
              </p>
            )}
            <p className="small">{pair.interpretation}</p>
            {pair.time_precision === "year" && (
              <p className="small">
                Collection years are reported; exact days and months are
                unknown.
              </p>
            )}
            {pair.comparability_basis && (
              <p className="small muted">{pair.comparability_basis}</p>
            )}
          </div>
        ))
      )}
      <p className="small muted">
        Wearables can help track habits alongside repeat tests. They cannot
        establish what caused a methylation-score change.
      </p>
    </section>
  );
}
