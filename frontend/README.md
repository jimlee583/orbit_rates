# Satellite Body-Rate Calculator — Frontend

Minimal React/TypeScript visualization console for the satellite body-rate
calculator backend.

## Prerequisites

- Node.js >= 18
- Backend running at `http://localhost:8000` (see `../sat-body-rates/README.md`)

## Quick start

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts on **http://localhost:5173**.

## Backend connection

By default the Vite dev server **proxies** all `/api/*` requests to
`http://localhost:8000`. This is configured in `vite.config.ts` and requires no
extra environment variables.

If you need to point at a different backend URL (e.g. a remote host), set the
`VITE_API_BASE_URL` environment variable:

```bash
VITE_API_BASE_URL=http://my-server:8000 npm run dev
```

When `VITE_API_BASE_URL` is set, requests go directly to that URL instead of
through the proxy, so the backend must have CORS configured to allow the
frontend origin.

## Project structure

```
frontend/
├── index.html               HTML shell
├── vite.config.ts            Dev server & proxy config
├── tsconfig.json / .app.json TypeScript config
├── package.json
└── src/
    ├── main.tsx              Entry point
    ├── App.tsx               Page layout & state
    ├── styles.css            Minimal CSS
    ├── vite-env.d.ts         Vite env type augmentation
    ├── api/
    │   ├── client.ts         Generic fetch wrapper
    │   └── bodyRates.ts      /api/body-rates/compute caller
    ├── types/
    │   └── api.ts            Request/response TypeScript types
    └── components/
        ├── InputForm.tsx     Orbital parameter form
        ├── SummaryCards.tsx   Peak-rate metric cards
        ├── TimeSeriesPlot.tsx Plotly time-series chart
        └── JsonViewer.tsx    Collapsible raw JSON panel
```

## CORS notes

The backend (`main.py`) includes `CORSMiddleware` allowing
`http://localhost:5173`. If you change the Vite port, update the backend's
`allow_origins` list to match.
