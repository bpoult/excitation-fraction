# excitation-fraction

Python calculation backend and Dash web GUI for experimental design in ultrafast transient absorption spectroscopy on a liquid microjet.

Given a target absorbance and excitation fraction, computes the required sample concentration and laser pulse parameters.

## Requirements

Python 3.12+

```bash
pip install numpy plotly dash dash-bootstrap-components
```

## Usage

### Run the web app

```bash
cd excitation-fraction
python -m src.app
# Open http://127.0.0.1:8050
```

### Run the tests

```bash
python -m pytest src/tests/test_calculations.py -v
```

### Use the functions directly

```python
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
```

## Structure

```
excitation-fraction/
├── configs/
│   └── default.json            # Factory default configuration
└── src/
    ├── models.py               # SampleConfig, ConcentrationResult, FluenceResult
    ├── calculations.py         # calculate_concentration(), calculate_fluence()
    ├── config_io.py            # Save / load / list JSON configurations
    ├── plots.py                # Plotly figure functions
    ├── app.py                  # Dash web application
    └── tests/
        └── test_calculations.py
```

## Documentation

- `SAMPLE_LASER_CALCULATIONS_README.md` — full description of the underlying spreadsheet formulas and physics
- `SESSION_REPORT.md` — implementation details, design decisions, and verified numerical results
- `DASH_IMPLEMENTATION_PLAN.md` — full specification for the GUI layer
