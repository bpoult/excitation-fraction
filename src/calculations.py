"""
calculations.py
---------------
Core physics calculations for sample concentration (Tab 1) and laser fluence
(Tab 2), based on the SAMPLE & LASER CALCULATIONS spreadsheet.

Functions
---------
calculate_concentration(config, jet_diameter_um, reservoir_volume_mL, target_absorbance)
    -> ConcentrationResult

calculate_fluence(config, target_absorbance, wavelength_nm, spot_size_v_um,
                  spot_size_h_um, rep_rate_Hz, target_fexc, pulse_duration_s)
    -> FluenceResult
"""

import math

from .models import SampleConfig, ConcentrationResult, FluenceResult

# Physical constants
_H = 6.62607015e-34   # Planck's constant (J·s)
_C = 299_792_458.0    # Speed of light (m/s)

# Conversion factor: ε (M⁻¹cm⁻¹) -> σ (cm²/molecule)
# σ = ε × 1000 · ln(10) / Nₐ
# = ε × 1000 × 2.302585 / 6.02214076e23
# ≈ ε × 3.82353e-21
_EPS_TO_SIGMA = 1000.0 * math.log(10) / 6.02214076e23  # cm² · M · cm


def calculate_concentration(
    config: SampleConfig,
    jet_diameter_um: float,
    reservoir_volume_mL: float,
    target_absorbance: float,
) -> ConcentrationResult:
    """
    Calculate the sample concentration and mass required to achieve a target
    absorbance in a liquid microjet (Tab 1).

    Uses the Beer-Lambert Law: A = ε · c · l

    Parameters
    ----------
    config : SampleConfig
        Shared sample parameters (extinction coefficient, molecular weight, etc.)
    jet_diameter_um : float
        Diameter of the liquid microjet, which is the optical path length (µm).
    reservoir_volume_mL : float
        Total volume of sample solution in the reservoir (mL).
    target_absorbance : float
        Target optical density (OD) of the sample at the excitation wavelength.

    Returns
    -------
    ConcentrationResult
        transmission, concentration_mM, mass_mg
    """
    # Laser transmission through jet: T = 10^(-A)
    transmission = 10.0 ** (-target_absorbance)

    # Rearranged Beer-Lambert: c(M) = A / (ε · l)
    # Convert jet diameter from µm to cm: 1 µm = 1e-4 cm
    path_length_cm = jet_diameter_um * 1e-4
    concentration_M = target_absorbance / (config.extinction_coeff * path_length_cm)
    concentration_mM = concentration_M * 1000.0

    # Mass: m(g) = c(mol/L) × V(L) × MW(g/mol)  →  mg
    reservoir_volume_L = reservoir_volume_mL / 1000.0
    mass_mg = concentration_M * reservoir_volume_L * config.molecular_weight * 1000.0

    return ConcentrationResult(
        transmission=transmission,
        concentration_mM=concentration_mM,
        mass_mg=mass_mg,
    )


def calculate_fluence(
    config: SampleConfig,
    target_absorbance: float,
    wavelength_nm: float,
    spot_size_v_um: float,
    spot_size_h_um: float,
    rep_rate_Hz: float,
    target_fexc: float,
    pulse_duration_s: float = 50e-15,
) -> FluenceResult:
    """
    Calculate the laser pulse parameters required to achieve a target average
    excitation fraction <fexc> in a liquid microjet (Tab 2).

    Uses fexc = σ · Φ with Beer-Lambert attenuation through the jet depth.
    The pulse energy is solved at the jet midpoint (attenuated by 10^(-A/2)).

    Parameters
    ----------
    config : SampleConfig
        Shared sample parameters (extinction coefficient, molecular weight, etc.)
    target_absorbance : float
        Optical density (OD) of the sample at the excitation wavelength.
    wavelength_nm : float
        Central wavelength of the excitation pulse (nm).
    spot_size_v_um : float
        Vertical laser spot size, full width at half maximum (µm FWHM).
    spot_size_h_um : float
        Horizontal laser spot size, full width at half maximum (µm FWHM).
    rep_rate_Hz : float
        Pulse repetition rate of the laser (Hz).
    target_fexc : float
        Target spatially-averaged excitation fraction <fexc> (dimensionless).
    pulse_duration_s : float, optional
        Pulse duration used for peak intensity calculation (s). Default 50 fs.

    Returns
    -------
    FluenceResult
        All output fields including pulse_duration_s echoed back.
    """
    # Absorption cross section: σ (cm²) = ε × 1000·ln(10) / Nₐ
    sigma_cm2 = _EPS_TO_SIGMA * config.extinction_coeff

    # Energy per photon: E = hc/λ  (λ in metres)
    energy_per_photon_J = (_H * _C) / (wavelength_nm * 1e-9)

    # Beam area (ellipse): A = π · a · b
    # spot_size_v/h are full diameters in µm; radii in µm → cm: × 1e-4
    # product of two (×1e-4) factors = ×1e-8
    beam_area_cm2 = math.pi * (spot_size_v_um / 2.0) * (spot_size_h_um / 2.0) * 1e-8

    # Midpoint attenuation factor: 10^(-A/2)
    midpoint_attenuation = 10.0 ** (-target_absorbance / 2.0)

    # Pulse energy: rearrange <fexc> = σ · Φ_mid for E
    # Φ_mid = E / (beam_area · energy_per_photon) · midpoint_attenuation
    # E (J) = <fexc> · energy_per_photon · beam_area / (midpoint_attenuation · σ)
    pulse_energy_J = (
        energy_per_photon_J * target_fexc * beam_area_cm2
    ) / (midpoint_attenuation * sigma_cm2)
    pulse_energy_uJ = pulse_energy_J * 1e6

    # Average power
    avg_power_W = pulse_energy_J * rep_rate_Hz
    avg_power_mW = avg_power_W * 1000.0
    avg_power_uW = avg_power_mW * 1000.0

    # Fluence (mJ/cm²): F = E(J) / beam_area → convert J to mJ
    fluence_mJ_cm2 = (pulse_energy_J * 1000.0) / beam_area_cm2

    # Photon count per pulse
    n_photons_per_pulse = pulse_energy_J / energy_per_photon_J

    # fexc at front face of jet: sees higher fluence than midpoint
    # fexc_front = <fexc> / 10^(-A/2)
    fexc_front = target_fexc / midpoint_attenuation

    # fexc at back face: attenuated by full OD relative to front
    fexc_back = fexc_front * (10.0 ** (-target_absorbance))

    # Peak intensity: I = fluence (J/cm²) / pulse_duration (s)
    peak_intensity_W_cm2 = (fluence_mJ_cm2 / 1000.0) / pulse_duration_s

    return FluenceResult(
        pulse_energy_uJ=pulse_energy_uJ,
        avg_power_mW=avg_power_mW,
        avg_power_uW=avg_power_uW,
        fluence_mJ_cm2=fluence_mJ_cm2,
        n_photons_per_pulse=n_photons_per_pulse,
        fexc_front=fexc_front,
        fexc_back=fexc_back,
        peak_intensity_W_cm2=peak_intensity_W_cm2,
        pulse_duration_s=pulse_duration_s,
    )
