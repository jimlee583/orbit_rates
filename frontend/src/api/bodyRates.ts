import type { BodyRateRequest, BodyRateResponse } from "../types/api";
import { post } from "./client";

export function computeBodyRates(
  req: BodyRateRequest,
): Promise<BodyRateResponse> {
  return post<BodyRateRequest, BodyRateResponse>(
    "/api/body-rates/compute",
    req,
  );
}
