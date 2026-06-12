# Dash Implementation Plan — Sample & Laser Calculations GUI

**Date written:** 2026-06-12
**Working directory:** `/sdf/home/b/bpoult/Excitation_Fraction/`
**Python version:** 3.12.3
**Status:** Ready to implement — backend (models, calculations, tests) is complete.

---

## 0. Purpose of This Document

This document is a complete, self-contained specification for implementing the Dash GUI layer
on top of the existing Python calculation backend. A new session should be able to read this
file (and the files listed in Section 2) and implement everything without any additional
clarification from the user.

All design decisions described here have already been agreed with the user. Do not re-ask
questions that are already answered in this document.

---

## 1. Project Context

### What this project is

A web-based GUI for two experimental design calculations used in ultrafast transient absorption
spectroscopy on a liquid microjet of **[Co(bpy)₃][Cl]₃** in ACN:DMSO, excited at ~393 nm.

- **Tab 1 (Sample Concentration):** Given a target absorbance, what concentration and mass
  of sample is needed?
- **Tab 2 (Laser Fluence):** Given that absorbance and a target average excitation fraction
  `<fexc>`, what laser pulse parameters are needed?

### Source documents

| File | Purpose |
|------|---------|
| `SAMPLE & LASER CALCULATIONS.xlsx` | Original Excel spreadsheet (specification source) |
| `SAMPLE_LASER_CALCULATIONS_README.md` | Full documentation of all spreadsheet cells and formulas |
| `IMPLEMENTATION_PLAN.md` | Design plan for the backend (already implemented) |
| `SESSION_REPORT.md` | Full record of the backend implementation session |

---

## 2. What Already Exists (Do Not Modify)

The backend is complete, tested, and passing. Do not change these files unless a bug is found.

```
src/
├── __init__.py                 # Exports SampleConfig, ConcentrationResult,
│                               # FluenceResult, calculate_concentration,
│                               # calculate_fluence
├── models.py                   # SampleConfig, ConcentrationResult, FluenceResult
├── calculations.py             # calculate_concentration(), calculate_fluence()
└── tests/
    ├── __init__.py
    └── test_calculations.py    # 17 pytest tests — all passing
```

### Quick reference: function signatures

```python
from src.models import SampleConfig, ConcentrationResult, FluenceResult
from src.calculations import calculate_concentration, calculate_fluence

# Tab 1
def calculate_concentration(
    config: SampleConfig,
    jet_diameter_um: float,       # µm — optical path length
    reservoir_volume_mL: float,   # mL
    target_absorbance: float,     # OD
) -> ConcentrationResult:
    ...

# Tab 2
def calculate_fluence(
    config: SampleConfig,
    target_absorbance: float,     # OD — synced from Tab 1
    wavelength_nm: float,         # nm
    spot_size_v_um: float,        # µm FWHM
    spot_size_h_um: float,        # µm FWHM
    rep_rate_Hz: float,           # Hz
    target_fexc: float,           # dimensionless
    pulse_duration_s: float = 50e-15,  # s
) -> FluenceResult:
    ...
```

### Default input values (from spreadsheet)

These are the values to pre-populate the GUI with on first load (also stored in
`configs/default.json`).

| Parameter | Value | Units |
|-----------|-------|-------|
| `sample_name` | `"[Co(bpy)3][Cl]3"` | — |
| `extinction_coeff` | `123.0` | M⁻¹cm⁻¹ |
| `molecular_weight` | `633.698` | g/mol |
| `solvent_ratio` | `"ACN:DMSO 306:1"` | — |
| `jet_diameter_um` | `5.0` | µm |
| `reservoir_volume_mL` | `35.0` | mL |
| `target_absorbance` | `0.025` | — |
| `wavelength_nm` | `393.0` | nm |
| `spot_size_v_um` | `240.0` | µm FWHM |
| `spot_size_h_um` | `100.0` | µm FWHM |
| `rep_rate_Hz` | `33000.0` | Hz |
| `target_fexc` | `0.24` | — |
| `pulse_duration_s` | `50e-15` | s |

### To verify the backend is still passing before starting

```bash
cd /sdf/home/b/bpoult/Excitation_Fraction
python -m pytest src/tests/test_calculations.py -v
```

Expected: **17 passed**.

---

## 3. Dependencies

Install all required packages before implementing:

```bash
pip install dash dash-bootstrap-components plotly
```

| Package | Purpose |
|---------|---------|
| `dash` | Core web framework (includes `dcc`, `html`, `Input`, `Output`, `State`, `callback`) |
| `dash-bootstrap-components` | Bootstrap-styled layout components (`dbc.Tabs`, `dbc.Card`, `dbc.Modal`, `dbc.Row`, `dbc.Col`, etc.) |
| `plotly` | Figure generation (already a Dash dependency, but used directly in `plots.py`) |

Verify imports work:

```python
import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
```

---

## 4. New Files to Create

```
Excitation_Fraction/
├── configs/                    # NEW — top-level, separate from src/
│   └── default.json            # NEW — pre-loaded default configuration
└── src/
    ├── config_io.py            # NEW — save / load / list JSON configs
    ├── plots.py                # NEW — 4 Plotly figure functions
    └── app.py                  # NEW — Dash application
```

**Why `configs/` is at the top level (not inside `src/`):** The user explicitly requested
this so that config files can be transferred between machines or version-controlled separately
from the code.

---

## 5. `configs/default.json`

Create this file first. It is the factory default, pre-loaded when the app starts and
listed first in the config dropdown.

```json
{
    "name": "Default — [Co(bpy)3][Cl]3",
    "created": "2026-06-12T00:00:00",
    "sample_name": "[Co(bpy)3][Cl]3",
    "extinction_coeff": 123.0,
    "molecular_weight": 633.698,
    "solvent_ratio": "ACN:DMSO 306:1",
    "jet_diameter_um": 5.0,
    "reservoir_volume_mL": 35.0,
    "target_absorbance": 0.025,
    "wavelength_nm": 393.0,
    "spot_size_v_um": 240.0,
    "spot_size_h_um": 100.0,
    "rep_rate_Hz": 33000.0,
    "target_fexc": 0.24,
    "pulse_duration_s": 5e-14
}
```

**Field descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Human-readable display name shown in the dropdown |
| `created` | `str` | ISO 8601 timestamp; set automatically by `save_config()` |
| All other fields | `float` or `str` | Direct input values for both calculation functions |

---

## 6. `src/config_io.py`

Handles all JSON config file I/O. Contains three public functions. No Dash imports — pure
Python. The `configs_dir` argument should always be passed as an absolute path resolved
relative to this file:

```python
import pathlib
CONFIGS_DIR = pathlib.Path(__file__).parent.parent / "configs"
```

### `list_configs(configs_dir: pathlib.Path) -> list[dict]`

- Scans `configs_dir` for all `*.json` files.
- Returns a list of dicts sorted by filename, each with:
  - `"label"`: the `name` field from inside the JSON (used as dropdown display text)
  - `"value"`: the absolute filepath as a string (used as dropdown value)
- If `configs_dir` does not exist, return an empty list (do not raise).

```python
def list_configs(configs_dir: pathlib.Path) -> list[dict]:
    """
    Return a list of dicts suitable for a dcc.Dropdown options list.
    Each dict has keys 'label' (config name string) and 'value' (filepath string).
    Sorted alphabetically by filename. Returns [] if directory does not exist.
    """
```

### `load_config(filepath: str | pathlib.Path) -> dict`

- Reads and JSON-parses the file at `filepath`.
- Returns the full dict including `name` and `created` fields.
- Raises `FileNotFoundError` if the file does not exist.
- Raises `ValueError` if the JSON is malformed or missing required fields.

Required fields that must be present (raise `ValueError` if any are missing):

```
sample_name, extinction_coeff, molecular_weight, solvent_ratio,
jet_diameter_um, reservoir_volume_mL, target_absorbance,
wavelength_nm, spot_size_v_um, spot_size_h_um,
rep_rate_Hz, target_fexc, pulse_duration_s
```

```python
def load_config(filepath: str | pathlib.Path) -> dict:
    """
    Load a config JSON file. Returns the full dict.
    Raises FileNotFoundError or ValueError on bad input.
    """
```

### `save_config(configs_dir: pathlib.Path, name: str, data: dict) -> pathlib.Path`

- Derives a safe filename from `name` by lowercasing, replacing spaces/special chars with
  underscores, and appending `.json`.
  - Example: `"My Config #2"` → `my_config__2.json`
  - Use `re.sub(r'[^\w]+', '_', name.strip().lower()) + '.json'`
- Sets `data["name"] = name` and `data["created"] = datetime.now().isoformat()`.
- Creates `configs_dir` if it does not exist (`mkdir(parents=True, exist_ok=True)`).
- Writes JSON with `indent=4`.
- Returns the `pathlib.Path` of the written file.
- **Does NOT check for existing files** — the overwrite check is handled in the Dash
  callback (the GUI confirms before calling this function).

```python
def save_config(configs_dir: pathlib.Path, name: str, data: dict) -> pathlib.Path:
    """
    Save data as a named config JSON file. Always overwrites if file exists.
    Returns the path of the written file.
    """
```

---

## 7. `src/plots.py`

Four standalone functions. Each accepts calculation results/inputs and returns a
`plotly.graph_objects.Figure`. No Dash imports. All figures should use a consistent
dark theme for visual coherence in the app:

```python
PLOT_TEMPLATE = "plotly_dark"
MARKER_COLOR = "#EF553B"   # red/orange — visually distinct operating point marker
LINE_COLOR   = "#636EFA"   # Plotly default blue — sweep line
```

Each figure must include:
- A descriptive title that includes the sample name from `SampleConfig.sample_name`
- Labelled axes with units
- A highlighted operating point marker (filled circle, size 12, color `MARKER_COLOR`)
  at the current input values

---

### `plot_od_vs_concentration`

```python
def plot_od_vs_concentration(
    config: SampleConfig,
    result: ConcentrationResult,
    target_absorbance: float,
    jet_diameter_um: float,
) -> go.Figure:
```

**Purpose:** Show the Beer-Lambert relationship between concentration and absorbance for the
current jet geometry and sample. Helps the user understand where their target OD falls on
the curve.

**Sweep:** Generate ~200 concentration values from 0 to 3× the current `result.concentration_mM`.
For each concentration `c` (mM), compute `OD = extinction_coeff * (c / 1000) * jet_diameter_um * 1e-4`.

**Operating point:** Dot at `(result.concentration_mM, target_absorbance)`.

**Axis labels:**
- X: `"Concentration (mM)"`
- Y: `"Absorbance (OD)"`

---

### `plot_fexc_vs_depth`

```python
def plot_fexc_vs_depth(
    config: SampleConfig,
    result: FluenceResult,
    jet_diameter_um: float,
    target_absorbance: float,
) -> go.Figure:
```

**Purpose:** Show how the excitation fraction varies across the jet depth due to Beer-Lambert
attenuation. Helps the user understand the spatial inhomogeneity of excitation.

**Physics:** At depth `z` (µm) into the jet (0 = front face, `jet_diameter_um` = back face):

```
OD_at_z = target_absorbance * (z / jet_diameter_um)
fexc(z) = fexc_front * 10^(-OD_at_z)
```

**Sweep:** 300 evenly-spaced depth values from 0 to `jet_diameter_um`.

**Operating point markers:** Three dots:
- Front face: `(0, result.fexc_front)`
- Midpoint: `(jet_diameter_um / 2, target_fexc)` — label as `<fexc>`
- Back face: `(jet_diameter_um, result.fexc_back)`

Add a horizontal dashed line at `y = target_fexc` (the average) to make the midpoint clear.

**Axis labels:**
- X: `"Depth into jet (µm)"`
- Y: `"fexc(z)"`

---

### `plot_pulse_energy_vs_fexc`

```python
def plot_pulse_energy_vs_fexc(
    config: SampleConfig,
    target_absorbance: float,
    wavelength_nm: float,
    spot_size_v_um: float,
    spot_size_h_um: float,
    rep_rate_Hz: float,
    pulse_duration_s: float,
    current_fexc: float,
    current_result: FluenceResult,
    fexc_max: float = 2.0,
) -> go.Figure:
```

**Purpose:** Show the required pulse energy as a function of target `<fexc>`. The user can
see how much energy is needed across a range of excitation fractions, and where their current
operating point sits.

**Note on axes:** X = pulse energy (µJ), Y = `<fexc>`. This is deliberately inverted from
the typical convention (fexc as input) because the user thinks of pulse energy as the
experimental dial they turn.

**Sweep:** Generate 300 `<fexc>` values from 0 (exclusive — start at a small positive value
like `1e-4`) to `fexc_max`. For each, call `calculate_fluence(...)` to get pulse energy.
Extract `pulse_energy_uJ` from each result.

**`fexc_max` parameter:** Defaults to `2.0`. Exposed as a numeric input in the GUI (see
Section 8). The user can change it to zoom in or extend the range.

**Operating point:** Dot at `(current_result.pulse_energy_uJ, current_fexc)`.

**Axis labels:**
- X: `"Pulse Energy (µJ)"`
- Y: `"⟨fexc⟩"`

---

### `plot_fluence_vs_pulse_energy`

```python
def plot_fluence_vs_pulse_energy(
    config: SampleConfig,
    target_absorbance: float,
    wavelength_nm: float,
    spot_size_v_um: float,
    spot_size_h_um: float,
    rep_rate_Hz: float,
    pulse_duration_s: float,
    current_fexc: float,
    current_result: FluenceResult,
    fexc_max: float = 2.0,
) -> go.Figure:
```

**Purpose:** Show fluence (mJ/cm²) as a function of pulse energy (µJ). This is a linear
relationship for fixed beam geometry; the plot makes it easy to read off the fluence at any
pulse energy.

**Sweep:** Same sweep as `plot_pulse_energy_vs_fexc` — same 300 `<fexc>` values. For each
result, extract `(pulse_energy_uJ, fluence_mJ_cm2)`.

**Operating point:** Dot at `(current_result.pulse_energy_uJ, current_result.fluence_mJ_cm2)`.

**Axis labels:**
- X: `"Pulse Energy (µJ)"`
- Y: `"Fluence (mJ/cm²)"`

---

## 8. `src/app.py` — Dash Application

### Entry point

```bash
cd /sdf/home/b/bpoult/Excitation_Fraction
python -m src.app
```

The file must be runnable as a module. The bottom of `app.py` must be:

```python
if __name__ == "__main__":
    app.run(debug=True)
```

### Imports and path setup

`app.py` lives inside `src/`, so relative imports work. The `configs/` directory must be
resolved relative to the package root:

```python
import pathlib
CONFIGS_DIR = pathlib.Path(__file__).parent.parent / "configs"
```

### Bootstrap theme

Use `dash_bootstrap_components.themes.DARKLY` for a dark theme consistent with the Plotly
dark plot template:

```python
import dash_bootstrap_components as dbc
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
```

---

### Layout overview

```
app.layout
└── dbc.Container (fluid=True)
    ├── dcc.Store(id="shared-state")          # Holds SampleConfig fields + target_absorbance
    ├── [Top bar]                             # Config dropdown + save controls
    └── dbc.Tabs
        ├── dbc.Tab — "Sample Concentration"  # Tab 1
        └── dbc.Tab — "Laser Fluence"         # Tab 2
```

---

### `dcc.Store` — shared state

**ID:** `"shared-state"`

**Storage type:** `"memory"` (lives for the browser session; reset on page reload)

**Contents (a dict):**

```python
{
    "sample_name":       str,
    "extinction_coeff":  float,
    "molecular_weight":  float,
    "solvent_ratio":     str,
    "target_absorbance": float,
}
```

This store is written by the Tab 1 callback and read by the Tab 2 callback. It eliminates
the manual copy problem from the original spreadsheet (Tab 2 `B2`).

---

### Top bar

A `dbc.Row` above the tabs containing two logical groups:

**Group 1 — Load config:**

| Component | ID | Description |
|-----------|-----|-------------|
| `dcc.Dropdown` | `"config-dropdown"` | Options populated from `list_configs(CONFIGS_DIR)`. `value` is the filepath string. `clearable=False`. |
| `dbc.Button` | `"load-config-btn"` | Label: "Load". Triggers the load callback. |

**Group 2 — Save config:**

| Component | ID | Description |
|-----------|-----|-------------|
| `dbc.Input` | `"save-name-input"` | Placeholder: "Config name…". Type: text. |
| `dbc.Button` | `"save-config-btn"` | Label: "Save". Triggers overwrite-check callback. |

**Overwrite confirmation modal:**

| Component | ID | Description |
|-----------|-----|-------------|
| `dbc.Modal` | `"overwrite-modal"` | Hidden by default (`is_open=False`). |
| `dbc.ModalHeader` | — | Text: "Config already exists" |
| `dbc.ModalBody` | `"overwrite-modal-body"` | Text: "A config named '…' already exists. Overwrite it?" (name filled dynamically) |
| `dbc.Button` (in footer) | `"overwrite-confirm-btn"` | Label: "Overwrite". Color: "danger". |
| `dbc.Button` (in footer) | `"overwrite-cancel-btn"` | Label: "Cancel". Color: "secondary". |

---

### Tab 1 — Sample Concentration

#### Input panel (`dbc.Card`)

All inputs are `dbc.Input` components with `type="number"` except `sample_name` and
`solvent_ratio` which are `type="text"`.

| Label | Component ID | Default value | Step / min |
|-------|-------------|---------------|------------|
| Sample name | `"input-sample-name"` | `"[Co(bpy)3][Cl]3"` | — |
| Extinction coeff (M⁻¹cm⁻¹) | `"input-extinction-coeff"` | `123.0` | `1.0` / `0` |
| Molecular weight (g/mol) | `"input-molecular-weight"` | `633.698` | `0.001` / `0` |
| Solvent ratio | `"input-solvent-ratio"` | `"ACN:DMSO 306:1"` | — |
| Jet diameter (µm) | `"input-jet-diameter"` | `5.0` | `0.1` / `0` |
| Reservoir volume (mL) | `"input-reservoir-volume"` | `35.0` | `0.1` / `0` |
| Target absorbance (OD) | `"input-target-absorbance"` | `0.025` | `0.001` / `0` |

#### Results card (`dbc.Card`)

Displays the three `ConcentrationResult` fields. Use `dbc.ListGroup` or a simple table.

| Label | Component ID | Units |
|-------|-------------|-------|
| Transmission | `"result-transmission"` | — |
| Concentration | `"result-concentration-mM"` | mM |
| Mass | `"result-mass-mg"` | mg |

#### Plot

| Component | ID |
|-----------|-----|
| `dcc.Graph` | `"plot-od-vs-concentration"` |

---

### Tab 2 — Laser Fluence

#### Input panel (`dbc.Card`)

SampleConfig fields and `target_absorbance` are **not shown** in Tab 2 inputs — they come
from `dcc.Store`. The Tab 2 input panel only contains the fluence-specific parameters.

| Label | Component ID | Default value | Step / min |
|-------|-------------|---------------|------------|
| Wavelength (nm) | `"input-wavelength"` | `393.0` | `1.0` / `0` |
| Spot size vertical (µm FWHM) | `"input-spot-v"` | `240.0` | `1.0` / `0` |
| Spot size horizontal (µm FWHM) | `"input-spot-h"` | `100.0` | `1.0` / `0` |
| Rep rate (Hz) | `"input-rep-rate"` | `33000.0` | `1.0` / `0` |
| Target ⟨fexc⟩ | `"input-target-fexc"` | `0.24` | `0.01` / `0` |
| Pulse duration (fs) | `"input-pulse-duration-fs"` | `50.0` | `1.0` / `0` |
| fexc plot max | `"input-fexc-max"` | `2.0` | `0.1` / `0` |

**Important:** Pulse duration is displayed and stored in **femtoseconds** in the UI
(`input-pulse-duration-fs`) for readability. The callback must convert to seconds before
calling `calculate_fluence`: `pulse_duration_s = value * 1e-15`.

**`input-fexc-max`** controls the y-axis upper limit of `plot_pulse_energy_vs_fexc` and
the sweep range of both Tab 2 plots. Label it: "fexc plot max".

#### Results card

| Label | Component ID | Units |
|-------|-------------|-------|
| Pulse energy | `"result-pulse-energy-uJ"` | µJ |
| Avg power | `"result-avg-power-mW"` | mW |
| Avg power | `"result-avg-power-uW"` | µW |
| Fluence | `"result-fluence-mJ-cm2"` | mJ/cm² |
| Photons/pulse | `"result-n-photons"` | — |
| fexc front | `"result-fexc-front"` | — |
| fexc back | `"result-fexc-back"` | — |
| Peak intensity | `"result-peak-intensity"` | W/cm² |
| Pulse duration | `"result-pulse-duration"` | s |

Also display (read-only, sourced from store):
- `target_absorbance` in use (labelled "Absorbance (from Tab 1)")
- `sample_name` in use

#### Plots (2×2 grid using `dbc.Row` / `dbc.Col`)

| Position | Component ID | Function |
|----------|-------------|----------|
| Top-left | `"plot-fexc-vs-depth"` | `plot_fexc_vs_depth()` |
| Top-right | `"plot-pulse-energy-vs-fexc"` | `plot_pulse_energy_vs_fexc()` |
| Bottom-left | `"plot-fluence-vs-pulse-energy"` | `plot_fluence_vs_pulse_energy()` |
| Bottom-right | `"plot-od-vs-concentration-tab2"` | `plot_od_vs_concentration()` mirrored from Tab 1 for reference |

---

## 9. Callbacks

### Callback 1 — Tab 1 calculation + shared state update

**Trigger:** Any Tab 1 input changes (`Input` on all 7 Tab 1 input component IDs).

**Outputs:**
- `"result-transmission"` → `children`
- `"result-concentration-mM"` → `children`
- `"result-mass-mg"` → `children`
- `"plot-od-vs-concentration"` → `figure`
- `"shared-state"` → `data`

**Logic:**

```python
config = SampleConfig(
    sample_name=sample_name,
    extinction_coeff=extinction_coeff,
    molecular_weight=molecular_weight,
    solvent_ratio=solvent_ratio,
)
result = calculate_concentration(config, jet_diameter_um, reservoir_volume_mL, target_absorbance)
fig = plot_od_vs_concentration(config, result, target_absorbance, jet_diameter_um)
shared = {
    "sample_name": sample_name,
    "extinction_coeff": extinction_coeff,
    "molecular_weight": molecular_weight,
    "solvent_ratio": solvent_ratio,
    "target_absorbance": target_absorbance,
}
return f"{result.transmission:.6f}", f"{result.concentration_mM:.3f}", f"{result.mass_mg:.2f}", fig, shared
```

Use `dash.no_update` for any output if any required input is `None`.

---

### Callback 2 — Tab 2 calculation

**Trigger:** Any Tab 2 input changes + `"shared-state"` data change.

**Inputs:** All 7 Tab 2 input component IDs + `"shared-state"` (as `State` or `Input`
depending on whether Tab 2 should auto-update when Tab 1 changes — **use `Input`** so it
updates automatically).

**Outputs:**
- All 9 Tab 2 result component IDs → `children`
- `"plot-fexc-vs-depth"` → `figure`
- `"plot-pulse-energy-vs-fexc"` → `figure`
- `"plot-fluence-vs-pulse-energy"` → `figure`
- `"plot-od-vs-concentration-tab2"` → `figure`

**Logic:**

```python
# Reconstruct config and inputs from store + Tab 2 inputs
config = SampleConfig(
    sample_name=shared["sample_name"],
    extinction_coeff=shared["extinction_coeff"],
    molecular_weight=shared["molecular_weight"],
    solvent_ratio=shared["solvent_ratio"],
)
pulse_duration_s = pulse_duration_fs * 1e-15
result = calculate_fluence(
    config,
    target_absorbance=shared["target_absorbance"],
    wavelength_nm=wavelength_nm,
    spot_size_v_um=spot_v,
    spot_size_h_um=spot_h,
    rep_rate_Hz=rep_rate,
    target_fexc=target_fexc,
    pulse_duration_s=pulse_duration_s,
)
# Generate all four plots, return all outputs
```

---

### Callback 3 — Load config

**Trigger:** `"load-config-btn"` click.

**State:** `"config-dropdown"` value (the filepath string).

**Outputs:** All 13 input component IDs (Tab 1 + Tab 2 inputs) → `value`.

**Logic:**

```python
data = load_config(filepath)
return (
    data["sample_name"],
    data["extinction_coeff"],
    data["molecular_weight"],
    data["solvent_ratio"],
    data["jet_diameter_um"],
    data["reservoir_volume_mL"],
    data["target_absorbance"],
    data["wavelength_nm"],
    data["spot_size_v_um"],
    data["spot_size_h_um"],
    data["rep_rate_Hz"],
    data["target_fexc"],
    data["pulse_duration_s"] * 1e15,    # convert s → fs for display
)
```

---

### Callback 4 — Save: overwrite check

**Trigger:** `"save-config-btn"` click.

**State:** `"save-name-input"` value + all 13 input component values.

**Outputs:**
- `"overwrite-modal"` → `is_open`
- `"overwrite-modal-body"` → `children`

**Logic:**

```python
filename = re.sub(r'[^\w]+', '_', name.strip().lower()) + '.json'
filepath = CONFIGS_DIR / filename
if filepath.exists():
    return True, f"A config named '{name}' already exists. Overwrite it?"
else:
    # No collision — save immediately, do not open modal
    _do_save(name, all_inputs)
    return False, ""
```

The `_do_save` helper assembles the data dict from the 13 input values and calls
`save_config(CONFIGS_DIR, name, data)`.

---

### Callback 5 — Save: confirm overwrite

**Trigger:** `"overwrite-confirm-btn"` click.

**State:** `"save-name-input"` value + all 13 input values.

**Outputs:**
- `"overwrite-modal"` → `is_open` (set to `False` to close)
- `"config-dropdown"` → `options` (refresh list after save)

**Logic:**

```python
_do_save(name, all_inputs)
options = list_configs(CONFIGS_DIR)
return False, options
```

---

### Callback 6 — Cancel overwrite

**Trigger:** `"overwrite-cancel-btn"` click.

**Outputs:** `"overwrite-modal"` → `is_open` (set to `False`).

---

### Callback 7 — Refresh config dropdown after save (no-overwrite path)

After a successful save with no collision (handled inside Callback 4), the dropdown options
must also be refreshed. Use an `Output` on `"config-dropdown"` → `options` from Callback 4
as well, returning `list_configs(CONFIGS_DIR)` after the save.

**Note:** If managing two callbacks updating the same Output is complex, consider using a
hidden `dcc.Store(id="save-trigger")` that increments on each save, and a separate callback
that reads it and refreshes the dropdown. Either approach is acceptable.

---

## 10. Error Handling

All callbacks that call calculation functions should wrap the call in a `try/except` block.
On any error, return `"—"` for all result text outputs and an empty figure with an error
annotation for all plot outputs. Do not let the app crash.

```python
try:
    result = calculate_fluence(...)
except Exception as e:
    # Return dash.no_update or placeholder values
    ...
```

Also guard against `None` inputs (fields that have been cleared by the user). Check all
required numeric inputs are not `None` before computing; return `dash.no_update` if any are.

---

## 11. Number Formatting in Results

Format result fields consistently:

| Field | Format |
|-------|--------|
| `transmission` | `f"{v:.6f}"` |
| `concentration_mM` | `f"{v:.3f} mM"` |
| `mass_mg` | `f"{v:.2f} mg"` |
| `pulse_energy_uJ` | `f"{v:.4f} µJ"` |
| `avg_power_mW` | `f"{v:.3f} mW"` |
| `avg_power_uW` | `f"{v:.1f} µW"` |
| `fluence_mJ_cm2` | `f"{v:.3f} mJ/cm²"` |
| `n_photons_per_pulse` | `f"{v:.3e}"` |
| `fexc_front` | `f"{v:.5f}"` |
| `fexc_back` | `f"{v:.5f}"` |
| `peak_intensity_W_cm2` | `f"{v:.3e} W/cm²"` |
| `pulse_duration_s` | `f"{v * 1e15:.1f} fs"` |

---

## 12. Final Directory Structure After Implementation

```
Excitation_Fraction/
├── SAMPLE & LASER CALCULATIONS.xlsx
├── SAMPLE_LASER_CALCULATIONS_README.md
├── IMPLEMENTATION_PLAN.md
├── SESSION_REPORT.md
├── DASH_IMPLEMENTATION_PLAN.md         # This file
├── configs/
│   └── default.json                    # Factory default config
└── src/
    ├── __init__.py
    ├── models.py
    ├── calculations.py
    ├── config_io.py                    # NEW
    ├── plots.py                        # NEW
    ├── app.py                          # NEW
    └── tests/
        ├── __init__.py
        └── test_calculations.py
```

---

## 13. Implementation Order

Implement in this order to allow incremental testing:

1. **`configs/default.json`** — no dependencies, verify JSON is valid
2. **`src/config_io.py`** — pure Python, test manually in a REPL
3. **`src/plots.py`** — pure Plotly, test by calling functions in a Jupyter notebook
   or script and calling `.show()` on the returned figures
4. **`src/app.py`** — depends on everything above; build layout first with static
   placeholder outputs, then wire up callbacks one at a time in the order listed in
   Section 9

---

## 14. Testing the Finished App

```bash
cd /sdf/home/b/bpoult/Excitation_Fraction
python -m pytest src/tests/test_calculations.py -v   # backend still passes
python -m src.app                                      # start the app
# Open browser at http://127.0.0.1:8050
```

Manual checks to perform in the browser:

1. Default values are pre-populated correctly (match Section 2 default table).
2. Changing Tab 1 inputs updates results card and plot immediately.
3. Tab 2 `target_absorbance` display updates when Tab 1 absorbance input changes.
4. Changing Tab 2 inputs updates all four plots and results card.
5. Changing `fexc_max` input updates the y-axis range of `plot-pulse-energy-vs-fexc`.
6. Saving a new config writes a JSON file to `configs/` and refreshes the dropdown.
7. Saving a config with a duplicate name opens the overwrite modal.
8. Clicking "Overwrite" in the modal writes the file and closes the modal.
9. Clicking "Cancel" closes the modal without writing.
10. Selecting a config from the dropdown and clicking "Load" populates all input fields.
