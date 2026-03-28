"""Body-rate computation from Euler-angle time histories.

The body rates (p, q, r) are computed via numerical differentiation of
the roll, pitch, and yaw histories.  For the MVP this is a simple
finite-difference approach using ``numpy.gradient``, which is second-order
accurate at interior points and first-order at the endpoints.

MVP assumptions
---------------
* Small-angle / decoupled approximation: p ≈ dφ/dt, q ≈ dθ/dt,
  r ≈ dψ/dt.  The full kinematic relationship involves cross-coupling
  terms that depend on the current Euler angles, but for the small
  roll/yaw excursions produced by the current attitude models the
  decoupled approximation is adequate.

Future work
-----------
* Use the exact Euler-angle kinematic equations:
      p = φ̇ − ψ̇ sin θ
      q = θ̇ cos φ + ψ̇ cos θ sin φ
      r = −θ̇ sin φ + ψ̇ cos θ cos φ
* Switch to quaternion-based angular-velocity extraction.
"""

import numpy as np
from numpy.typing import NDArray


def compute_body_rates(
    time_s: NDArray[np.float64],
    roll_deg: NDArray[np.float64],
    pitch_deg: NDArray[np.float64],
    yaw_deg: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Differentiate Euler-angle histories to obtain body rates [deg/s].

    Parameters
    ----------
    time_s:
        1-D time vector [s].
    roll_deg, pitch_deg, yaw_deg:
        Euler-angle time histories [deg].

    Returns
    -------
    p_deg_s, q_deg_s, r_deg_s:
        Body angular-rate time histories [deg/s].
    """
    p_deg_s = np.gradient(roll_deg, time_s)
    q_deg_s = np.gradient(pitch_deg, time_s)
    r_deg_s = np.gradient(yaw_deg, time_s)
    return p_deg_s, q_deg_s, r_deg_s


def rate_summary(
    p_deg_s: NDArray[np.float64],
    q_deg_s: NDArray[np.float64],
    r_deg_s: NDArray[np.float64],
) -> dict[str, float]:
    """Return peak absolute body rates.

    Returns
    -------
    dict with keys ``max_abs_p_deg_s``, ``max_abs_q_deg_s``,
    ``max_abs_r_deg_s``.
    """
    return {
        "max_abs_p_deg_s": float(np.max(np.abs(p_deg_s))),
        "max_abs_q_deg_s": float(np.max(np.abs(q_deg_s))),
        "max_abs_r_deg_s": float(np.max(np.abs(r_deg_s))),
    }
