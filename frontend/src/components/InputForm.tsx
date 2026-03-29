import { useState } from "react";
import type { AttitudeMode, BodyRateRequest } from "../types/api";

const DEFAULTS: BodyRateRequest = {
  altitude_km: 550,
  inclination_deg: 97.6,
  beta_deg: 30,
  attitude_mode: "sun_nadir",
  duration_min: 90,
  num_points: 360,
};

const ATTITUDE_OPTIONS: { value: AttitudeMode; label: string }[] = [
  { value: "nadir", label: "Nadir" },
  { value: "velocity", label: "Velocity" },
  { value: "sun_nadir", label: "Sun-Nadir" },
];

interface Props {
  onSubmit: (req: BodyRateRequest) => void;
  loading: boolean;
}

export function InputForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<BodyRateRequest>({ ...DEFAULTS });

  function setField<K extends keyof BodyRateRequest>(
    key: K,
    value: BodyRateRequest[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(form);
  }

  function handleReset() {
    setForm({ ...DEFAULTS });
  }

  return (
    <form className="input-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <label>
          <span>Altitude [km]</span>
          <input
            type="number"
            value={form.altitude_km}
            onChange={(e) => setField("altitude_km", +e.target.value)}
            min={1}
            step="any"
            required
          />
        </label>

        <label>
          <span>Inclination [deg]</span>
          <input
            type="number"
            value={form.inclination_deg}
            onChange={(e) => setField("inclination_deg", +e.target.value)}
            min={0}
            max={180}
            step="any"
            required
          />
        </label>

        <label>
          <span>Beta angle [deg]</span>
          <input
            type="number"
            value={form.beta_deg}
            onChange={(e) => setField("beta_deg", +e.target.value)}
            min={-90}
            max={90}
            step="any"
            required
          />
        </label>

        <label>
          <span>Attitude mode</span>
          <select
            value={form.attitude_mode}
            onChange={(e) =>
              setField("attitude_mode", e.target.value as AttitudeMode)
            }
          >
            {ATTITUDE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        <label>
          <span>Duration [min]</span>
          <input
            type="number"
            value={form.duration_min}
            onChange={(e) => setField("duration_min", +e.target.value)}
            min={0.1}
            step="any"
            required
          />
        </label>

        <label>
          <span>Points</span>
          <input
            type="number"
            value={form.num_points}
            onChange={(e) => setField("num_points", Math.max(2, +e.target.value))}
            min={2}
            step={1}
            required
          />
        </label>
      </div>

      <div className="form-actions">
        <button type="submit" disabled={loading}>
          {loading ? "Computing…" : "Compute"}
        </button>
        <button type="button" onClick={handleReset} disabled={loading}>
          Reset
        </button>
      </div>
    </form>
  );
}
