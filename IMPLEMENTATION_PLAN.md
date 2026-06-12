# Implementation Plan — Sample & Laser Calculations (Python)

## Overview

Convert the two-tab Excel spreadsheet (`SAMPLE & LASER CALCULATIONS.xlsx`) into a set of Python functions backed by typed dataclasses. This is the foundation layer before building a Dash web GUI on top.

---

## Directory Structure

```
Excitation_Fraction/
└── src/
    ├── __init__.py
    ├── models.py
    ├── calculations.py
    └── tests/
        ├── __init__.py
        └── test_calculations.py
```

Both `src/` and `src/tests/` contain `__init__.py` files, making them proper Python packages. This allows clean imports (e.g., `from src.calculations import calculate_concentration`) and full pytest test discovery.

---

## `models.py`

Three dataclasses covering shared config, Tab 1 outputs, and Tab 2 outputs.

### `SampleConfig`

Holds parameters shared between both calculation functions. Passed as the first argument to both `calculate_concentration` and `calculate_fluence`.

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `sample_name` | `str` | — | Name of the sample (metadata, used for plot labels) |
| `extinction_coeff` | `float` | M⁻¹cm⁻¹ | Molar extinction coefficient at excitation wavelength |
| `molecular_weight` | `float` | g/mol | Molecular weight of the solute |
| `solvent_ratio` | `str` | — | Solvent description, e.g. `"ACN:DMSO 306:1"` (metadata) |

### `ConcentrationResult`

Output of `calculate_concentration` (Tab 1).

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `transmission` | `float` | — | Fraction of laser light transmitted through the jet |
| `concentration_mM` | `float` | mM | Required molar concentration of sample |
| `mass_mg` | `float` | mg | Mass of solute to dissolve in the reservoir |

### `FluenceResult`

Output of `calculate_fluence` (Tab 2).

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `pulse_energy_uJ` | `float` | µJ | Required pulse energy |
| `avg_power_mW` | `float` | mW | Average laser power |
| `avg_power_uW` | `float` | µW | Average laser power (alternate unit) |
| `fluence_mJ_cm2` | `float` | mJ/cm² | Pulse fluence at sample |
| `n_photons_per_pulse` | `float` | — | Number of photons per pulse |
| `fexc_front` | `float` | — | Excitation fraction at jet front face |
| `fexc_back` | `float` | — | Excitation fraction at jet back face |
| `peak_intensity_W_cm2` | `float` | W/cm² | Peak intensity assuming Gaussian pulse |
| `pulse_duration_s` | `float` | s | Pulse duration echoed back from input |

---

## `calculations.py`

### `calculate_concentration`

```python
def calculate_concentration(
    config: SampleConfig,
    jet_diameter_um: float,       # µm — optical path length through jet
    reservoir_volume_mL: float,   # mL — total reservoir volume
    target_absorbance: float,     # OD — target optical density at excitation wavelength
) -> ConcentrationResult
```

**Physics:** Beer-Lambert Law — `A = ε · c · l`

**Steps:**
1. `transmission = 10 ** -target_absorbance`
2. `concentration_mM = (target_absorbance / (extinction_coeff × jet_diameter_um × 1e-4)) × 1000`
   - `jet_diameter_um × 1e-4` converts µm → cm
3. `mass_mg = (concentration_mM / 1000) × (reservoir_volume_mL / 1000) × molecular_weight × 1000`

---

### `calculate_fluence`

```python
def calculate_fluence(
    config: SampleConfig,
    target_absorbance: float,      # OD
    wavelength_nm: float,          # nm
    spot_size_v_um: float,         # µm FWHM, vertical
    spot_size_h_um: float,         # µm FWHM, horizontal
    rep_rate_Hz: float,            # Hz
    target_fexc: float,            # dimensionless, target average excitation fraction
    pulse_duration_s: float = 50e-15,  # s, default 50 fs
) -> FluenceResult
```

**Physics:** Excitation fraction `fexc = σ · Φ`, with Beer-Lambert attenuation through jet depth.

**Steps:**
1. `sigma = 3.82e-21 × extinction_coeff` — cross section (cm²), where `3.82e-21 = 1000·ln(10)/Nₐ`
2. `energy_per_photon = (6.62607015e-34 × 299792458) / (wavelength_nm × 1e-9)` — J/photon
3. `beam_area = π × (spot_size_v_um / 2) × (spot_size_h_um / 2) × 1e-8` — cm²
4. `pulse_energy_uJ = (energy_per_photon × target_fexc × beam_area × 1e6) / (10^(-target_absorbance/2) × sigma)`
   - `10^(-A/2)` accounts for attenuation at jet midpoint
5. `avg_power_mW = (pulse_energy_uJ × 1e-6) × rep_rate_Hz × 1000`
6. `avg_power_uW = avg_power_mW × 1000`
7. `fluence_mJ_cm2 = (pulse_energy_uJ / 1000) / beam_area`
8. `n_photons_per_pulse = (pulse_energy_uJ × 1e-6) / energy_per_photon`
9. `fexc_front = target_fexc / 10^(-target_absorbance / 2)`
10. `fexc_back = fexc_front × 10^(-target_absorbance)`
11. `peak_intensity_W_cm2 = (fluence_mJ_cm2 / 1000) / pulse_duration_s`
12. Echo `pulse_duration_s` into result

---

## `tests/test_calculations.py`

Validates both functions against the default spreadsheet values from the README using `pytest.approx` with a relative tolerance of `1e-4`.

### Tab 1 Test Inputs (from README defaults)

| Parameter | Value |
|-----------|-------|
| `sample_name` | `"[Co(bpy)3][Cl]3"` |
| `extinction_coeff` | `123` M⁻¹cm⁻¹ |
| `molecular_weight` | `633.698` g/mol |
| `solvent_ratio` | `"ACN:DMSO 306:1"` |
| `jet_diameter_um` | `5` µm |
| `reservoir_volume_mL` | `35` mL |
| `target_absorbance` | `0.025` |

### Tab 2 Test Inputs (from README defaults)

| Parameter | Value |
|-----------|-------|
| `target_absorbance` | `0.025` |
| `wavelength_nm` | `393` |
| `spot_size_v_um` | `240` µm FWHM |
| `spot_size_h_um` | `100` µm FWHM |
| `rep_rate_Hz` | `33000` Hz |
| `target_fexc` | `0.24` |
| `pulse_duration_s` | `50e-15` s |

### Test Functions

- `test_transmission()` — verifies `ConcentrationResult.transmission`
- `test_concentration_mM()` — verifies `ConcentrationResult.concentration_mM`
- `test_mass_mg()` — verifies `ConcentrationResult.mass_mg`
- `test_pulse_energy_uJ()` — verifies `FluenceResult.pulse_energy_uJ`
- `test_avg_power_mW()` — verifies `FluenceResult.avg_power_mW`
- `test_avg_power_uW()` — verifies `FluenceResult.avg_power_uW`
- `test_fluence_mJ_cm2()` — verifies `FluenceResult.fluence_mJ_cm2`
- `test_n_photons_per_pulse()` — verifies `FluenceResult.n_photons_per_pulse`
- `test_fexc_front()` — verifies `FluenceResult.fexc_front`
- `test_fexc_back()` — verifies `FluenceResult.fexc_back`
- `test_peak_intensity_W_cm2()` — verifies `FluenceResult.peak_intensity_W_cm2`
- `test_pulse_duration_echoed()` — verifies `FluenceResult.pulse_duration_s` is echoed correctly

---

## Known Issues Resolved

| Issue (from README) | Resolution |
|---------------------|------------|
| Tab 2 `B2` is a manual copy of Tab 1 `B4` | Both functions accept `target_absorbance` directly; a single variable can be passed to both |
| Extinction coefficient typo (124 vs 123) | Correct value `123` used in `SampleConfig`; no hardcoding in functions |
| Pulse duration hardcoded at 50 fs | Exposed as `pulse_duration_s` parameter with `50e-15` default; echoed in `FluenceResult` |

---

## Future Work

- `plots.py` — Plotly figure-generating functions (OD vs. concentration, fexc vs. jet depth, pulse energy vs. target fexc, peak intensity vs. pulse energy)
- `app.py` — Dash web GUI with two-tab layout mirroring the spreadsheet
