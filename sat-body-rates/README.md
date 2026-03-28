# Satellite Body-Rate Calculator

A backend API that computes required spacecraft body rates for a satellite in low Earth orbit. Given orbital parameters and a pointing mode, it produces angular-rate and attitude time histories suitable for attitude-control analysis and mission planning.

## Internal Attitude Representation

The backend uses **Direction Cosine Matrices (DCMs)** as the internal source of truth for spacecraft attitude. Euler angles are derived from the DCM history for display output only and are **never** used as the basis for body-rate computation.

### Why not differentiate Euler angles?

The previous MVP computed body rates (p, q, r) by numerically differentiating Euler-angle histories. This is problematic because:

1. **Kinematic cross-coupling.** The true relationship between Euler-angle rates and body rates involves trigonometric coupling terms (e.g. p = φ̇ − ψ̇ sin θ). Simply setting p ≈ dφ/dt ignores these terms and is only valid for small angles.
2. **Gimbal lock.** The 3-2-1 Euler sequence is singular when pitch θ = ±90°, which occurs twice per orbit for a nadir-pointing satellite accumulating pitch relative to inertial.
3. **Physical fidelity.** Real spacecraft attitude determination and control systems work with DCMs or quaternions, not Euler angles.

### Current approach

For each time step, the attitude is constructed geometrically:

1. Orbital geometry provides the position and velocity unit vectors.
2. Body-frame axes are assembled from the pointing-mode geometry (e.g. z_body = nadir, x_body = velocity or Sun projection).
3. The body-from-inertial DCM is stored directly.

Body rates are then extracted using discrete attitude kinematics:

    ΔC = C_{k+1} · C_k^T
    [ω×] ≈ (ΔC^T − ΔC) / (2 · Δt)
    ω = vee([ω×])

Euler angles are derived only for the response payload, computed as the body deviation from the LVLH frame:

    C_BL = C_BI · C_LI^T    →    extract 3-2-1 angles

## Current Status — MVP

This is a **first-pass backend** focused on structure, correctness, and extensibility. A React frontend will be added in a future iteration.

### Modeling Assumptions & Limitations

| Assumption | Detail |
|---|---|
| Circular orbit | Eccentricity = 0; constant altitude throughout the simulation |
| Two-body dynamics | No J2, atmospheric drag, or third-body perturbations |
| Orbit in X–Y plane | Simplified inertial frame; inclination is accepted but not used geometrically |
| No control / actuators | Pure kinematic profiles — no reaction wheels, thrusters, or control loops |
| DCM-based body rates | p, q, r extracted from DCM kinematics via antisymmetric finite differencing |
| Euler angles = display only | 3-2-1 (ZYX) body-from-LVLH deviations; zero for nadir mode |
| Nadir mode | Body frame = LVLH; once-per-orbit rotation about y_body at the orbital rate |
| Velocity mode | **Identical to nadir** in this MVP — true velocity-vector alignment is deferred |
| Sun-nadir mode | z_body = nadir; x_body aligned with Sun projection onto the nadir-perpendicular plane; Sun direction fixed in inertial space |
| Fixed Sun direction | ŝ = [cos β, 0, sin β] in the inertial frame; adequate for simulations up to a few orbits |

All simplifications are clearly marked in the source code with comments indicating where high-fidelity math should be inserted.

### Coordinate-Frame Conventions

| Frame | X axis | Y axis | Z axis |
|---|---|---|---|
| Inertial (simplified ECI) | Initial radius direction | 90° ahead in orbit plane | Orbit normal |
| LVLH | Velocity (along-track) | Cross-track (−orbit-normal) | Nadir (toward Earth) |
| Body (nadir) | Along-track (RAM) | Cross-track | Nadir (instrument boresight) |

The body-from-inertial DCM **C_BI** transforms vectors from the inertial frame to the body frame. Its rows are the body-frame unit axes expressed in inertial coordinates.

### Attitude Modes

**nadir** — Body frame coincides with LVLH. The only motion relative to inertial is the orbital rotation (q ≈ −n, p = r = 0). Euler angles (body-from-LVLH) are identically zero.

**velocity** — Geometrically identical to nadir for circular orbits (x_body is already along velocity). Routed through the full DCM pipeline. Will differ from nadir for eccentric orbits in a future iteration.

**sun_nadir** — Primary axis z_body points nadir. The secondary reference is the Sun direction projected onto the plane perpendicular to nadir. x_body is aligned with this projection, producing a yaw-steering manoeuvre that varies around the orbit. The body rates are visibly distinct from nadir, with time-varying p and r components driven by the sun-tracking geometry.

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
        │   ├── frames.py       # Rotation matrices, DCM/quaternion utilities
        │   ├── attitude.py     # DCM-based attitude construction
        │   └── body_rates.py   # Body rates from DCM kinematics
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

#### Response Fields

| Field | Description |
|---|---|
| `time_s` | Time vector [s] |
| `roll_deg` | Roll deviation from LVLH [deg] (3-2-1 sequence) |
| `pitch_deg` | Pitch deviation from LVLH [deg] |
| `yaw_deg` | Yaw deviation from LVLH [deg] |
| `p_deg_s` | Body roll rate relative to inertial [deg/s] |
| `q_deg_s` | Body pitch rate relative to inertial [deg/s] |
| `r_deg_s` | Body yaw rate relative to inertial [deg/s] |
| `summary` | Aggregate metrics (see below) |

#### Summary Metrics

| Key | Description |
|---|---|
| `max_abs_p_deg_s` | Peak \|p\| [deg/s] |
| `max_abs_q_deg_s` | Peak \|q\| [deg/s] |
| `max_abs_r_deg_s` | Peak \|r\| [deg/s] |
| `max_body_rate_deg_s` | Peak RSS body-rate magnitude [deg/s] |
| `orbital_rate_deg_s` | Mean orbital angular rate [deg/s] |

> **Note on Euler angles vs body rates:** The Euler angles show the body's deviation from the instantaneous LVLH frame. For nadir pointing these are identically zero. The body rates show the total angular velocity relative to inertial — for nadir, q ≈ −n (the orbital rate). These are different quantities by design.

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

- **True LVLH frame construction** — derive the LVLH frame from full orbital state vectors (position, velocity) rather than the simplified circular-orbit geometry.
- **Quaternion propagation everywhere** — replace DCM storage and differencing with quaternion integration for reduced storage and potential SLERP interpolation.
- **Eccentric orbit support** — accept eccentricity and compute true-anomaly–dependent attitude profiles; this will make the velocity mode distinct from nadir.
- **J2 perturbations** — incorporate secular RAAN drift and argument-of-perigee precession.
- **Realistic Sun ephemeris** — model the Sun direction as a function of epoch and orbital elements rather than treating it as fixed.
- **Control / dynamics propagation** — integrate equations of motion with reaction-wheel or thruster models to produce realistic slew profiles.
- **React frontend** — interactive UI with parameter controls, plotted time histories (Euler angles, body rates), and 3D orbit/attitude visualisation.
