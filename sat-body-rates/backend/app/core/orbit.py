"""Orbital-mechanics utilities for circular LEO orbits.

MVP assumptions
---------------
* Circular orbit (eccentricity = 0).
* Two-body Keplerian dynamics — no J2, drag, or third-body perturbations.
* Constant altitude throughout the simulation.

Future work
-----------
* Support eccentric orbits (compute true-anomaly time history).
* Add J2 secular-rate corrections for RAAN and argument of perigee.
* Accept TLE / state-vector inputs.
"""

import numpy as np
from numpy.typing import NDArray

# WGS-84 Earth gravitational parameter [km^3 / s^2]
MU_EARTH_KM3_S2: float = 398_600.4418

# Mean Earth radius [km]
R_EARTH_KM: float = 6_371.0


def mean_motion_rad_s(altitude_km: float) -> float:
    """Return the mean motion *n* [rad/s] for a circular orbit.

    Parameters
    ----------
    altitude_km:
        Altitude above the Earth's surface [km].  Must be positive.
    """
    r_km = R_EARTH_KM + altitude_km
    return float(np.sqrt(MU_EARTH_KM3_S2 / r_km**3))


def mean_motion_deg_s(altitude_km: float) -> float:
    """Return the mean motion *n* [deg/s] for a circular orbit."""
    return float(np.degrees(mean_motion_rad_s(altitude_km)))


def orbital_period_s(altitude_km: float) -> float:
    """Return the orbital period [s] for a circular orbit."""
    return 2.0 * np.pi / mean_motion_rad_s(altitude_km)


def time_vector_s(duration_min: float, num_points: int) -> NDArray[np.float64]:
    """Generate an equally-spaced time vector [s].

    Parameters
    ----------
    duration_min:
        Total simulation duration [min].
    num_points:
        Number of output samples (must be >= 2).
    """
    return np.linspace(0.0, duration_min * 60.0, num_points)
