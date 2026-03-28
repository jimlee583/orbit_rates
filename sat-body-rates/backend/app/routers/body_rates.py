"""Router for the /api/body-rates endpoints."""

from fastapi import APIRouter, HTTPException

from backend.app.core import attitude, body_rates as br, orbit
from backend.app.models.schemas import (
    BodyRateRequest,
    BodyRateResponse,
    BodyRateSummary,
)

router = APIRouter(prefix="/body-rates", tags=["body-rates"])


@router.post("/compute", response_model=BodyRateResponse)
async def compute_body_rates(req: BodyRateRequest) -> BodyRateResponse:
    """Compute spacecraft body-rate time histories for a circular LEO orbit.

    Accepts orbital and attitude parameters, generates Euler-angle profiles
    for the requested pointing mode, and returns body rates derived by
    numerical differentiation.
    """
    try:
        n_rad_s = orbit.mean_motion_rad_s(req.altitude_km)
        n_deg_s = orbit.mean_motion_deg_s(req.altitude_km)
        time_s = orbit.time_vector_s(req.duration_min, req.num_points)

        roll_deg, pitch_deg, yaw_deg = attitude.generate_attitude_profile(
            time_s=time_s,
            mean_motion_rad_s=n_rad_s,
            attitude_mode=req.attitude_mode.value,
            beta_deg=req.beta_deg,
        )

        p_deg_s, q_deg_s, r_deg_s = br.compute_body_rates(
            time_s, roll_deg, pitch_deg, yaw_deg
        )

        summary_dict = br.rate_summary(p_deg_s, q_deg_s, r_deg_s)
        summary_dict["orbital_rate_deg_s"] = n_deg_s

        return BodyRateResponse(
            time_s=time_s.tolist(),
            roll_deg=roll_deg.tolist(),
            pitch_deg=pitch_deg.tolist(),
            yaw_deg=yaw_deg.tolist(),
            p_deg_s=p_deg_s.tolist(),
            q_deg_s=q_deg_s.tolist(),
            r_deg_s=r_deg_s.tolist(),
            summary=BodyRateSummary(**summary_dict),
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Internal computation error: {exc}"
        ) from exc
