"""Body-rate computation from DCM attitude kinematics.

This module extracts angular velocity (p, q, r) from a time history of
body-from-inertial DCMs using discrete attitude kinematics — **not** by
differentiating Euler angles.  This avoids the kinematic cross-coupling
errors and gimbal-lock sensitivity inherent in the Euler-angle approach.

Angular-velocity extraction
---------------------------
For a body-from-inertial DCM *C*, the kinematic equation is:

    Ċ = −[ω×] · C

where [ω×] is the skew-symmetric matrix of the body angular velocity ω
(relative to inertial, expressed in the body frame).  Solving:

    [ω×] = −Ċ · Cᵀ

Using a forward finite difference between adjacent DCMs Cₖ and Cₖ₊₁:

    ΔC = Cₖ₊₁ · Cₖᵀ     (relative rotation, body_k → body_{k+1})

The skew-symmetric angular-velocity matrix is recovered from the
antisymmetric part:

    [ω×] ≈ (ΔCᵀ − ΔC) / (2 · Δt)

and the angular-velocity vector is extracted via the ``vee`` map:

    ω = [ S₃₂,  S₁₃,  S₂₁ ]     where S = [ω×]

For interior points, adjacent forward-difference estimates are averaged
(equivalent to central differencing for uniform Δt).  Endpoints use
one-sided differences.

This approach is first-order accurate at the endpoints and second-order
at interior points, which is more than adequate for the time steps used
in practice (≲ 15 s for a 360-sample orbit).

Euler-angle output
------------------
Roll, pitch, and yaw are extracted from the **body-from-LVLH** DCM:

    C_BL(t) = C_BI(t) · C_LI(t)ᵀ

using the 3-2-1 (ZYX) Euler sequence.  For nadir pointing, C_BL = I at
all times, so all angles are identically zero.  For sun_nadir, the angles
show the body's deviation from the LVLH frame (primarily a yaw offset
from sun-tracking).

These angles are for display and debugging only — they are **never** used
as the basis for body-rate computation.
"""

import numpy as np
from numpy.typing import NDArray

from backend.app.core.frames import dcm_to_euler_321_batch, vee


def compute_body_rates_from_dcms(
    dcm_bi: NDArray[np.float64],
    time_s: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Compute body angular velocity from a DCM time history.

    Parameters
    ----------
    dcm_bi : shape (N, 3, 3)
        Body-from-inertial DCMs at each time step.
    time_s : shape (N,)
        Time vector [s].

    Returns
    -------
    p_deg_s, q_deg_s, r_deg_s : each shape (N,)
        Body angular-rate components [deg/s].
        p = about x_body (roll rate),
        q = about y_body (pitch rate),
        r = about z_body (yaw rate).
    """
    N = len(time_s)
    if N < 2:
        raise ValueError("Need at least 2 time samples to compute rates.")

    dt = np.diff(time_s)  # (N-1,)

    # Relative rotations: ΔC[k] = C[k+1] · C[k]ᵀ
    delta_C = np.einsum("nij,nkj->nik", dcm_bi[1:], dcm_bi[:-1])

    # Antisymmetric part → skew-symmetric [ω×]
    # S = (ΔCᵀ − ΔC) / (2 · Δt)
    skew = (
        np.swapaxes(delta_C, -2, -1) - delta_C
    ) / (2.0 * dt[:, np.newaxis, np.newaxis])

    # Extract angular velocity via vee map: ω = [S₃₂, S₁₃, S₂₁]
    omega_fwd = np.stack(
        [skew[:, 2, 1], skew[:, 0, 2], skew[:, 1, 0]], axis=-1
    )  # (N-1, 3) in rad/s

    # Map N-1 forward-difference values to N output points.
    omega = np.empty((N, 3))
    omega[0] = omega_fwd[0]                              # forward at first
    omega[-1] = omega_fwd[-1]                             # backward at last
    if N > 2:
        omega[1:-1] = (omega_fwd[:-1] + omega_fwd[1:]) / 2.0  # central avg

    p_deg_s = np.degrees(omega[:, 0])
    q_deg_s = np.degrees(omega[:, 1])
    r_deg_s = np.degrees(omega[:, 2])
    return p_deg_s, q_deg_s, r_deg_s


def extract_euler_angles(
    dcm_bi: NDArray[np.float64],
    dcm_lvlh: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Derive Euler angles (3-2-1) of the body relative to the LVLH frame.

    Computes C_BL = C_BI · C_LI^T at each time step, then extracts
    roll (φ), pitch (θ), yaw (ψ) in degrees.

    Parameters
    ----------
    dcm_bi : shape (N, 3, 3)
        Body-from-inertial DCMs.
    dcm_lvlh : shape (N, 3, 3)
        LVLH-from-inertial DCMs.

    Returns
    -------
    roll_deg, pitch_deg, yaw_deg : each shape (N,)
    """
    # C_BL = C_BI · C_LIᵀ
    dcm_bl = np.einsum("nij,nkj->nik", dcm_bi, dcm_lvlh)

    roll_rad, pitch_rad, yaw_rad = dcm_to_euler_321_batch(dcm_bl)
    return np.degrees(roll_rad), np.degrees(pitch_rad), np.degrees(yaw_rad)


def rate_summary(
    p_deg_s: NDArray[np.float64],
    q_deg_s: NDArray[np.float64],
    r_deg_s: NDArray[np.float64],
) -> dict[str, float]:
    """Return aggregate body-rate metrics.

    Returns
    -------
    dict with keys ``max_abs_p_deg_s``, ``max_abs_q_deg_s``,
    ``max_abs_r_deg_s``, and ``max_body_rate_deg_s`` (RSS magnitude).
    """
    magnitude = np.sqrt(p_deg_s**2 + q_deg_s**2 + r_deg_s**2)
    return {
        "max_abs_p_deg_s": float(np.max(np.abs(p_deg_s))),
        "max_abs_q_deg_s": float(np.max(np.abs(q_deg_s))),
        "max_abs_r_deg_s": float(np.max(np.abs(r_deg_s))),
        "max_body_rate_deg_s": float(np.max(magnitude)),
    }
