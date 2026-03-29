"""Core engineering tests for the satellite body-rate calculator.

Coverage
--------
1. Nadir body rates: q ≈ −n, p ≈ 0, r ≈ 0
2. DCM orthogonality: ‖C·Cᵀ − I‖_F < 1e-13 for all modes and time steps
3. Euler angles: roll = pitch = yaw = 0 for nadir pointing (body = LVLH)
4. Sun-nadir geometry: z_body aligned with nadir at every time step
5. DCM determinant: det(C) = +1 (proper rotation, not reflection)
6. Runtime warnings: inclination and low-beta warnings are emitted
"""

import warnings

import numpy as np
import pytest

from backend.app.core import body_rates as br
from backend.app.core import orbit, attitude

# ---------------------------------------------------------------------------
# Shared test parameters
# ---------------------------------------------------------------------------

ALTITUDE_KM = 550.0
DURATION_MIN = 90.0
NUM_POINTS = 360

# Number of endpoint samples to skip when checking interior accuracy.
# Endpoints use one-sided differences; skipping 2 on each side is conservative.
_SKIP = 2


# ---------------------------------------------------------------------------
# Module-scoped fixture — computed once and reused by all nadir tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def nadir_run():
    """Full nadir-mode run at 550 km, 90 min, 360 samples."""
    n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
    time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
    dcm_bi, dcm_lvlh = attitude.generate_attitude_dcms(
        time_s, n_rad_s, "nadir", 0.0
    )
    p, q, r = br.compute_body_rates_from_dcms(dcm_bi, time_s)
    return {
        "n_rad_s": n_rad_s,
        "time_s": time_s,
        "dcm_bi": dcm_bi,
        "dcm_lvlh": dcm_lvlh,
        "p": p,
        "q": q,
        "r": r,
    }


# ===========================================================================
# 1. Nadir body rates
# ===========================================================================

class TestNadirBodyRates:
    """Requirement: q ≈ −n, p ≈ 0, r ≈ 0 for nadir pointing.

    The antisymmetric finite-difference formula applied to a rotation by a
    finite angle θ = n·Δt extracts sin(θ)/Δt, not θ/Δt.  The theoretically
    exact extracted rate is therefore sin(n·Δt)/Δt [rad/s], which differs
    from n by n³·Δt²/6 ≈ 2.85 × 10⁻⁶ deg/s at 550 km / 360 samples / 90 min.
    Tests assert against this discrete-formula reference, not against the
    continuous ideal n, so that a correct implementation passes exactly.
    """

    @staticmethod
    def _expected_q_deg_s(n_rad_s: float, time_s: np.ndarray) -> float:
        """Exact pitch rate that the discrete formula should return [deg/s].

        For constant angular velocity ω = n and uniform time step Δt the
        antisymmetric extraction gives sin(n·Δt)/Δt at every sample.
        """
        dt = float(np.diff(time_s)[0])
        return -np.degrees(np.sin(n_rad_s * dt) / dt)

    def test_pitch_rate_equals_discrete_formula(self, nadir_run):
        """q must match sin(n·Δt)/Δt at every interior sample.

        This is the exact output of the antisymmetric DCM differencing method
        for a rigid body rotating at constant rate.  Floating-point residuals
        should be below 1 × 10⁻¹⁰ deg/s.
        """
        expected = self._expected_q_deg_s(
            nadir_run["n_rad_s"], nadir_run["time_s"]
        )
        q = nadir_run["q"]
        np.testing.assert_allclose(
            q[_SKIP:-_SKIP], expected,
            atol=1e-10,
            err_msg="Pitch rate q should match sin(n·Δt)/Δt for nadir pointing",
        )

    def test_pitch_rate_within_truncation_error_of_n(self, nadir_run):
        """q must also be close to −n within the known O(n·(n·Δt)²/6) error.

        This confirms the physical interpretation: the finite-difference
        rate converges to the true orbital rate as Δt → 0.
        """
        n_rad_s = nadir_run["n_rad_s"]
        dt = float(np.diff(nadir_run["time_s"])[0])
        # Theoretical truncation: n − sin(n·Δt)/Δt = n³·Δt²/6 + O((n·Δt)⁴)
        truncation_deg_s = np.degrees(n_rad_s**3 * dt**2 / 6.0)
        n_deg_s = np.degrees(n_rad_s)
        q = nadir_run["q"]
        np.testing.assert_allclose(
            q[_SKIP:-_SKIP], -n_deg_s,
            atol=2.0 * truncation_deg_s,   # 2× for rounding headroom
            err_msg="Pitch rate q should be within truncation error of −n",
        )

    def test_roll_rate_near_zero(self, nadir_run):
        """p must be zero — nadir pointing has no roll dynamics."""
        p = nadir_run["p"]
        np.testing.assert_allclose(
            p[_SKIP:-_SKIP], 0.0,
            atol=1e-10,
            err_msg="Roll rate p should be zero for nadir pointing",
        )

    def test_yaw_rate_near_zero(self, nadir_run):
        """r must be zero — nadir pointing has no yaw dynamics."""
        r = nadir_run["r"]
        np.testing.assert_allclose(
            r[_SKIP:-_SKIP], 0.0,
            atol=1e-10,
            err_msg="Yaw rate r should be zero for nadir pointing",
        )

    def test_endpoint_pitch_rate_matches_discrete_formula(self, nadir_run):
        """Endpoints (one-sided differences) must also match sin(n·Δt)/Δt.

        For constant ω the one-sided and central estimates are identical, so
        the same reference value and tight tolerance apply.
        """
        expected = self._expected_q_deg_s(
            nadir_run["n_rad_s"], nadir_run["time_s"]
        )
        q = nadir_run["q"]
        np.testing.assert_allclose(
            q[[0, -1]], expected,
            atol=1e-10,
            err_msg="Endpoint pitch rates should match sin(n·Δt)/Δt",
        )


# ===========================================================================
# 2. DCM orthogonality
# ===========================================================================

class TestDCMOrthogonality:
    """Requirement: ‖C·Cᵀ − I‖_F < 1e-13 for every returned DCM."""

    @pytest.mark.parametrize("mode,beta", [
        ("nadir",     0.0),
        ("velocity",  0.0),
        ("sun_nadir", 30.0),
        ("sun_nadir", 60.0),
    ])
    def test_dcm_bi_orthonormal(self, mode, beta):
        """body-from-inertial DCMs must be orthogonal for all attitude modes."""
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        dcm_bi, _ = attitude.generate_attitude_dcms(
            time_s, n_rad_s, mode, beta
        )
        # Vectorised: compute C·Cᵀ for all N steps simultaneously
        cct = np.einsum("nij,nkj->nik", dcm_bi, dcm_bi)          # (N, 3, 3)
        residuals = np.linalg.norm(cct - np.eye(3), axis=(-2, -1))  # (N,)
        assert np.max(residuals) < 1e-13, (
            f"mode={mode}, beta={beta}: max ‖C·Cᵀ−I‖_F = {np.max(residuals):.2e}"
        )

    def test_dcm_lvlh_orthonormal(self, nadir_run):
        """LVLH-from-inertial DCMs must also be orthogonal."""
        dcm_lvlh = nadir_run["dcm_lvlh"]
        cct = np.einsum("nij,nkj->nik", dcm_lvlh, dcm_lvlh)
        residuals = np.linalg.norm(cct - np.eye(3), axis=(-2, -1))
        assert np.max(residuals) < 1e-13, (
            f"max ‖C_LVLH·C_LVLHᵀ−I‖_F = {np.max(residuals):.2e}"
        )

    @pytest.mark.parametrize("mode,beta", [
        ("nadir",     0.0),
        ("sun_nadir", 45.0),
    ])
    def test_dcm_bi_determinant_is_plus_one(self, mode, beta):
        """det(C) must be +1 (proper rotation, not an improper reflection)."""
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        dcm_bi, _ = attitude.generate_attitude_dcms(
            time_s, n_rad_s, mode, beta
        )
        dets = np.linalg.det(dcm_bi)   # (N,)
        np.testing.assert_allclose(
            dets, 1.0,
            atol=1e-13,
            err_msg=f"mode={mode}: det(C_BI) must equal +1",
        )


# ===========================================================================
# 3. Euler angles for nadir pointing
# ===========================================================================

class TestNadirEulerAngles:
    """Requirement: roll = pitch = yaw = 0 for nadir pointing.

    For nadir mode the body frame IS the LVLH frame, so C_BL = I at every
    time step and all 3-2-1 Euler angles are identically zero.
    """

    def test_roll_is_zero(self, nadir_run):
        roll, _, _ = br.extract_euler_angles(
            nadir_run["dcm_bi"], nadir_run["dcm_lvlh"]
        )
        np.testing.assert_allclose(roll, 0.0, atol=1e-10)

    def test_pitch_is_zero(self, nadir_run):
        _, pitch, _ = br.extract_euler_angles(
            nadir_run["dcm_bi"], nadir_run["dcm_lvlh"]
        )
        np.testing.assert_allclose(pitch, 0.0, atol=1e-10)

    def test_yaw_is_zero(self, nadir_run):
        _, _, yaw = br.extract_euler_angles(
            nadir_run["dcm_bi"], nadir_run["dcm_lvlh"]
        )
        np.testing.assert_allclose(yaw, 0.0, atol=1e-10)


# ===========================================================================
# 4. Sun-nadir geometric correctness
# ===========================================================================

class TestSunNadirGeometry:
    """z_body must point toward nadir (−r̂) at every time step."""

    @pytest.mark.parametrize("beta", [15.0, 30.0, 60.0])
    def test_z_body_is_nadir(self, beta):
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        dcm_bi, _ = attitude.generate_attitude_dcms(
            time_s, n_rad_s, "sun_nadir", beta
        )

        # z_body in inertial coordinates = third row of C_BI expressed as a
        # column, i.e. C_BI^T · ê_z where ê_z = [0,0,1].
        # Equivalently, the third column of C_BI^T = third row of C_BI.
        z_body_inertial = dcm_bi[:, 2, :]   # (N, 3)  — third row of C_BI

        # Nadir direction in inertial frame: −r̂
        theta = n_rad_s * time_s
        N = len(time_s)
        r_hat = np.column_stack([np.cos(theta), np.sin(theta), np.zeros(N)])
        nadir = -r_hat

        np.testing.assert_allclose(
            z_body_inertial, nadir,
            atol=1e-12,
            err_msg=f"beta={beta}: z_body should equal nadir (−r̂)",
        )


# ===========================================================================
# 5. Runtime warnings
# ===========================================================================

class TestWarnings:
    """Verify that the appropriate UserWarnings are emitted."""

    def test_low_beta_warning_is_raised(self):
        """sun_nadir with |β| < 5° must emit a UserWarning."""
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        with pytest.warns(UserWarning, match="geometric singularity"):
            attitude.generate_attitude_dcms(time_s, n_rad_s, "sun_nadir", 2.0)

    def test_beta_zero_warning_is_raised(self):
        """sun_nadir with β = 0 is the exact singularity — must warn."""
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        with pytest.warns(UserWarning, match="geometric singularity"):
            attitude.generate_attitude_dcms(time_s, n_rad_s, "sun_nadir", 0.0)

    def test_no_warning_for_safe_beta(self):
        """sun_nadir with |β| >= 5° must not emit a singularity warning."""
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            # Should not raise — 5.0 is exactly at the boundary (strict <)
            attitude.generate_attitude_dcms(time_s, n_rad_s, "sun_nadir", 5.0)

    def test_nonzero_inclination_warning_is_raised(self):
        """Passing a non-zero inclination must emit a UserWarning."""
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        with pytest.warns(UserWarning, match="inclination_deg"):
            attitude.generate_attitude_dcms(
                time_s, n_rad_s, "nadir", 0.0, inclination_deg=97.6
            )

    def test_zero_inclination_no_warning(self):
        """inclination=0 must not emit a warning (geometrically consistent)."""
        n_rad_s = orbit.mean_motion_rad_s(ALTITUDE_KM)
        time_s = orbit.time_vector_s(DURATION_MIN, NUM_POINTS)
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            attitude.generate_attitude_dcms(
                time_s, n_rad_s, "nadir", 0.0, inclination_deg=0.0
            )
