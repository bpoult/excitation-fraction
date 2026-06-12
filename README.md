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
    sample_name="[Ru(bpy)3][Cl]3",
    extinction_coeff=10800,
    molecular_weight=640.53,
    solvent_ratio="Water",
)

conc = calculate_concentration(config, jet_diameter_um=100.0, reservoir_volume_mL=35.0, target_absorbance=0.3)
flux = calculate_fluence(config, target_absorbance=0.3, wavelength_nm=400.0,
                         spot_size_v_um=100.0, spot_size_h_um=100.0,
                         rep_rate_Hz=120, target_fexc=0.25)
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