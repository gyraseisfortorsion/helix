import type { RunEvent } from "../types";

export function ActivityChips({ events }: { events: RunEvent[] }) {
  const latest = new Map<string, RunEvent>();
  for (const event of events) {
    if (event.kind !== "failed" && event.agent !== "Workspace")
      latest.set(event.agent, event);
  }
  return (
    <div className="activity-chips" aria-label="Agent activity">
      {[...latest.values()].slice(-4).map((event, index) => (
        <div className="activity-chip" key={event.agent} title={event.message}>
          <span className="activity-number">{index + 1}</span>
          <strong>{event.agent}</strong>
          <span>{event.message}</span>
        </div>
      ))}
    </div>
  );
}
