"""Reference-frame helpers, rotation utilities, and DCM/quaternion operations.

Coordinate-frame conventions used throughout this application
=============================================================

Inertial frame (simplified ECI for this MVP)
---------------------------------------------
A right-handed frame with the orbit lying in the X–Y plane:

* **X_I** — along the initial satellite radius vector at *t = 0*.
* **Y_I** — 90° ahead in the orbit plane (prograde at *t = 0*).
* **Z_I** — orbit-normal direction (completes the right-handed triad).

For a circular orbit the position and velocity unit vectors are:

    r̂(t) = [ cos θ,  sin θ,  0 ]
    v̂(t) = [−sin θ,  cos θ,  0 ]     θ = n · t

LVLH (Local Vertical / Local Horizontal) frame
-----------------------------------------------
Constructed at every time step from the instantaneous orbital geometry:

* **x_LVLH** = v̂   (along-track / velocity / RAM direction)
* **y_LVLH** = z_LVLH × x_LVLH   (cross-track, ≈ orbit anti-normal)
* **z_LVLH** = −r̂  (nadir — toward the Earth's centre)

Body frame
----------
Axes are aligned with the spacecraft structure.  For a nadir-pointing
satellite, the body frame coincides with the LVLH frame:

* **x_body** — along-track (RAM)
* **y_body** — cross-track
* **z_body** — nadir (instrument boresight toward Earth)

Sign conventions
----------------
* All rotation matrices are **body-from-inertial** (C_BI): they transform
  a vector expressed in the inertial frame into the body frame.
* The rows of C_BI are the body-frame unit axes expressed in inertial
  coordinates.
* Angular velocity **ω** is the angular velocity of the body frame
  with respect to the inertial frame, expressed in the body frame.

Euler sequence
--------------
The **3-2-1 (ZYX)** sequence is used exclusively for display output:

    C = R_x(φ) · R_y(θ) · R_z(ψ)

where φ = roll, θ = pitch, ψ = yaw.  Extraction:

    θ  = −arcsin(C[0,2])
    φ  =  atan2(C[1,2], C[2,2])
    ψ  =  atan2(C[0,1], C[0,0])

These Euler angles represent the **body deviation from the LVLH frame**,
*not* body-from-inertial.  They are derived from C_BL = C_BI · C_LI^T
and are used for human-readable output only.
"""

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Elementary rotation matrices (right-hand rule)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Vector utilities
# ---------------------------------------------------------------------------

def normalize(v: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return the unit vector of *v*.  Raises ValueError if ‖v‖ ≈ 0."""
    n = np.linalg.norm(v)
    if n < 1e-15:
        raise ValueError("Cannot normalise a near-zero vector.")
    return v / n


# ---------------------------------------------------------------------------
# DCM construction helpers
# ---------------------------------------------------------------------------

def dcm_from_body_axes(
    x_body: NDArray[np.float64],
    y_body: NDArray[np.float64],
    z_body: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Assemble a body-from-inertial DCM from three orthonormal body axes.

    Each axis must be a 3-element array expressed in inertial coordinates.
    The returned 3×3 matrix has the body axes as its rows.
    """
    return np.array([x_body, y_body, z_body])


def orthonormal_triad_from_primary_secondary(
    z_primary: NDArray[np.float64],
    ref_secondary: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Build an orthonormal right-handed triad from a primary Z axis and a
    secondary reference direction.

    The triad is constructed so that:
    * z_body  = z_primary  (normalised)
    * y_body  = z_body × ref_secondary  (normalised)
    * x_body  = y_body × z_body

    This guarantees x_body lies in the half-plane containing *ref_secondary*
    (relative to z_body) and the triad is exactly orthonormal and right-handed.

    Parameters
    ----------
    z_primary :
        Desired body Z direction (will be normalised).
    ref_secondary :
        Reference direction used to resolve the remaining rotational freedom
        about z_primary.  Must not be (anti-)parallel to z_primary.

    Returns
    -------
    x_body, y_body, z_body — each a unit 3-vector in inertial coordinates.
    """
    z = normalize(z_primary)
    y_raw = np.cross(z, ref_secondary)
    y = normalize(y_raw)
    x = np.cross(y, z)
    return x, y, z


def euler_to_dcm_321(
    roll_rad: float, pitch_rad: float, yaw_rad: float,
) -> NDArray[np.float64]:
    """Build a 3-2-1 (ZYX: yaw → pitch → roll) body-from-inertial DCM."""
    return rotation_x(roll_rad) @ rotation_y(pitch_rad) @ rotation_z(yaw_rad)


# ---------------------------------------------------------------------------
# DCM → Euler-angle extraction (3-2-1 sequence)
# ---------------------------------------------------------------------------

def dcm_to_euler_321(C: NDArray[np.float64]) -> tuple[float, float, float]:
    """Extract 3-2-1 Euler angles (roll, pitch, yaw) from a single DCM.

    Returns angles in **radians**.

    Near gimbal lock (|C[0,2]| ≈ 1, i.e. pitch ≈ ±90°), roll and yaw
    become poorly determined.  The arcsin argument is clamped to [−1, 1]
    for numerical safety.
    """
    pitch = -np.arcsin(np.clip(C[0, 2], -1.0, 1.0))
    roll = np.arctan2(C[1, 2], C[2, 2])
    yaw = np.arctan2(C[0, 1], C[0, 0])
    return float(roll), float(pitch), float(yaw)


def dcm_to_euler_321_batch(
    dcm: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Vectorised 3-2-1 Euler extraction for an (N, 3, 3) DCM history.

    Returns (roll_rad, pitch_rad, yaw_rad) — each shape (N,).
    """
    pitch = -np.arcsin(np.clip(dcm[:, 0, 2], -1.0, 1.0))
    roll = np.arctan2(dcm[:, 1, 2], dcm[:, 2, 2])
    yaw = np.arctan2(dcm[:, 0, 1], dcm[:, 0, 0])
    return roll, pitch, yaw


# ---------------------------------------------------------------------------
# DCM ↔ Quaternion
# ---------------------------------------------------------------------------

def dcm_to_quaternion(C: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert a single 3×3 DCM to a unit quaternion [q0, q1, q2, q3].

    Uses the Shepperd method for numerical stability.
    q0 is the scalar part; (q1, q2, q3) is the vector part.
    The returned quaternion is normalised and sign-chosen so that q0 ≥ 0.
    """
    tr = np.trace(C)
    candidates = np.array([
        tr,
        2.0 * C[0, 0] - tr,
        2.0 * C[1, 1] - tr,
        2.0 * C[2, 2] - tr,
    ])
    k = int(np.argmax(candidates))

    if k == 0:
        s = 0.5 * np.sqrt(1.0 + tr)
        q = np.array([
            s,
            (C[1, 2] - C[2, 1]) / (4.0 * s),
            (C[2, 0] - C[0, 2]) / (4.0 * s),
            (C[0, 1] - C[1, 0]) / (4.0 * s),
        ])
    elif k == 1:
        s = 0.5 * np.sqrt(1.0 + 2.0 * C[0, 0] - tr)
        q = np.array([
            (C[1, 2] - C[2, 1]) / (4.0 * s),
            s,
            (C[0, 1] + C[1, 0]) / (4.0 * s),
            (C[2, 0] + C[0, 2]) / (4.0 * s),
        ])
    elif k == 2:
        s = 0.5 * np.sqrt(1.0 + 2.0 * C[1, 1] - tr)
        q = np.array([
            (C[2, 0] - C[0, 2]) / (4.0 * s),
            (C[0, 1] + C[1, 0]) / (4.0 * s),
            s,
            (C[1, 2] + C[2, 1]) / (4.0 * s),
        ])
    else:
        s = 0.5 * np.sqrt(1.0 + 2.0 * C[2, 2] - tr)
        q = np.array([
            (C[0, 1] - C[1, 0]) / (4.0 * s),
            (C[2, 0] + C[0, 2]) / (4.0 * s),
            (C[1, 2] + C[2, 1]) / (4.0 * s),
            s,
        ])

    if q[0] < 0.0:
        q = -q
    return q / np.linalg.norm(q)


def quaternion_normalize(q: NDArray[np.float64]) -> NDArray[np.float64]:
    """Normalise a quaternion [q0, q1, q2, q3] to unit magnitude."""
    return q / np.linalg.norm(q)


# ---------------------------------------------------------------------------
# Skew-symmetric / angular-velocity helpers
# ---------------------------------------------------------------------------

def vee(S: NDArray[np.float64]) -> NDArray[np.float64]:
    """Extract the 3-vector from a skew-symmetric matrix.

    For the skew-symmetric matrix corresponding to ω = [ω_x, ω_y, ω_z]:

        [ω×] = [[  0,  −ω_z,  ω_y],
                [ ω_z,   0,  −ω_x],
                [−ω_y,  ω_x,   0 ]]

    The extraction is:  ω = [ S[2,1],  S[0,2],  S[1,0] ].
    """
    return np.array([S[2, 1], S[0, 2], S[1, 0]])
