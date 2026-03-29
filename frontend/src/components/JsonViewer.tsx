import { useState } from "react";
import type { BodyRateResponse } from "../types/api";

interface Props {
  data: BodyRateResponse;
}

export function JsonViewer({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="json-viewer">
      <button
        className="json-toggle"
        type="button"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "▾ Hide" : "▸ Show"} raw JSON
      </button>
      {open && (
        <pre className="json-pre">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}
