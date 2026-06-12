# Session Report — Sample & Laser Calculations (Python Implementation)

**Date:** 2026-06-12
**Working directory:** `/sdf/home/b/bpoult/Excitation_Fraction/`
**Python version:** 3.12.3
**pytest version:** 9.0.3

---

## 1. Project Context

### Source Material

The spreadsheet `SAMPLE & LASER CALCULATIONS.xlsx` was used as the specification for this implementation. Its full documentation is in `SAMPLE_LASER_CALCULATIONS_README.md`. The spreadsheet contains two tabs:

- **Tab 1 (SAMPLE CONCENTRATION):** Given a target absorbance, what concentration and mass of sample is required?
- **Tab 2 (LASER FLUENCE - 400 nm):** Given that absorbance and a target average excitation fraction `<fexc>`, what laser pulse parameters are needed?

### Experiment

The sample is **[Co(bpy)₃][Cl]₃** dissolved in an **ACN:DMSO** solvent mixture, excited at **393 nm** on a liquid microjet of known diameter.

### Goal

Convert the spreadsheet into a set of typed Python functions and dataclasses that:
1. Are physically correct and well-documented
2. Resolve known issues in the original spreadsheet (see Section 8)
3. Serve as the computation backend for a future **Dash web GUI**

---

## 2. Directory Structure

```
Excitation_Fraction/
├── SAMPLE & LASER CALCULATIONS.xlsx    # Original spreadsheet
├── SAMPLE_LASER_CALCULATIONS_README.md # Spreadsheet documentation
├── IMPLEMENTATION_PLAN.md              # Pre-implementation design plan
├── SESSION_REPORT.md                   # This file
└── src/
    ├── __init__.py                     # Package exports
    ├── models.py                       # Dataclasses: SampleConfig, ConcentrationResult, FluenceResult
    ├── calculations.py                 # calculate_concentration(), calculate_fluence()
    └── tests/
        ├── __init__.py                 # Makes tests/ a package
        └── test_calculations.py        # 17 pytest tests
```

Both `src/` and `src/tests/` are proper Python packages (contain `__init__.py`), enabling clean imports:

```python
from src.calculations import calculate_concentration, calculate_fluence
from src.models import SampleConfig
```

---

## 3. `models.py` — Dataclasses

Dataclasses were chosen over plain dicts or tuples because:
- Fields are named and statically typed — self-documenting and IDE-friendly
- `dataclasses.asdict()` produces JSON-serializable output, required for passing data between Dash callbacks and components
- More structured than tuples, which would require fragile positional unpacking

### `SampleConfig`

Holds parameters that are **shared between both calculation functions**. Passed as the first argument to both `calculate_concentration` and `calculate_fluence`. This design means `target_absorbance` and `extinction_coeff` never need to be duplicated, directly resolving the manual-copy issue in the original spreadsheet (Tab 2 `B2`).

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `sample_name` | `str` | — | Human-readable sample name. Metadata; used for plot labels in the future GUI. |
| `extinction_coeff` | `float` | M⁻¹cm⁻¹ | Molar extinction coefficient at the excitation wavelength. |
| `molecular_weight` | `float` | g/mol | Molecular weight of the solute. |
| `solvent_ratio` | `str` | — | Solvent system description, e.g. `"ACN:DMSO 306:1"`. Metadata; used for plot labels. |

### `ConcentrationResult`

Return type of `calculate_concentration()` (Tab 1).

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `transmission` | `float` | — | Fraction of laser light transmitted through the jet. Derived from Beer-Lambert: T = 10^(−A). |
| `concentration_mM` | `float` | mM | Required molar concentration of the sample solution. |
| `mass_mg` | `float` | mg | Mass of solute to weigh out and dissolve in the reservoir. |

### `FluenceResult`

Return type of `calculate_fluence()` (Tab 2).

| Field | Type | Units | Description |
|-------|------|-------|-------------|
| `pulse_energy_uJ` | `float` | µJ | Required laser pulse energy to achieve `<fexc>`. |
| `avg_power_mW` | `float` | mW | Average laser power at the given repetition rate. |
| `avg_power_uW` | `float` | µW | Average laser power (alternate unit). |
| `fluence_mJ_cm2` | `float` | mJ/cm² | Pulse fluence at the sample position. |
| `n_photons_per_pulse` | `float` | — | Number of photons per pulse. |
| `fexc_front` | `float` | — | Excitation fraction at the front face of the jet (highest fluence). |
| `fexc_back` | `float` | — | Excitation fraction at the back face of the jet (lowest fluence, attenuated by full OD). |
| `peak_intensity_W_cm2` | `float` | W/cm² | Peak intensity assuming the specified pulse duration. |
| `pulse_duration_s` | `float` | s | Pulse duration echoed back from the function input. |

---

## 4. `calculations.py` — Functions

### Physical Constants

Defined as module-level private constants:

| Constant | Value | Description |
|----------|-------|-------------|
| `_H` | `6.62607015e-34` J·s | Planck's constant (CODATA 2018) |
| `_C` | `299_792_458.0` m/s | Speed of light (exact) |
| `_EPS_TO_SIGMA` | `1000·ln(10) / 6.02214076e23` | Conversion factor ε (M⁻¹cm⁻¹) → σ (cm²/molecule) |

**Important:** `_EPS_TO_SIGMA` is computed precisely as `1000·ln(10)/Nₐ ≈ 3.82353×10⁻²¹` rather than using the spreadsheet's hardcoded approximation `3.82e-21`. This gives higher numerical accuracy.

---

### `calculate_concentration()`

**File:** `src/calculations.py:32`

**Signature:**
```python
def calculate_concentration(
    config: SampleConfig,
    jet_diameter_um: float,
    reservoir_volume_mL: float,
    target_absorbance: float,
) -> ConcentrationResult
```

**Parameter Reference:**

| Parameter | Units | Description |
|-----------|-------|-------------|
| `config` | — | `SampleConfig` instance (provides `extinction_coeff`, `molecular_weight`) |
| `jet_diameter_um` | µm | Diameter of the liquid microjet; this is the optical path length `l` |
| `reservoir_volume_mL` | mL | Total volume of sample solution in the reservoir |
| `target_absorbance` | — | Target optical density (OD) at the excitation wavelength |

**Physics — Beer-Lambert Law:**

$$A = \varepsilon \cdot c \cdot l$$

Rearranged to solve for concentration:

$$c \, (\text{M}) = \frac{A}{\varepsilon \cdot l}$$

where `l` is the jet diameter converted from µm to cm (`× 1e-4`).

**Step-by-step derivation:**

```
1. transmission    = 10^(−A)
2. path_length_cm  = jet_diameter_um × 1e-4
3. concentration_M = A / (ε × path_length_cm)
4. concentration_mM = concentration_M × 1000
5. mass_mg         = concentration_M × (reservoir_volume_mL / 1000) × MW × 1000
```

---

### `calculate_fluence()`

**File:** `src/calculations.py:80`

**Signature:**
```python
def calculate_fluence(
    config: SampleConfig,
    target_absorbance: float,
    wavelength_nm: float,
    spot_size_v_um: float,
    spot_size_h_um: float,
    rep_rate_Hz: float,
    target_fexc: float,
    pulse_duration_s: float = 50e-15,
) -> FluenceResult
```

**Parameter Reference:**

| Parameter | Units | Default | Description |
|-----------|-------|---------|-------------|
| `config` | — | — | `SampleConfig` instance (provides `extinction_coeff`) |
| `target_absorbance` | — | — | OD of sample at excitation wavelength |
| `wavelength_nm` | nm | — | Central wavelength of excitation pulse |
| `spot_size_v_um` | µm FWHM | — | Vertical laser spot size (full diameter) |
| `spot_size_h_um` | µm FWHM | — | Horizontal laser spot size (full diameter) |
| `rep_rate_Hz` | Hz | — | Laser pulse repetition rate |
| `target_fexc` | — | — | Target spatially-averaged excitation fraction `<fexc>` |
| `pulse_duration_s` | s | `50e-15` | Pulse duration for peak intensity calculation (50 fs default) |

**Physics — Excitation Fraction:**

The excitation fraction `fexc` is the probability that a molecule absorbs a photon per pulse. In the linear (low-fluence) regime:

$$f_\text{exc} = \sigma \cdot \Phi$$

where:
- **σ** is the absorption cross section (cm²/molecule)
- **Φ** is the photon fluence (photons/cm²)

**Cross-section conversion:**

$$\sigma \, (\text{cm}^2) = \varepsilon \, (\text{M}^{-1}\text{cm}^{-1}) \times \frac{1000 \cdot \ln(10)}{N_A}$$

**Beam attenuation through jet depth:**

The laser is attenuated as it passes through the absorbing jet. The fluence at depth `z` follows Beer-Lambert:

$$\Phi(z) = \Phi_0 \cdot 10^{-\varepsilon c z}$$

The pulse energy is solved at the **jet midpoint** (attenuated by `10^(−A/2)`), which represents the spatially-averaged excitation condition. Front and back face values are derived from this:

- `fexc_front = <fexc> / 10^(−A/2)` — front sees more fluence than midpoint
- `fexc_back = fexc_front × 10^(−A)` — back is attenuated by full OD relative to front

**Step-by-step derivation:**

```
1.  sigma_cm2            = _EPS_TO_SIGMA × ε
2.  energy_per_photon_J  = (h × c) / (λ_nm × 1e-9)
3.  beam_area_cm2        = π × (spot_v_um/2) × (spot_h_um/2) × 1e-8
4.  midpoint_attenuation = 10^(−A/2)
5.  pulse_energy_J       = (energy_per_photon × <fexc> × beam_area) /
                           (midpoint_attenuation × sigma)
6.  pulse_energy_uJ      = pulse_energy_J × 1e6
7.  avg_power_mW         = pulse_energy_J × rep_rate_Hz × 1000
8.  avg_power_uW         = avg_power_mW × 1000
9.  fluence_mJ_cm2       = (pulse_energy_J × 1000) / beam_area_cm2
10. n_photons_per_pulse  = pulse_energy_J / energy_per_photon_J
11. fexc_front           = <fexc> / midpoint_attenuation
12. fexc_back            = fexc_front × 10^(−A)
13. peak_intensity       = (fluence_mJ_cm2 / 1000) / pulse_duration_s
14. echo pulse_duration_s into FluenceResult
```

**Linear regime validity:** The formula `fexc = σ·Φ` is accurate when `fexc << 1`. When `fexc_front` approaches or exceeds ~0.5, saturation effects become significant and the full expression `fexc = 1 − e^(−σΦ)` should be used. No warning is raised in the current implementation; the caller is responsible for checking this condition.

---

## 5. Test Suite — `src/tests/test_calculations.py`

### Framework & Methodology

- **pytest** with `pytest.approx(rel=1e-4)` for all numerical assertions (relative tolerance of 0.01%)
- Expected values were pre-computed independently in Python before writing the test assertions, confirming they match the spreadsheet formulas precisely
- Tests are organised into three classes corresponding to logical groupings

### Default Test Inputs

These match the spreadsheet default values documented in `SAMPLE_LASER_CALCULATIONS_README.md`:

**`SampleConfig`:**

| Field | Value |
|-------|-------|
| `sample_name` | `"[Co(bpy)3][Cl]3"` |
| `extinction_coeff` | `123.0` M⁻¹cm⁻¹ |
| `molecular_weight` | `633.698` g/mol |
| `solvent_ratio` | `"ACN:DMSO 306:1"` |

**`calculate_concentration` inputs:**

| Parameter | Value | Units |
|-----------|-------|-------|
| `jet_diameter_um` | `5.0` | µm |
| `reservoir_volume_mL` | `35.0` | mL |
| `target_absorbance` | `0.025` | — |

**`calculate_fluence` inputs:**

| Parameter | Value | Units |
|-----------|-------|-------|
| `target_absorbance` | `0.025` | — |
| `wavelength_nm` | `393.0` | nm |
| `spot_size_v_um` | `240.0` | µm FWHM |
| `spot_size_h_um` | `100.0` | µm FWHM |
| `rep_rate_Hz` | `33000.0` | Hz |
| `target_fexc` | `0.24` | — |
| `pulse_duration_s` | `50e-15` | s |

---

### Test Results

**Run command:**
```bash
cd /sdf/home/b/bpoult/Excitation_Fraction
python3 -m pytest src/tests/test_calculations.py -v
```

**Result: 17 passed in 0.11s**

| # | Test Class | Test Name | Expected Value | Status |
|---|-----------|-----------|----------------|--------|
| 1 | `TestCalculateConcentration` | `test_transmission` | `0.94406` | PASSED |
| 2 | `TestCalculateConcentration` | `test_concentration_mM` | `406.504 mM` | PASSED |
| 3 | `TestCalculateConcentration` | `test_mass_mg` | `9016.03 mg` | PASSED |
| 4 | `TestCalculateFluence` | `test_pulse_energy_uJ` | `50.041 µJ` | PASSED |
| 5 | `TestCalculateFluence` | `test_avg_power_mW` | `1651.36 mW` | PASSED |
| 6 | `TestCalculateFluence` | `test_avg_power_uW` | `1,651,355.5 µW` | PASSED |
| 7 | `TestCalculateFluence` | `test_fluence_mJ_cm2` | `265.476 mJ/cm²` | PASSED |
| 8 | `TestCalculateFluence` | `test_n_photons_per_pulse` | `9.900 × 10¹³` | PASSED |
| 9 | `TestCalculateFluence` | `test_fexc_front` | `0.24701` | PASSED |
| 10 | `TestCalculateFluence` | `test_fexc_back` | `0.23319` | PASSED |
| 11 | `TestCalculateFluence` | `test_peak_intensity_W_cm2` | `5.310 × 10¹² W/cm²` | PASSED |
| 12 | `TestCalculateFluence` | `test_pulse_duration_echoed` | `50e-15 s` | PASSED |
| 13 | `TestEdgeCases` | `test_zero_absorbance_transmission` | `1.0` | PASSED |
| 14 | `TestEdgeCases` | `test_custom_pulse_duration` | `100e-15 s`, `I/2` | PASSED |
| 15 | `TestEdgeCases` | `test_fexc_front_greater_than_back` | `fexc_front > fexc_back` | PASSED |
| 16 | `TestEdgeCases` | `test_fexc_average_bracketed` | `fexc_back < 0.24 < fexc_front` | PASSED |
| 17 | `TestEdgeCases` | `test_avg_power_uW_is_mW_times_1000` | exact unit relationship | PASSED |

---

## 6. Verified Numerical Results (Default Inputs)

Full output of both functions under the default spreadsheet inputs:

### `calculate_concentration` outputs

| Field | Value | Units |
|-------|-------|-------|
| `transmission` | `0.944061` | — |
| `concentration_mM` | `406.504` | mM |
| `mass_mg` | `9016.03` | mg |

### `calculate_fluence` outputs

| Field | Value | Units |
|-------|-------|-------|
| `pulse_energy_uJ` | `50.041` | µJ |
| `avg_power_mW` | `1651.36` | mW |
| `avg_power_uW` | `1,651,355.5` | µW |
| `fluence_mJ_cm2` | `265.476` | mJ/cm² |
| `n_photons_per_pulse` | `9.900 × 10¹³` | — |
| `fexc_front` | `0.24701` | — |
| `fexc_back` | `0.23319` | — |
| `peak_intensity_W_cm2` | `5.310 × 10¹²` | W/cm² |
| `pulse_duration_s` | `5.0 × 10⁻¹⁴` | s |

### Intermediate values (for reference)

| Quantity | Value | Units |
|----------|-------|-------|
| Absorption cross section σ | `4.7029 × 10⁻¹⁹` | cm²/molecule |
| Energy per photon (393 nm) | `5.0546 × 10⁻¹⁹` | J/photon |
| Beam area (240 × 100 µm ellipse) | `1.8850 × 10⁻⁴` | cm² |
| Midpoint attenuation `10^(−A/2)` | `0.97163` | — |

---

## 7. Known Issues Resolved

All three known issues documented in `SAMPLE_LASER_CALCULATIONS_README.md` were resolved in this implementation:

| Issue (from README) | Original Spreadsheet Behaviour | Resolution in Python |
|---------------------|-------------------------------|----------------------|
| **Tab 2 absorbance is a manual copy** | Tab 2 cell `B2` must be hand-updated when Tab 1 `B4` changes | Both functions accept `target_absorbance` as a direct parameter. A single Python variable can be passed to both, eliminating the duplication. |
| **Extinction coefficient typo** | Tab 2 `H2` = `124` M⁻¹cm⁻¹ (incorrect) | Correct value `123` M⁻¹cm⁻¹ used in `SampleConfig`. No value is hardcoded in the functions themselves; `extinction_coeff` is always sourced from the config object. |
| **Pulse duration hardcoded at 50 fs** | `J14` formula hardcodes `5e-14` s; cannot be changed without editing the cell | Exposed as `pulse_duration_s` parameter with `50e-15` as a named default. The value is also echoed back in `FluenceResult.pulse_duration_s` for display in the GUI. |

---

## 8. Design Decisions

### Why dataclasses?

The target GUI is **Dash** (Plotly). Dash callbacks pass data as JSON-serializable Python objects between components. `dataclasses.asdict()` produces a plain dict directly usable in this pipeline, while also giving named, typed fields during development.

### Why a shared `SampleConfig`?

Parameters like `extinction_coeff` and `molecular_weight` are used in both Tab 1 and Tab 2. Wrapping them in a shared config object:
- Eliminates the need to pass the same values to both functions separately
- Makes it trivial to change one value (e.g., swap sample) and have both functions update
- Maps directly to a single "sample configuration" panel in the future GUI

### Why are `sample_name` and `solvent_ratio` in `SampleConfig`?

They do not affect any calculation. They are included so that plot titles, axis labels, and result displays in the Dash GUI can be automatically annotated with the sample identity and solvent system without requiring separate state management.

### Class vs. standalone functions?

Standalone functions were chosen over a class. A class would add complexity (instantiation, `self`) without benefit, since there is no mutable shared state. The `SampleConfig` dataclass provides the necessary grouping of shared inputs.

---

## 9. Next Steps

The following work was planned in the original session but not yet implemented:

### `plots.py` — Plotly Figures

Four figures to be implemented as standalone functions, each accepting the relevant result dataclass and returning a `plotly.graph_objects.Figure`:

| # | Function | X-axis | Y-axis | Uses |
|---|----------|--------|--------|------|
| 1 | `plot_od_vs_concentration()` | Concentration (mM) | Absorbance (OD) | `ConcentrationResult`, `SampleConfig` |
| 2 | `plot_fexc_vs_depth()` | Depth through jet (µm) | fexc(z) | `FluenceResult`, jet diameter |
| 3 | `plot_pulse_energy_vs_fexc()` | `<fexc>` | Pulse energy (µJ) | `SampleConfig`, fluence inputs |
| 4 | `plot_peak_intensity_vs_pulse_energy()` | Pulse energy (µJ) | Peak intensity (W/cm²) | `FluenceResult` |

### `app.py` — Dash Web GUI

Two-tab layout mirroring the spreadsheet:

- **Tab 1 panel:** Numeric inputs for all `calculate_concentration` parameters → results card + Plot 1
- **Tab 2 panel:** Numeric inputs for all `calculate_fluence` parameters → results card + Plots 2–4
- **Shared state:** `dcc.Store` component holds `target_absorbance` and `SampleConfig` fields, so Tab 2 automatically reflects Tab 1 without any manual copy step
- **Sample/solvent metadata** displayed in plot titles and result labels

### To run the tests in a new session:

```bash
cd /sdf/home/b/bpoult/Excitation_Fraction
python3 -m pytest src/tests/test_calculations.py -v
```

### To use the functions interactively:

```python
import sys
sys.path.insert(0, "/sdf/home/b/bpoult/Excitation_Fraction")

from src.models import SampleConfig
from src.calculations import calculate_concentration, calculate_fluence

config = SampleConfig(
    sample_name="[Co(bpy)3][Cl]3",
    extinction_coeff=123.0,
    molecular_weight=633.698,
    solvent_ratio="ACN:DMSO 306:1",
)

conc = calculate_concentration(config, jet_diameter_um=5.0, reservoir_volume_mL=35.0, target_absorbance=0.025)
flux = calculate_fluence(config, target_absorbance=0.025, wavelength_nm=393.0,
                         spot_size_v_um=240.0, spot_size_h_um=100.0,
                         rep_rate_Hz=33000.0, target_fexc=0.24)

print(conc)
print(flux)
```
