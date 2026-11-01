import { useEffect, useRef, useState } from "react";
import type { Data, Layout } from "plotly.js";

export function Chart({
  data,
  layout,
  label,
}: {
  data: Data[];
  layout?: Partial<Layout>;
  label: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let disposed = false;
    const element = ref.current;
    let cleanup: (() => void) | undefined;
    import("plotly.js-dist-min")
      .then(({ default: plotly }) => {
        if (!element || disposed) return;
        plotly.newPlot(
          element,
          data,
          {
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            font: {
              family: "Inter, system-ui, sans-serif",
              size: 11,
              color: "#6d6a7c",
            },
            margin: { t: 18, r: 18, b: 45, l: 48 },
            height: 280,
            xaxis: { gridcolor: "#e4ddd1", zeroline: false },
            yaxis: { gridcolor: "#e4ddd1", zeroline: false },
            showlegend: false,
            ...layout,
          },
          { responsive: true, displayModeBar: false },
        );
        const observer = new ResizeObserver(() => plotly.Plots.resize(element));
        observer.observe(element);
        cleanup = () => {
          observer.disconnect();
          plotly.purge(element);
        };
      })
      .catch(() => {
        if (!disposed) setError(true);
      });
    return () => {
      disposed = true;
      cleanup?.();
    };
  }, [data, layout]);
  return error ? (
    <p className="notice">
      Chart could not load. The numeric results remain available.
    </p>
  ) : (
    <div role="img" aria-label={label} className="chart" ref={ref} />
  );
}
