"""Attitude-profile generators for supported pointing modes.

Sign convention (body-frame Euler angles, 3-2-1 sequence)
----------------------------------------------------------
* **Roll  (φ)** — rotation about the body X axis (along-track).
* **Pitch (θ)** — rotation about the body Y axis (cross-track).
* **Yaw   (ψ)** — rotation about the body Z axis (nadir).

All angles are returned in **degrees**.

MVP assumptions
---------------
* Nadir mode: the spacecraft maintains a perfect nadir-pointing attitude.
  The only non-zero rotation is a continuous pitch that tracks the orbital
  rate, keeping the Z-body axis aligned with the local vertical.  Roll and
  yaw are identically zero.

* Velocity mode: for this MVP, velocity-vector pointing produces the same
  profile as nadir pointing.  In a high-fidelity model the X-body axis
  would be aligned with the velocity vector (requiring a ~90° yaw offset
  in the LVLH frame), but that distinction is deferred to a future
  iteration.  **This is an intentional MVP simplification.**

* Sun-nadir mode: the spacecraft pitches at the orbital rate (like nadir)
  but also introduces a **sinusoidal yaw steering** driven by the solar
  beta angle.  This creates a distinct, nontrivial attitude profile that
  exercises all three Euler channels.  The yaw amplitude scales with
  |beta_deg| so that beta = 0 reduces to pure nadir.

  The simplified yaw-steering law is:
      ψ(t) = β · sin(n · t)
  where n is the orbital mean motion.  A small roll coupling term is added:
      φ(t) = −0.5 · β · sin(2 · n · t)
  to make the profile visually richer without implying physical accuracy.

Future work
-----------
* Replace Euler-angle profiles with full quaternion propagation.
* Implement true velocity-vector (LVLH X-axis) alignment.
* Model realistic sun-tracking yaw-steering laws (e.g., continuous
  sun-pointing with seasonal beta-angle variation).
* Support inertial / target-tracking pointing modes.
"""

import numpy as np
from numpy.typing import NDArray


def generate_attitude_profile(
    time_s: NDArray[np.float64],
    mean_motion_rad_s: float,
    attitude_mode: str,
    beta_deg: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Return (roll_deg, pitch_deg, yaw_deg) arrays over a time vector.

    Parameters
    ----------
    time_s:
        1-D array of time stamps [s].
    mean_motion_rad_s:
        Orbital mean motion *n* [rad/s].
    attitude_mode:
        One of ``"nadir"``, ``"velocity"``, ``"sun_nadir"``.
    beta_deg:
        Solar beta angle [deg].  Only used by the ``sun_nadir`` mode.

    Returns
    -------
    roll_deg, pitch_deg, yaw_deg:
        Euler-angle time histories in degrees.
    """
    n = mean_motion_rad_s

    # Pitch tracks the orbit for all modes (nadir-pointing baseline).
    # θ(t) = −n·t  (negative because the satellite rotates nose-down to
    # keep the nadir face pointed at the Earth).
    pitch_deg = np.degrees(-n * time_s)

    if attitude_mode == "nadir":
        roll_deg = np.zeros_like(time_s)
        yaw_deg = np.zeros_like(time_s)

    elif attitude_mode == "velocity":
        # MVP: identical to nadir. See module docstring.
        roll_deg = np.zeros_like(time_s)
        yaw_deg = np.zeros_like(time_s)

    elif attitude_mode == "sun_nadir":
        roll_deg, yaw_deg = _sun_nadir_steering(time_s, n, beta_deg)

    else:
        raise ValueError(f"Unknown attitude mode: {attitude_mode!r}")

    return roll_deg, pitch_deg, yaw_deg


def _sun_nadir_steering(
    time_s: NDArray[np.float64],
    n: float,
    beta_deg: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Simplified yaw-steering and roll coupling for sun-nadir mode.

    See the module-level docstring for the governing equations and
    caveats.
    """
    beta = beta_deg  # amplitude in degrees

    yaw_deg = beta * np.sin(n * time_s)
    roll_deg = -0.5 * beta * np.sin(2.0 * n * time_s)

    return roll_deg, yaw_deg
