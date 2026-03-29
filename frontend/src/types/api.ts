/** Spacecraft attitude-pointing modes supported by the backend. */
export type AttitudeMode = "nadir" | "velocity" | "sun_nadir";

/** POST /api/body-rates/compute request body. */
export interface BodyRateRequest {
  altitude_km: number;
  inclination_deg: number;
  beta_deg: number;
  attitude_mode: AttitudeMode;
  duration_min: number;
  num_points: number;
}

/** Aggregate metrics from a body-rate computation. */
export interface BodyRateSummary {
  max_abs_p_deg_s: number;
  max_abs_q_deg_s: number;
  max_abs_r_deg_s: number;
  max_body_rate_deg_s: number;
  orbital_rate_deg_s: number;
}

/** POST /api/body-rates/compute response body. */
export interface BodyRateResponse {
  time_s: number[];
  roll_deg: number[];
  pitch_deg: number[];
  yaw_deg: number[];
  p_deg_s: number[];
  q_deg_s: number[];
  r_deg_s: number[];
  summary: BodyRateSummary;
}
