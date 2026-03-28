"""Attitude construction via DCM geometry for supported pointing modes.

This module is the **source of truth** for spacecraft attitude.  Each mode
constructs the body-from-inertial DCM history directly from orbital
geometry — no Euler angles are created first.  Euler angles are derived
downstream (in ``body_rates.py``) for display purposes only.

Frame conventions
-----------------
See ``frames.py`` for the full coordinate-frame specification.  In brief:

* The simplified inertial frame has the orbit in the X–Y plane.
* LVLH: x = velocity, y = cross-track (−orbit-normal), z = nadir.
* Body axes coincide with LVLH for the nadir-pointing case.

Supported modes
---------------

**nadir**
    Body frame = LVLH.  The spacecraft maintains a perfect nadir-pointing
    attitude in a circular orbit.  The only body rotation relative to
    inertial is the once-per-orbit pitch driven by orbital motion.

**velocity**
    For the circular-orbit MVP this is geometrically identical to nadir
    (x_body is already aligned with the velocity vector).  It is routed
    through the same DCM pipeline so that the code path is exercised.
    A future iteration can distinguish this mode for eccentric orbits
    where the velocity direction differs from the LVLH x-axis.

**sun_nadir**
    Primary constraint: z_body = nadir (−r̂).
    Secondary reference: the Sun direction projected into the plane
    perpendicular to nadir.  x_body is aligned with this projection,
    giving a yaw-steering effect that depends on orbital position and
    solar beta angle.

    The Sun direction is modelled as fixed in inertial space:

        ŝ = [ cos β,  0,  sin β ]

    where β is the solar beta angle (elevation of the Sun above the
    orbit plane).  This is adequate for simulations up to a few orbits;
    the ~1°/day Sun motion is neglected.

    When the Sun projection onto the nadir-perpendicular plane is
    near-zero (Sun nearly aligned with nadir), the algorithm falls
    back to the velocity direction to avoid singularity.

MVP simplifications
-------------------
* Circular orbit only (r̂ ⊥ v̂, constant speed).
* Orbit in the inertial X–Y plane; orbit normal = Z_I.
* Sun direction fixed in inertial space.
* ``inclination_deg`` is accepted but not used in the geometry.  A
  ``UserWarning`` is raised whenever a non-zero value is supplied so that
  callers are not silently misled into thinking inclined-orbit geometry is
  being computed.
"""

import warnings

import numpy as np
from numpy.typing import NDArray

from backend.app.core.frames import (
    dcm_from_body_axes,
    normalize,
    orthonormal_triad_from_primary_secondary,
)

# Threshold below which the Sun-projection magnitude is considered
# degenerate and the velocity fallback is used.  Set to ~0.6° (sin 0.6° ≈
# 0.01) so that numerically noisy near-singular directions are caught before
# they produce large DCM discontinuities and spurious rate spikes.
_SUN_PROJECTION_TOL: float = 1e-2

# Solar beta angle below which a singularity warning is issued.  For
# |β| < _BETA_WARN_DEG the Sun projection onto the local horizontal plane
# becomes small near θ ≈ 0 and θ ≈ π, causing x_body to snap between the
# Sun-projection direction and the velocity fallback within one time step.
_BETA_WARN_DEG: float = 5.0


def generate_attitude_dcms(
    time_s: NDArray[np.float64],
    mean_motion_rad_s: float,
    attitude_mode: str,
    beta_deg: float,
    inclination_deg: float = 0.0,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Construct body-from-inertial DCM histories for the requested mode.

    Parameters
    ----------
    time_s :
        1-D array of time stamps [s], shape (N,).
    mean_motion_rad_s :
        Orbital mean motion *n* [rad/s].
    attitude_mode :
        One of ``"nadir"``, ``"velocity"``, ``"sun_nadir"``.
    beta_deg :
        Solar beta angle [deg].  Only used by the ``sun_nadir`` mode.
    inclination_deg :
        Orbital inclination [deg].  **Not used in the current geometry.**
        The orbit is always computed in the simplified inertial X–Y plane
        regardless of this value.  A ``UserWarning`` is raised when a
        non-zero value is supplied so callers are not silently misled.

    Returns
    -------
    dcm_bi : ndarray, shape (N, 3, 3)
        Body-from-inertial DCMs at each time step.
    dcm_lvlh : ndarray, shape (N, 3, 3)
        LVLH-from-inertial DCMs at each time step (used downstream for
        Euler-angle extraction relative to LVLH).
    """
    if inclination_deg != 0.0:
        warnings.warn(
            f"inclination_deg={inclination_deg:.4g}° was supplied but is not "
            "used in the current geometry. The orbit is computed in a "
            "simplified inertial frame with the orbit fixed in the X–Y plane. "
            "All attitude profiles and body rates are independent of "
            "inclination until true inclined-orbit geometry is implemented.",
            UserWarning,
            stacklevel=2,
        )

    n = mean_motion_rad_s
    theta = n * time_s  # true anomaly for circular orbit [rad]

    r_hat, v_hat = _orbital_unit_vectors(theta)

    dcm_lvlh = _build_nadir_dcms(r_hat, v_hat)

    if attitude_mode in ("nadir", "velocity"):
        dcm_bi = dcm_lvlh.copy()
    elif attitude_mode == "sun_nadir":
        dcm_bi = _build_sun_nadir_dcms(r_hat, v_hat, beta_deg)
    else:
        raise ValueError(f"Unknown attitude mode: {attitude_mode!r}")

    return dcm_bi, dcm_lvlh


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _orbital_unit_vectors(
    theta: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Position and velocity unit vectors for a circular orbit in the X–Y plane.

    Parameters
    ----------
    theta : shape (N,)
        True anomaly (= n·t for circular orbits) [rad].

    Returns
    -------
    r_hat, v_hat : each shape (N, 3)
    """
    N = len(theta)
    r_hat = np.column_stack([np.cos(theta), np.sin(theta), np.zeros(N)])
    v_hat = np.column_stack([-np.sin(theta), np.cos(theta), np.zeros(N)])
    return r_hat, v_hat


def _build_nadir_dcms(
    r_hat: NDArray[np.float64],
    v_hat: NDArray[np.float64],
) -> NDArray[np.float64]:
    """LVLH / nadir-pointing DCMs: body frame = LVLH.

    Body axes (all expressed in inertial coordinates):
        x_body = v̂      (along-track / velocity)
        y_body = z × x   (cross-track, ≈ −orbit-normal)
        z_body = −r̂      (nadir)
    """
    N = len(r_hat)
    z_body = -r_hat
    x_body = v_hat
    y_body = np.cross(z_body, x_body)  # (N, 3)

    dcm = np.zeros((N, 3, 3))
    dcm[:, 0, :] = x_body
    dcm[:, 1, :] = y_body
    dcm[:, 2, :] = z_body
    return dcm


def _build_sun_nadir_dcms(
    r_hat: NDArray[np.float64],
    v_hat: NDArray[np.float64],
    beta_deg: float,
) -> NDArray[np.float64]:
    """Sun-nadir pointing: z_body = nadir, x_body toward Sun projection.

    At each time step the Sun direction is projected onto the plane
    perpendicular to the nadir axis.  x_body is aligned with this
    projection, producing a yaw-steering manoeuvre that varies around
    the orbit.

    When the projection magnitude drops below ``_SUN_PROJECTION_TOL``
    (i.e. the Sun is within ~0.6° of nadir or zenith), the velocity
    direction is used as a fallback reference.

    Singularity warning
    -------------------
    For |beta_deg| < ``_BETA_WARN_DEG`` (5°) the Sun lies nearly in the
    orbit plane.  With the fixed Sun model ``ŝ = [cos β, 0, sin β]`` the
    Sun projection magnitude passes through zero near θ = 0 and θ = π,
    causing x_body to switch abruptly between the Sun-projection direction
    and the velocity fallback.  This near-discontinuity in the DCM
    produces large body-rate spikes at those orbital positions.  A
    ``UserWarning`` is raised when this condition is detected.
    """
    if abs(beta_deg) < _BETA_WARN_DEG:
        warnings.warn(
            f"beta_deg={beta_deg:.2f}° is within {_BETA_WARN_DEG}° of zero. "
            "With the fixed Sun model the sun_nadir mode has a geometric "
            "singularity near theta=0 and theta=pi where the Sun projection "
            "onto the local horizontal plane approaches zero. x_body will "
            "fall back to the velocity direction at those points, producing "
            "large body-rate spikes in the output. Consider using a non-zero "
            "beta angle or interpreting the rates near those positions with "
            "caution.",
            UserWarning,
            stacklevel=3,
        )

    N = len(r_hat)
    beta_rad = np.radians(beta_deg)
    sun_inertial = np.array([np.cos(beta_rad), 0.0, np.sin(beta_rad)])

    dcm = np.zeros((N, 3, 3))

    for k in range(N):
        z = -r_hat[k]  # nadir

        # Project Sun onto the plane perpendicular to z_body
        sun_perp = sun_inertial - np.dot(sun_inertial, z) * z
        norm_sun_perp = np.linalg.norm(sun_perp)

        if norm_sun_perp < _SUN_PROJECTION_TOL:
            ref = v_hat[k]  # fallback to velocity direction
        else:
            ref = sun_perp / norm_sun_perp

        x, y, _ = orthonormal_triad_from_primary_secondary(z, ref)
        dcm[k] = dcm_from_body_axes(x, y, z)

    return dcm
