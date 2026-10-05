# excitation-fraction

Python calculation backend and Dash web GUI for experimental design in ultrafast transient absorption spectroscopy on a liquid microjet.

Given a target absorbance and excitation fraction, computes the required sample concentration and laser pulse parameters.

## Windows app (no Python needed)

1. Download `ExcitationFraction-win64.zip` from the [latest release](https://github.com/bpoult/excitation-fraction/releases/latest).
2. Extract it anywhere (e.g. your Desktop) and run `ExcitationFraction\ExcitationFraction.exe`.
   Keep the exe inside its folder — it needs the `_internal\` folder next to it.
3. The first time, Windows SmartScreen may say "Windows protected your PC" because the exe is not code-signed. Click **More info → Run anyway**.

Notes:
- Requires the Microsoft Edge WebView2 runtime, which is built into Windows 11 and recent Windows 10. If the app reports it is missing, install the [Evergreen bootstrapper](https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section).
- Saved configurations are written to `ExcitationFraction\configs\*.json`. Copy or share these files freely; `default.json` is recreated if deleted.
- If the app fails to start, see `ExcitationFraction\excitation_fraction.log`.
- The app is fully offline — no internet connection is required.

## Running from source

Python 3.12+

```bash
pip install -r requirements.txt
```

### Run the web app (development, hot reload)

```bash
cd excitation-fraction
python -m src.app
# Open http://127.0.0.1:8050
```

### Run the desktop shell without building

```bash
pip install -r requirements-build.txt
python launcher.py
```

### Run the tests

```bash
python -m pytest src/tests/test_calculations.py -v
```

## Building the Windows app

From a shell with the project environment active (`pip install -r requirements-build.txt` once):

```bat
build.bat
```

This runs PyInstaller with `ExcitationFraction.spec` and produces `dist\ExcitationFraction-win64.zip`
(a one-folder build: `ExcitationFraction.exe` + `_internal\`). Attach the zip to a GitHub Release, e.g.

```bash
git tag v1.0.0 && git push --tags
gh release create v1.0.0 dist/ExcitationFraction-win64.zip --title "v1.0.0" --notes "..."
```

Do not commit the zip or `dist\` to the repository.

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
├── launcher.py                 # Desktop entry point (local server + native window)
├── ExcitationFraction.spec     # PyInstaller build spec
├── build.bat                   # Build + zip the Windows app
├── requirements.txt            # Runtime dependencies
├── requirements-build.txt      # + PyInstaller, pywebview, pytest
└── src/
    ├── assets/                 # Bundled Bootstrap Darkly theme (served offline)
    ├── models.py               # SampleConfig, ConcentrationResult, FluenceResult
    ├── calculations.py         # calculate_concentration(), calculate_fluence()
    ├── config_io.py            # Save / load / list JSON configurations
    ├── plots.py                # Plotly figure functions
    ├── app.py                  # Dash web application
    └── tests/
        └── test_calculations.py
```