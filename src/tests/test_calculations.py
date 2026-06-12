"""
test_calculations.py
--------------------
Validates calculate_concentration() and calculate_fluence() against the
default spreadsheet values documented in SAMPLE_LASER_CALCULATIONS_README.md.

All expected values are derived from the formulas in the README using the
default inputs listed there. Assertions use pytest.approx with rel=1e-4.

Default inputs
--------------
SampleConfig:
    sample_name      = "[Co(bpy)3][Cl]3"
    extinction_coeff = 123  M⁻¹cm⁻¹
    molecular_weight = 633.698  g/mol
    solvent_ratio    = "ACN:DMSO 306:1"

Tab 1 (calculate_concentration):
    jet_diameter_um      = 5       µm
    reservoir_volume_mL  = 35      mL
    target_absorbance    = 0.025

Tab 2 (calculate_fluence):
    target_absorbance  = 0.025
    wavelength_nm      = 393
    spot_size_v_um     = 240   µm FWHM
    spot_size_h_um     = 100   µm FWHM
    rep_rate_Hz        = 33000 Hz
    target_fexc        = 0.24
    pulse_duration_s   = 50e-15  s
"""

import pytest

from src.models import SampleConfig
from src.calculations import calculate_concentration, calculate_fluence


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_config() -> SampleConfig:
    return SampleConfig(
        sample_name="[Co(bpy)3][Cl]3",
        extinction_coeff=123.0,   # M⁻¹cm⁻¹
        molecular_weight=633.698, # g/mol
        solvent_ratio="ACN:DMSO 306:1",
    )


@pytest.fixture
def concentration_result(default_config):
    return calculate_concentration(
        config=default_config,
        jet_diameter_um=5.0,
        reservoir_volume_mL=35.0,
        target_absorbance=0.025,
    )


@pytest.fixture
def fluence_result(default_config):
    return calculate_fluence(
        config=default_config,
        target_absorbance=0.025,
        wavelength_nm=393.0,
        spot_size_v_um=240.0,
        spot_size_h_um=100.0,
        rep_rate_Hz=33000.0,
        target_fexc=0.24,
        pulse_duration_s=50e-15,
    )


# ---------------------------------------------------------------------------
# Tab 1 — calculate_concentration
# ---------------------------------------------------------------------------

class TestCalculateConcentration:

    def test_transmission(self, concentration_result):
        """T = 10^(-0.025) ≈ 0.94406"""
        assert concentration_result.transmission == pytest.approx(0.9440608762859234, rel=1e-4)

    def test_concentration_mM(self, concentration_result):
        """c = A / (ε · l) = 0.025 / (123 × 5e-4) = 406.504 mM"""
        assert concentration_result.concentration_mM == pytest.approx(406.50406504065046, rel=1e-4)

    def test_mass_mg(self, concentration_result):
        """m = c(M) × V(L) × MW(g/mol) × 1000 mg/g ≈ 9016.03 mg"""
        assert concentration_result.mass_mg == pytest.approx(9016.028455284553, rel=1e-4)


# ---------------------------------------------------------------------------
# Tab 2 — calculate_fluence
# ---------------------------------------------------------------------------

class TestCalculateFluence:

    def test_pulse_energy_uJ(self, fluence_result):
        """Pulse energy required for <fexc>=0.24 ≈ 50.041 µJ"""
        assert fluence_result.pulse_energy_uJ == pytest.approx(50.04107710076656, rel=1e-4)

    def test_avg_power_mW(self, fluence_result):
        """P = E(J) × rep_rate = 50.041e-6 × 33000 × 1000 ≈ 1651.36 mW"""
        assert fluence_result.avg_power_mW == pytest.approx(1651.3555443252963, rel=1e-4)

    def test_avg_power_uW(self, fluence_result):
        """avg_power_uW = avg_power_mW × 1000 ≈ 1651355.5 µW"""
        assert fluence_result.avg_power_uW == pytest.approx(1651355.5443252963, rel=1e-4)

    def test_fluence_mJ_cm2(self, fluence_result):
        """F = E(mJ) / beam_area(cm²) ≈ 265.476 mJ/cm²"""
        assert fluence_result.fluence_mJ_cm2 == pytest.approx(265.4761592743216, rel=1e-4)

    def test_n_photons_per_pulse(self, fluence_result):
        """N = E(J) / (hc/λ) ≈ 9.900e13"""
        assert fluence_result.n_photons_per_pulse == pytest.approx(99001657809225.86, rel=1e-4)

    def test_fexc_front(self, fluence_result):
        """fexc_front = <fexc> / 10^(-A/2) ≈ 0.24701"""
        assert fluence_result.fexc_front == pytest.approx(0.24700812652666276, rel=1e-4)

    def test_fexc_back(self, fluence_result):
        """fexc_back = fexc_front × 10^(-A) ≈ 0.23319"""
        assert fluence_result.fexc_back == pytest.approx(0.23319070837850547, rel=1e-4)

    def test_peak_intensity_W_cm2(self, fluence_result):
        """I = fluence(J/cm²) / pulse_duration ≈ 5.310e12 W/cm²"""
        assert fluence_result.peak_intensity_W_cm2 == pytest.approx(5309523185486.432, rel=1e-4)

    def test_pulse_duration_echoed(self, fluence_result):
        """pulse_duration_s must be echoed back unchanged"""
        assert fluence_result.pulse_duration_s == pytest.approx(50e-15, rel=1e-10)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_zero_absorbance_transmission(self, default_config):
        """At zero absorbance, transmission should be exactly 1.0"""
        result = calculate_concentration(
            config=default_config,
            jet_diameter_um=5.0,
            reservoir_volume_mL=35.0,
            target_absorbance=0.0,
        )
        assert result.transmission == pytest.approx(1.0, rel=1e-10)

    def test_custom_pulse_duration(self, default_config):
        """A non-default pulse duration should be echoed and affect peak intensity"""
        custom_duration = 100e-15  # 100 fs
        result = calculate_fluence(
            config=default_config,
            target_absorbance=0.025,
            wavelength_nm=393.0,
            spot_size_v_um=240.0,
            spot_size_h_um=100.0,
            rep_rate_Hz=33000.0,
            target_fexc=0.24,
            pulse_duration_s=custom_duration,
        )
        assert result.pulse_duration_s == pytest.approx(custom_duration, rel=1e-10)
        # Peak intensity should be half of the 50 fs case (same fluence, double duration)
        assert result.peak_intensity_W_cm2 == pytest.approx(5309523185486.432 / 2.0, rel=1e-4)

    def test_fexc_front_greater_than_back(self, fluence_result):
        """Front face always sees higher fluence than back face"""
        assert fluence_result.fexc_front > fluence_result.fexc_back

    def test_fexc_average_bracketed(self, fluence_result):
        """<fexc> should lie between fexc_back and fexc_front"""
        assert fluence_result.fexc_back < 0.24 < fluence_result.fexc_front

    def test_avg_power_uW_is_mW_times_1000(self, fluence_result):
        """avg_power_uW must equal avg_power_mW × 1000 exactly"""
        assert fluence_result.avg_power_uW == pytest.approx(
            fluence_result.avg_power_mW * 1000.0, rel=1e-10
        )
