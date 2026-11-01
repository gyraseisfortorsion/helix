import { ArrowRight } from "lucide-react";
import type { Profile } from "../types";

export function DemoExamples({
  profiles,
  current,
  onChoose,
}: {
  profiles: Profile[];
  current?: Profile;
  onChoose: (
    id: string,
    view: "genetics" | "trends" | "family" | "methylation",
  ) => void;
}) {
  const alex = profiles.find((p) => p.demo_persona_key === "alex-v1");
  const sam = profiles.find((p) => p.demo_persona_key === "sam-v1");
  const family = profiles.find(
    (p) => p.public_dataset_key === "family-na12043",
  );
  const blood = profiles.find((p) => p.public_dataset_key === "GSM1009666");
  const repeat = profiles.find((p) => p.demo_scenario === "repeat_methylation");
  const examples = [
    {
      profile: alex,
      view: "genetics" as const,
      title: "Joint & molecular",
      description: "Measured GDF5 variant · AlphaGenome / Evo 2",
    },
    {
      profile: sam,
      view: "trends" as const,
      title: "Heart rate & wearables",
      description: "Covered heart-rate loci · actual Fitbit trends",
    },
    {
      profile: family,
      view: "family" as const,
      title: "Family inheritance",
      description: "Two measured PAH carriers · conditional 25%",
    },
    {
      profile: blood,
      view: "methylation" as const,
      title: "Methylation report",
      description: "71 measured model sites · research age estimate",
    },
    {
      profile: repeat,
      view: "methylation" as const,
      title: "Repeat methylation",
      description: "Same donor · measured 1997 and 2007 samples",
    },
  ];
  return (
    <details className="demo-guide">
      <summary>
        <span>Explore covered demo examples</span>
        <span className="small muted">
          {current?.data_coverage?.genetic_calls || 0} DNA calls ·{" "}
          {current?.data_coverage?.wearable_records || 0} wearable records ·{" "}
          {current?.data_coverage?.methylation_samples || 0} methylation samples
        </span>
      </summary>
      <div className="demo-example-grid">
        {examples
          .filter((e) => e.profile)
          .map((example) => (
            <button
              key={example.title}
              onClick={() => onChoose(example.profile!.id, example.view)}
            >
              <strong>
                {example.title}
                <ArrowRight size={14} />
              </strong>
              <span>{example.description}</span>
            </button>
          ))}
      </div>
      <p className="small muted">
        Each example uses attributed public measurements. Different source
        donors are kept identifiable; the family pairing and Alex/Sam scenarios
        are demonstrations.
      </p>
    </details>
  );
}
