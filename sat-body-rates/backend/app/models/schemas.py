"""Pydantic v2 request / response schemas for the body-rate calculator."""

from enum import Enum

from pydantic import BaseModel, Field


class AttitudeMode(str, Enum):
    """Supported spacecraft attitude-pointing modes."""

    NADIR = "nadir"
    VELOCITY = "velocity"
    SUN_NADIR = "sun_nadir"


# ── Request ──────────────────────────────────────────────────────────────────


class BodyRateRequest(BaseModel):
    """Input parameters for a body-rate computation."""

    altitude_km: float = Field(
        ..., gt=0, description="Circular orbit altitude above the Earth's surface [km]"
    )
    inclination_deg: float = Field(
        ..., ge=0, le=180, description="Orbital inclination [deg]"
    )
    beta_deg: float = Field(
        ..., ge=-90, le=90, description="Solar beta angle [deg]"
    )
    attitude_mode: AttitudeMode = Field(
        ..., description="Spacecraft attitude-pointing mode"
    )
    duration_min: float = Field(
        ..., gt=0, description="Simulation duration [min]"
    )
    num_points: int = Field(
        ..., ge=2, description="Number of equally-spaced output time steps"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "altitude_km": 550.0,
                    "inclination_deg": 97.6,
                    "beta_deg": 30.0,
                    "attitude_mode": "sun_nadir",
                    "duration_min": 90.0,
                    "num_points": 360,
                }
            ]
        }
    }


# ── Response ─────────────────────────────────────────────────────────────────


class BodyRateSummary(BaseModel):
    """Aggregate metrics derived from the body-rate time histories."""

    max_abs_p_deg_s: float = Field(
        ..., description="Maximum absolute roll rate [deg/s]"
    )
    max_abs_q_deg_s: float = Field(
        ..., description="Maximum absolute pitch rate [deg/s]"
    )
    max_abs_r_deg_s: float = Field(
        ..., description="Maximum absolute yaw rate [deg/s]"
    )
    orbital_rate_deg_s: float = Field(
        ..., description="Mean orbital angular rate [deg/s]"
    )


class BodyRateResponse(BaseModel):
    """Full output of a body-rate computation."""

    time_s: list[float] = Field(..., description="Time vector [s]")
    roll_deg: list[float] = Field(..., description="Roll angle history [deg]")
    pitch_deg: list[float] = Field(..., description="Pitch angle history [deg]")
    yaw_deg: list[float] = Field(..., description="Yaw angle history [deg]")
    p_deg_s: list[float] = Field(..., description="Roll body rate [deg/s]")
    q_deg_s: list[float] = Field(..., description="Pitch body rate [deg/s]")
    r_deg_s: list[float] = Field(..., description="Yaw body rate [deg/s]")
    summary: BodyRateSummary
