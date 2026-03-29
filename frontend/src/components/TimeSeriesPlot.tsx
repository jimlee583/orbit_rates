import Plot from "react-plotly.js";
import type { Data, Layout } from "plotly.js";

interface Trace {
  name: string;
  y: number[];
}

interface Props {
  title: string;
  time_s: number[];
  traces: Trace[];
  yLabel: string;
}

export function TimeSeriesPlot({ title, time_s, traces, yLabel }: Props) {
  const time_min = time_s.map((t) => t / 60);

  const data: Data[] = traces.map((tr) => ({
    x: time_min,
    y: tr.y,
    type: "scatter" as const,
    mode: "lines" as const,
    name: tr.name,
  }));

  const layout: Partial<Layout> = {
    title: { text: title },
    xaxis: { title: { text: "Time [min]" } },
    yaxis: { title: { text: yLabel } },
    legend: { orientation: "h", y: -0.2 },
    margin: { t: 40, r: 20, b: 60, l: 60 },
    autosize: true,
  };

  return (
    <div className="plot-container">
      <Plot
        data={data}
        layout={layout}
        useResizeHandler
        style={{ width: "100%", height: 380 }}
        config={{ responsive: true, displaylogo: false }}
      />
    </div>
  );
}
