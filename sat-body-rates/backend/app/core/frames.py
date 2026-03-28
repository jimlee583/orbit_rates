"""Reference-frame helpers and rotation utilities.

This module is intentionally minimal for the MVP.  It provides basic
rotation-matrix constructors and a stub for future DCM / quaternion
operations.

Future work
-----------
* Full DCM ↔ quaternion conversion suite.
* LVLH (Hill) frame construction from orbital state vectors.
* ECI ↔ ECEF ↔ LVLH chain with proper Earth-rotation modeling.
* Quaternion SLERP for attitude interpolation.
"""

import numpy as np
from numpy.typing import NDArray


def rotation_x(angle_rad: float) -> NDArray[np.float64]:
    """Elementary rotation matrix about the X axis (right-hand rule)."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [1.0, 0.0, 0.0],
        [0.0,   c,   s],
        [0.0,  -s,   c],
    ])


def rotation_y(angle_rad: float) -> NDArray[np.float64]:
    """Elementary rotation matrix about the Y axis (right-hand rule)."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [  c, 0.0,  -s],
        [0.0, 1.0, 0.0],
        [  s, 0.0,   c],
    ])


def rotation_z(angle_rad: float) -> NDArray[np.float64]:
    """Elementary rotation matrix about the Z axis (right-hand rule)."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [  c,   s, 0.0],
        [ -s,   c, 0.0],
        [0.0, 0.0, 1.0],
    ])


def euler_to_dcm_321(
    roll_rad: float, pitch_rad: float, yaw_rad: float
) -> NDArray[np.float64]:
    """Build a 3-2-1 (yaw → pitch → roll) DCM from Euler angles.

    This is placed here as a convenience for future high-fidelity
    attitude work.  The current MVP does not use full DCM propagation.
    """
    return rotation_x(roll_rad) @ rotation_y(pitch_rad) @ rotation_z(yaw_rad)
