// Original helix component from the supplied Figma Make mockup.
export function BrandMark() {
  return (
    <svg viewBox="0 0 28 36" width="28" height="36" aria-hidden="true">
      {Array.from({ length: 9 }, (_, i) => {
        const t = i / 8;
        const a = Math.sin(t * Math.PI * 2) * 9;
        return (
          <g key={i}>
            <line
              x1={14 - a}
              x2={14 + a}
              y1={3 + i * 3.8}
              y2={3 + i * 3.8}
              stroke="#1b1a2e"
              opacity=".25"
            />
            <circle cx={14 - a} cy={3 + i * 3.8} r="2" fill="#4338ca" />
            <circle cx={14 + a} cy={3 + i * 3.8} r="2" fill="#be185d" />
          </g>
        );
      })}
    </svg>
  );
}
