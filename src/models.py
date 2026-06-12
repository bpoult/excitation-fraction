"""
models.py
---------
Dataclasses for sample/laser calculation inputs and outputs.

SampleConfig   — shared parameters passed to both calculation functions
ConcentrationResult — outputs of calculate_concentration() (Tab 1)
FluenceResult       — outputs of calculate_fluence() (Tab 2)
"""

from dataclasses import dataclass


@dataclass
class SampleConfig:
    """
    Shared sample parameters used by both Tab 1 and Tab 2 calculations.

    Attributes
    ----------
    sample_name : str
        Human-readable name of the sample (metadata; used for plot labels).
    extinction_coeff : float
        Molar extinction coefficient at the excitation wavelength (M⁻¹cm⁻¹).
    molecular_weight : float
        Molecular weight of the solute (g/mol).
    solvent_ratio : str
        Description of the solvent system, e.g. "ACN:DMSO 306:1" (metadata).
    """

    sample_name: str
    extinction_coeff: float   # M⁻¹cm⁻¹
    molecular_weight: float   # g/mol
    solvent_ratio: str        # metadata only, e.g. "ACN:DMSO 306:1"


@dataclass
class ConcentrationResult:
    """
    Output of calculate_concentration() — Tab 1 results.

    Attributes
    ----------
    transmission : float
        Fraction of laser light transmitted through the jet (dimensionless).
        Derived from Beer-Lambert: T = 10^(-A).
    concentration_mM : float
        Required molar concentration of sample (mM).
    mass_mg : float
        Mass of solute to dissolve in the reservoir (mg).
    """

    transmission: float       # dimensionless
    concentration_mM: float   # mM
    mass_mg: float            # mg


@dataclass
class FluenceResult:
    """
    Output of calculate_fluence() — Tab 2 results.

    Attributes
    ----------
    pulse_energy_uJ : float
        Required laser pulse energy (µJ).
    avg_power_mW : float
        Average laser power (mW).
    avg_power_uW : float
        Average laser power (µW).
    fluence_mJ_cm2 : float
        Pulse fluence at the sample (mJ/cm²).
    n_photons_per_pulse : float
        Number of photons per pulse (dimensionless).
    fexc_front : float
        Excitation fraction at the front face of the jet (dimensionless).
    fexc_back : float
        Excitation fraction at the back face of the jet (dimensionless).
    peak_intensity_W_cm2 : float
        Peak intensity, assuming the specified pulse duration (W/cm²).
    pulse_duration_s : float
        Pulse duration echoed back from the function input (s).
    """

    pulse_energy_uJ: float        # µJ
    avg_power_mW: float           # mW
    avg_power_uW: float           # µW
    fluence_mJ_cm2: float         # mJ/cm²
    n_photons_per_pulse: float    # dimensionless
    fexc_front: float             # dimensionless
    fexc_back: float              # dimensionless
    peak_intensity_W_cm2: float   # W/cm²
    pulse_duration_s: float       # s (echoed from input)
