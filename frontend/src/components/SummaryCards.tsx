import type { BodyRateSummary } from "../types/api";

interface Props {
  summary: BodyRateSummary;
}

interface Metric {
  label: string;
  value: number;
  unit: string;
}

export function SummaryCards({ summary }: Props) {
  const metrics: Metric[] = [
    { label: "Max |p| (roll rate)", value: summary.max_abs_p_deg_s, unit: "deg/s" },
    { label: "Max |q| (pitch rate)", value: summary.max_abs_q_deg_s, unit: "deg/s" },
    { label: "Max |r| (yaw rate)", value: summary.max_abs_r_deg_s, unit: "deg/s" },
    { label: "Max RSS body rate", value: summary.max_body_rate_deg_s, unit: "deg/s" },
    { label: "Orbital rate", value: summary.orbital_rate_deg_s, unit: "deg/s" },
  ];

  return (
    <div className="summary-cards">
      {metrics.map((m) => (
        <div key={m.label} className="summary-card">
          <div className="card-label">{m.label}</div>
          <div className="card-value">
            {m.value.toExponential(4)} <span className="card-unit">{m.unit}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
