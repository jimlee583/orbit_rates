# Satellite Body-Rate Calculator

A backend API that computes required spacecraft body rates for a satellite in low Earth orbit. Given orbital parameters and a pointing mode, it produces Euler-angle and angular-rate time histories suitable for attitude-control analysis and mission planning.

## Current Status — MVP

This is a **first-pass backend** focused on structure, correctness, and extensibility. A React frontend will be added in a future iteration.

### Modeling Assumptions & Limitations

| Assumption | Detail |
|---|---|
| Circular orbit | Eccentricity = 0; constant altitude throughout the simulation |
| Two-body dynamics | No J2, atmospheric drag, or third-body perturbations |
| No control / actuators | Pure kinematic profiles — no reaction wheels, thrusters, or control loops |
| Decoupled body rates | p ≈ dφ/dt, q ≈ dθ/dt, r ≈ dψ/dt (valid for small roll/yaw excursions) |
| Nadir mode | Continuous pitch at the orbital rate; zero roll & yaw |
| Velocity mode | **Identical to nadir** in this MVP — true velocity-vector alignment is deferred |
| Sun-nadir mode | Simplified yaw-steering law ψ = β·sin(n·t) with a small roll coupling term |

All simplifications are clearly marked in the source code with comments indicating where high-fidelity math should be inserted.

## Project Structure

```
sat-body-rates/
├── pyproject.toml              # uv / PEP 621 project metadata
├── .python-version             # pins Python 3.13
├── README.md
└── backend/
    └── app/
        ├── main.py             # FastAPI application entry point
        ├── routers/
        │   └── body_rates.py   # POST /api/body-rates/compute
        ├── core/               # Pure engineering / math modules
        │   ├── orbit.py        # Orbital mechanics (mean motion, period)
        │   ├── frames.py       # Rotation matrices, DCM stubs
        │   ├── attitude.py     # Attitude-profile generators
        │   └── body_rates.py   # Numerical differentiation → p, q, r
        └── models/
            └── schemas.py      # Pydantic v2 request / response models
```

## Setup

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/) (install with `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Install Dependencies

```bash
cd sat-body-rates
uv sync
```

### Run the API

```bash
cd sat-body-rates
uv run uvicorn backend.app.main:app --reload --port 8000
```

The interactive API docs are available at **http://localhost:8000/docs**.

### Health Check

```bash
curl http://localhost:8000/api/health
```

```json
{"status": "ok"}
```

## API Usage

### `POST /api/body-rates/compute`

#### Example Request

```bash
curl -X POST http://localhost:8000/api/body-rates/compute \
  -H "Content-Type: application/json" \
  -d '{
    "altitude_km": 550.0,
    "inclination_deg": 97.6,
    "beta_deg": 30.0,
    "attitude_mode": "sun_nadir",
    "duration_min": 90.0,
    "num_points": 360
  }'
```

#### Example Response (truncated)

```json
{
  "time_s": [0.0, 15.04, 30.08, "..."],
  "roll_deg": [0.0, -0.397, -0.788, "..."],
  "pitch_deg": [0.0, -0.016, -0.032, "..."],
  "yaw_deg": [0.0, 0.318, 0.635, "..."],
  "p_deg_s": [0.0, -0.026, -0.052, "..."],
  "q_deg_s": [-0.063, -0.063, -0.063, "..."],
  "r_deg_s": [0.021, 0.021, 0.021, "..."],
  "summary": {
    "max_abs_p_deg_s": 0.063,
    "max_abs_q_deg_s": 0.063,
    "max_abs_r_deg_s": 0.021,
    "orbital_rate_deg_s": 0.063
  }
}
```

> **Note:** Exact values will differ — the numbers above are representative.

#### Validation Rules

| Field | Constraint |
|---|---|
| `altitude_km` | > 0 |
| `inclination_deg` | 0 – 180 |
| `beta_deg` | −90 – 90 |
| `duration_min` | > 0 |
| `num_points` | ≥ 2 |
| `attitude_mode` | `nadir`, `velocity`, or `sun_nadir` |

Invalid inputs return a `422 Unprocessable Entity` response with details.

## Future Extensions

- **Quaternion propagation** — replace Euler-angle profiles with full quaternion kinematics to avoid gimbal-lock issues and improve accuracy at large angles.
- **LVLH frame modeling** — construct the Local Vertical / Local Horizontal frame from orbital state vectors for proper body-to-reference transformations.
- **Eccentric orbit support** — accept eccentricity and compute true-anomaly–dependent attitude profiles.
- **J2 perturbations** — incorporate secular RAAN drift and argument-of-perigee precession.
- **Realistic sun-tracking** — model continuous sun-pointing yaw-steering laws used by Earth-observation satellites.
- **React frontend** — interactive UI with parameter controls, plotted time histories (roll/pitch/yaw, p/q/r), and 3D orbit visualization.
