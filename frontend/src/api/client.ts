const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

export async function post<Req, Res>(
  path: string,
  body: Req,
): Promise<Res> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail: string;
    try {
      const json = await res.json();
      detail = json.detail ?? JSON.stringify(json);
    } catch {
      detail = await res.text();
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<Res>;
}
