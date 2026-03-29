import { useState } from "react";
import type { BodyRateRequest, BodyRateResponse } from "./types/api";
import { computeBodyRates } from "./api/bodyRates";
import { ApiError } from "./api/client";
import { InputForm } from "./components/InputForm";
import { SummaryCards } from "./components/SummaryCards";
import { TimeSeriesPlot } from "./components/TimeSeriesPlot";
import { JsonViewer } from "./components/JsonViewer";

export default function App() {
  const [result, setResult] = useState<BodyRateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCompute(req: BodyRateRequest) {
    setLoading(true);
    setError(null);
    try {
      const data = await computeBodyRates(req);
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.status} — ${err.detail}`);
      } else {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Satellite Body-Rate Calculator</h1>
        <p className="subtitle">Engineering analysis console</p>
      </header>

      <InputForm onSubmit={handleCompute} loading={loading} />

      {error && <div className="error-banner">{error}</div>}

      {loading && <div className="loading">Computing…</div>}

      {result && (
        <>
          <section>
            <h2>Summary</h2>
            <SummaryCards summary={result.summary} />
          </section>

          <section>
            <h2>Body Rates vs Time</h2>
            <TimeSeriesPlot
              title="Body Rates"
              time_s={result.time_s}
              traces={[
                { name: "p (roll)", y: result.p_deg_s },
                { name: "q (pitch)", y: result.q_deg_s },
                { name: "r (yaw)", y: result.r_deg_s },
              ]}
              yLabel="Rate [deg/s]"
            />
          </section>

          <section>
            <h2>Euler Angles vs Time</h2>
            <TimeSeriesPlot
              title="Euler Angles"
              time_s={result.time_s}
              traces={[
                { name: "Roll", y: result.roll_deg },
                { name: "Pitch", y: result.pitch_deg },
                { name: "Yaw", y: result.yaw_deg },
              ]}
              yLabel="Angle [deg]"
            />
          </section>

          <section>
            <h2>Debug</h2>
            <JsonViewer data={result} />
          </section>
        </>
      )}
    </div>
  );
}
