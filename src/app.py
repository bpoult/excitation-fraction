"""
app.py
------
Dash web application for the Sample & Laser Calculations GUI.

Run with:
    cd /sdf/home/b/bpoult/Excitation_Fraction
    python -m src.app

Layout
------
- Top bar: config dropdown (load) + name input / save button
- Tab 1 — Sample Concentration: inputs → results card + OD vs. concentration plot
- Tab 2 — Laser Fluence: inputs → results card + 2x2 plot grid

Shared state (SampleConfig fields + target_absorbance) flows from Tab 1 to Tab 2
via a dcc.Store component, eliminating the manual-copy problem from the spreadsheet.
"""

import pathlib

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, callback, no_update

from .models import SampleConfig
from .calculations import calculate_concentration, calculate_fluence
from .plots import (
    plot_od_vs_concentration,
    plot_fexc_vs_depth,
    plot_pulse_energy_vs_fexc,
    plot_fluence_vs_pulse_energy,
)
from .config_io import list_configs, load_config, save_config, config_exists, CONFIGS_DIR

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="Sample & Laser Calculations",
)

# ---------------------------------------------------------------------------
# Default input values (match spreadsheet defaults)
# ---------------------------------------------------------------------------

DEFAULTS = {
    "sample_name": "[Ru(bpy)3][Cl]3",
    "extinction_coeff": 10800,
    "molecular_weight": 640.53,
    "solvent_ratio": "Water",
    "jet_diameter_um": 100.0,
    "reservoir_volume_mL": 35.0,
    "target_absorbance": 0.3,
    "wavelength_nm": 400.0,
    "spot_size_v_um": 100.0,
    "spot_size_h_um": 100.0,
    "rep_rate_Hz": 120.0,
    "target_fexc": 0.25,
    "pulse_duration_fs": 50.0,   # displayed in fs; converted to s in callbacks
    "fexc_max": 2.0,
}

# ---------------------------------------------------------------------------
# Helper: labelled input row
# ---------------------------------------------------------------------------

def _input_row(label: str, input_id: str, value, step=None, min_val=0,
               input_type="number", placeholder=None):
    """Return a dbc.Row containing a label and a dbc.Input."""
    kwargs = dict(
        id=input_id,
        type=input_type,
        value=value,
        debounce=True,
        className="mb-1",
        style={"backgroundColor": "#2b2b2b", "color": "#f0f0f0",
               "border": "1px solid #555"},
    )
    if input_type == "number":
        kwargs["step"] = step
        kwargs["min"] = min_val
    if placeholder:
        kwargs["placeholder"] = placeholder

    return dbc.Row([
        dbc.Col(html.Label(label, className="text-light small"), width=6),
        dbc.Col(dbc.Input(**kwargs), width=6),
    ], className="mb-1 align-items-center")


# ---------------------------------------------------------------------------
# Helper: result display row
# ---------------------------------------------------------------------------

def _result_row(label: str, result_id: str, value: str = "—"):
    return dbc.Row([
        dbc.Col(html.Span(label, className="text-secondary small"), width=6),
        dbc.Col(html.Span(value, id=result_id,
                          className="text-light small fw-bold"), width=6),
    ], className="mb-1")


# ---------------------------------------------------------------------------
# Layout helpers: Tab 1 and Tab 2
# ---------------------------------------------------------------------------

def _tab1_layout():
    return dbc.Container([
        dbc.Row([
            # Left: inputs
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Sample Configuration", className="fw-bold"),
                    dbc.CardBody([
                        _input_row("Sample name", "input-sample-name",
                                   DEFAULTS["sample_name"], input_type="text"),
                        _input_row("Extinction coeff (M⁻¹cm⁻¹)", "input-extinction-coeff",
                                   DEFAULTS["extinction_coeff"], step=1.0),
                        _input_row("Molecular weight (g/mol)", "input-molecular-weight",
                                   DEFAULTS["molecular_weight"], step=0.001),
                        _input_row("Solvent ratio", "input-solvent-ratio",
                                   DEFAULTS["solvent_ratio"], input_type="text"),
                    ]),
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardHeader("Experiment Parameters", className="fw-bold"),
                    dbc.CardBody([
                        _input_row("Jet diameter (µm)", "input-jet-diameter",
                                   DEFAULTS["jet_diameter_um"], step=0.1),
                        _input_row("Reservoir volume (mL)", "input-reservoir-volume",
                                   DEFAULTS["reservoir_volume_mL"], step=0.1),
                        _input_row("Target absorbance (OD)", "input-target-absorbance",
                                   DEFAULTS["target_absorbance"], step=0.001),
                    ]),
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardHeader("Results", className="fw-bold"),
                    dbc.CardBody([
                        _result_row("Transmission", "result-transmission"),
                        _result_row("Concentration", "result-concentration-mM"),
                        _result_row("Mass", "result-mass-mg"),
                    ]),
                ]),
            ], width=4),
            # Right: plot
            dbc.Col([
                dcc.Graph(id="plot-od-vs-concentration", style={"height": "500px"}),
            ], width=8),
        ]),
    ], fluid=True, className="mt-3")


def _tab2_layout():
    return dbc.Container([
        dbc.Row([
            # Left: inputs + results
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Laser Parameters", className="fw-bold"),
                    dbc.CardBody([
                        _input_row("Wavelength (nm)", "input-wavelength",
                                   DEFAULTS["wavelength_nm"], step=1.0),
                        _input_row("Spot size vertical (µm FWHM)", "input-spot-v",
                                   DEFAULTS["spot_size_v_um"], step=1.0),
                        _input_row("Spot size horizontal (µm FWHM)", "input-spot-h",
                                   DEFAULTS["spot_size_h_um"], step=1.0),
                        _input_row("Rep rate (Hz)", "input-rep-rate",
                                   DEFAULTS["rep_rate_Hz"], step=1.0),
                        _input_row("Target ⟨fexc⟩", "input-target-fexc",
                                   DEFAULTS["target_fexc"], step=0.01),
                        _input_row("Pulse duration (fs)", "input-pulse-duration-fs",
                                   DEFAULTS["pulse_duration_fs"], step=1.0),
                        _input_row("fexc plot max", "input-fexc-max",
                                   DEFAULTS["fexc_max"], step=0.1),
                    ]),
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardHeader("Shared from Tab 1", className="fw-bold"),
                    dbc.CardBody([
                        _result_row("Sample", "display-sample-name"),
                        _result_row("Absorbance (OD)", "display-target-absorbance"),
                    ]),
                ], className="mb-3"),
                dbc.Card([
                    dbc.CardHeader("Results", className="fw-bold"),
                    dbc.CardBody([
                        _result_row("Pulse energy", "result-pulse-energy-uJ"),
                        _result_row("Avg power", "result-avg-power-mW"),
                        _result_row("Avg power", "result-avg-power-uW"),
                        _result_row("Fluence", "result-fluence-mJ-cm2"),
                        _result_row("Photons / pulse", "result-n-photons"),
                        _result_row("fexc front", "result-fexc-front"),
                        _result_row("fexc back", "result-fexc-back"),
                        _result_row("Peak intensity", "result-peak-intensity"),
                        _result_row("Pulse duration", "result-pulse-duration"),
                    ]),
                ]),
            ], width=4),
            # Right: 2×2 plot grid
            # (1,1) pulse energy vs fexc  |  (1,2) fluence vs pulse energy
            # (2,1) OD vs concentration   |  (2,2) fexc vs depth
            dbc.Col([
                dbc.Row([
                    dbc.Col(dcc.Graph(id="plot-pulse-energy-vs-fexc",
                                     style={"height": "380px"}), width=6),
                    dbc.Col(dcc.Graph(id="plot-fluence-vs-pulse-energy",
                                     style={"height": "380px"}), width=6),
                ], className="mb-2"),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="plot-od-vs-concentration-tab2",
                                     style={"height": "380px"}), width=6),
                    dbc.Col(dcc.Graph(id="plot-fexc-vs-depth",
                                     style={"height": "380px"}), width=6),
                ]),
            ], width=8),
        ]),
    ], fluid=True, className="mt-3")


# ---------------------------------------------------------------------------
# Overwrite confirmation modal
# ---------------------------------------------------------------------------

_overwrite_modal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Config already exists")),
    dbc.ModalBody(id="overwrite-modal-body"),
    dbc.ModalFooter([
        dbc.Button("Overwrite", id="overwrite-confirm-btn",
                   color="danger", className="me-2"),
        dbc.Button("Cancel", id="overwrite-cancel-btn", color="secondary"),
    ]),
], id="overwrite-modal", is_open=False)


# ---------------------------------------------------------------------------
# Top bar
# ---------------------------------------------------------------------------

_top_bar = dbc.Card([
    dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.Label("Load configuration", className="text-light small mb-1"),
                dbc.Row([
                    dbc.Col(
                        dcc.Dropdown(
                            id="config-dropdown",
                            options=list_configs(CONFIGS_DIR),
                            placeholder="Select a saved config…",
                            clearable=False,
                            style={"backgroundColor": "#2b2b2b", "color": "#111"},
                        ),
                        width=9,
                    ),
                    dbc.Col(
                        dbc.Button("Load", id="load-config-btn",
                                   color="primary", size="sm", className="w-100"),
                        width=3,
                    ),
                ], className="g-2"),
            ], width=6),
            dbc.Col([
                html.Label("Save configuration", className="text-light small mb-1"),
                dbc.Row([
                    dbc.Col(
                        dbc.Input(
                            id="save-name-input",
                            placeholder="Config name…",
                            type="text",
                            size="sm",
                            style={"backgroundColor": "#2b2b2b", "color": "#f0f0f0",
                                   "border": "1px solid #555"},
                        ),
                        width=9,
                    ),
                    dbc.Col(
                        dbc.Button("Save", id="save-config-btn",
                                   color="success", size="sm", className="w-100"),
                        width=3,
                    ),
                ], className="g-2"),
            ], width=6),
        ]),
        dbc.Row([
            dbc.Col(
                html.Div(id="save-status", className="text-success small mt-1"),
            ),
        ]),
    ]),
], className="mb-3")


# ---------------------------------------------------------------------------
# Full app layout
# ---------------------------------------------------------------------------

app.layout = dbc.Container([
    dcc.Store(id="shared-state", storage_type="memory"),
    # Stores all current inputs for use by the save callbacks
    dcc.Store(id="all-inputs-store", storage_type="memory"),

    html.H4("Sample & Laser Calculations",
            className="text-light text-center mt-3 mb-3"),

    _top_bar,
    _overwrite_modal,

    dbc.Tabs([
        dbc.Tab(_tab1_layout(), label="Sample Concentration",
                tab_id="tab-1", activeTabClassName="fw-bold"),
        dbc.Tab(_tab2_layout(), label="Laser Fluence",
                tab_id="tab-2", activeTabClassName="fw-bold"),
    ], id="main-tabs", active_tab="tab-1"),

], fluid=True)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# IDs of all 13 input components (Tab 1 + Tab 2), in load-config return order
_ALL_INPUT_IDS = [
    "input-sample-name",
    "input-extinction-coeff",
    "input-molecular-weight",
    "input-solvent-ratio",
    "input-jet-diameter",
    "input-reservoir-volume",
    "input-target-absorbance",
    "input-wavelength",
    "input-spot-v",
    "input-spot-h",
    "input-rep-rate",
    "input-target-fexc",
    "input-pulse-duration-fs",
]

# Map from component ID to config dict key
_ID_TO_KEY = {
    "input-sample-name":        "sample_name",
    "input-extinction-coeff":   "extinction_coeff",
    "input-molecular-weight":   "molecular_weight",
    "input-solvent-ratio":      "solvent_ratio",
    "input-jet-diameter":       "jet_diameter_um",
    "input-reservoir-volume":   "reservoir_volume_mL",
    "input-target-absorbance":  "target_absorbance",
    "input-wavelength":         "wavelength_nm",
    "input-spot-v":             "spot_size_v_um",
    "input-spot-h":             "spot_size_h_um",
    "input-rep-rate":           "rep_rate_Hz",
    "input-target-fexc":        "target_fexc",
    "input-pulse-duration-fs":  "pulse_duration_fs",
}


def _build_data_dict(values: list) -> dict:
    """Zip _ALL_INPUT_IDS with values into a data dict (keys are config keys)."""
    return {_ID_TO_KEY[iid]: v for iid, v in zip(_ALL_INPUT_IDS, values)}


def _empty_fig(message: str = "No data"):
    """Return a blank dark figure with a centred annotation."""
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        annotations=[dict(text=message, x=0.5, y=0.5, xref="paper",
                          yref="paper", showarrow=False,
                          font=dict(size=14, color="grey"))],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


# ---------------------------------------------------------------------------
# Callback 1 — Tab 1: calculate concentration + update shared state
# ---------------------------------------------------------------------------

@app.callback(
    Output("result-transmission", "children"),
    Output("result-concentration-mM", "children"),
    Output("result-mass-mg", "children"),
    Output("plot-od-vs-concentration", "figure"),
    Output("shared-state", "data"),
    Output("all-inputs-store", "data"),
    Input("input-sample-name", "value"),
    Input("input-extinction-coeff", "value"),
    Input("input-molecular-weight", "value"),
    Input("input-solvent-ratio", "value"),
    Input("input-jet-diameter", "value"),
    Input("input-reservoir-volume", "value"),
    Input("input-target-absorbance", "value"),
    # Tab 2 inputs — needed to keep all-inputs-store current
    Input("input-wavelength", "value"),
    Input("input-spot-v", "value"),
    Input("input-spot-h", "value"),
    Input("input-rep-rate", "value"),
    Input("input-target-fexc", "value"),
    Input("input-pulse-duration-fs", "value"),
)
def update_tab1(
    sample_name, extinction_coeff, molecular_weight, solvent_ratio,
    jet_diameter_um, reservoir_volume_mL, target_absorbance,
    wavelength_nm, spot_v, spot_h, rep_rate, target_fexc, pulse_duration_fs,
):
    # Guard against missing inputs
    required_numeric = [extinction_coeff, molecular_weight, jet_diameter_um,
                        reservoir_volume_mL, target_absorbance]
    if any(v is None for v in required_numeric) or not sample_name:
        store = no_update
        all_store = no_update
        return "—", "—", "—", _empty_fig("Enter all inputs"), store, all_store

    try:
        config = SampleConfig(
            sample_name=str(sample_name),
            extinction_coeff=float(extinction_coeff),
            molecular_weight=float(molecular_weight),
            solvent_ratio=str(solvent_ratio) if solvent_ratio else "",
        )
        result = calculate_concentration(
            config,
            jet_diameter_um=float(jet_diameter_um),
            reservoir_volume_mL=float(reservoir_volume_mL),
            target_absorbance=float(target_absorbance),
        )
        fig = plot_od_vs_concentration(config, result,
                                       float(target_absorbance),
                                       float(jet_diameter_um))
    except Exception as exc:
        return f"Error: {exc}", "—", "—", _empty_fig(f"Error: {exc}"), no_update, no_update

    shared = {
        "sample_name": str(sample_name),
        "extinction_coeff": float(extinction_coeff),
        "molecular_weight": float(molecular_weight),
        "solvent_ratio": str(solvent_ratio) if solvent_ratio else "",
        "target_absorbance": float(target_absorbance),
        "jet_diameter_um": float(jet_diameter_um),
        "reservoir_volume_mL": float(reservoir_volume_mL),
    }

    # all-inputs-store for save callbacks
    all_inputs = {
        "sample_name": str(sample_name),
        "extinction_coeff": float(extinction_coeff),
        "molecular_weight": float(molecular_weight),
        "solvent_ratio": str(solvent_ratio) if solvent_ratio else "",
        "jet_diameter_um": float(jet_diameter_um),
        "reservoir_volume_mL": float(reservoir_volume_mL),
        "target_absorbance": float(target_absorbance),
        "wavelength_nm": float(wavelength_nm) if wavelength_nm is not None else DEFAULTS["wavelength_nm"],
        "spot_size_v_um": float(spot_v) if spot_v is not None else DEFAULTS["spot_size_v_um"],
        "spot_size_h_um": float(spot_h) if spot_h is not None else DEFAULTS["spot_size_h_um"],
        "rep_rate_Hz": float(rep_rate) if rep_rate is not None else DEFAULTS["rep_rate_Hz"],
        "target_fexc": float(target_fexc) if target_fexc is not None else DEFAULTS["target_fexc"],
        "pulse_duration_s": float(pulse_duration_fs) * 1e-15 if pulse_duration_fs is not None else 50e-15,
    }

    return (
        f"{result.transmission:.6f}",
        f"{result.concentration_mM:.3f} mM",
        f"{result.mass_mg:.2f} mg",
        fig,
        shared,
        all_inputs,
    )


# ---------------------------------------------------------------------------
# Callback 2 — Tab 2: calculate fluence + generate all four plots
# ---------------------------------------------------------------------------

@app.callback(
    Output("result-pulse-energy-uJ", "children"),
    Output("result-avg-power-mW", "children"),
    Output("result-avg-power-uW", "children"),
    Output("result-fluence-mJ-cm2", "children"),
    Output("result-n-photons", "children"),
    Output("result-fexc-front", "children"),
    Output("result-fexc-back", "children"),
    Output("result-peak-intensity", "children"),
    Output("result-pulse-duration", "children"),
    Output("display-sample-name", "children"),
    Output("display-target-absorbance", "children"),
    Output("plot-fexc-vs-depth", "figure"),
    Output("plot-pulse-energy-vs-fexc", "figure"),
    Output("plot-fluence-vs-pulse-energy", "figure"),
    Output("plot-od-vs-concentration-tab2", "figure"),
    Input("shared-state", "data"),
    Input("input-wavelength", "value"),
    Input("input-spot-v", "value"),
    Input("input-spot-h", "value"),
    Input("input-rep-rate", "value"),
    Input("input-target-fexc", "value"),
    Input("input-pulse-duration-fs", "value"),
    Input("input-fexc-max", "value"),
)
def update_tab2(
    shared, wavelength_nm, spot_v, spot_h, rep_rate,
    target_fexc, pulse_duration_fs, fexc_max,
):
    _blank = _empty_fig("Waiting for inputs…")
    _blanks = (_blank, _blank, _blank, _blank)

    if shared is None:
        return ("—",) * 9 + ("—", "—") + _blanks

    required = [wavelength_nm, spot_v, spot_h, rep_rate,
                target_fexc, pulse_duration_fs, fexc_max]
    if any(v is None for v in required):
        return ("—",) * 9 + (
            shared.get("sample_name", "—"),
            f"{shared.get('target_absorbance', '—')}",
        ) + _blanks

    try:
        config = SampleConfig(
            sample_name=shared["sample_name"],
            extinction_coeff=shared["extinction_coeff"],
            molecular_weight=shared["molecular_weight"],
            solvent_ratio=shared["solvent_ratio"],
        )
        target_absorbance = shared["target_absorbance"]
        pulse_duration_s = float(pulse_duration_fs) * 1e-15

        result = calculate_fluence(
            config,
            target_absorbance=target_absorbance,
            wavelength_nm=float(wavelength_nm),
            spot_size_v_um=float(spot_v),
            spot_size_h_um=float(spot_h),
            rep_rate_Hz=float(rep_rate),
            target_fexc=float(target_fexc),
            pulse_duration_s=pulse_duration_s,
        )

        # Mirrored concentration result for Tab2's OD plot
        from .calculations import calculate_concentration as _cc
        _jet_d = float(shared.get("jet_diameter_um", 5.0))
        _res_v = float(shared.get("reservoir_volume_mL", 35.0))
        conc_result = _cc(
            config,
            jet_diameter_um=_jet_d,
            reservoir_volume_mL=_res_v,
            target_absorbance=target_absorbance,
        )

        fig_depth = plot_fexc_vs_depth(
            config, result,
            _jet_d,
            target_absorbance,
        )
        fig_fexc = plot_pulse_energy_vs_fexc(
            config, target_absorbance, float(wavelength_nm),
            float(spot_v), float(spot_h), float(rep_rate), pulse_duration_s,
            float(target_fexc), result, fexc_max=float(fexc_max),
        )
        fig_fluence = plot_fluence_vs_pulse_energy(
            config, target_absorbance, float(wavelength_nm),
            float(spot_v), float(spot_h), float(rep_rate), pulse_duration_s,
            float(target_fexc), result, fexc_max=float(fexc_max),
        )
        fig_od = plot_od_vs_concentration(
            config, conc_result, target_absorbance, _jet_d,
        )

    except Exception as exc:
        err = f"Error: {exc}"
        return (err,) * 9 + (shared.get("sample_name", "—"),
                              str(shared.get("target_absorbance", "—"))) + (
            _empty_fig(err), _empty_fig(err), _empty_fig(err), _empty_fig(err),
        )

    return (
        f"{result.pulse_energy_uJ:.4f} µJ",
        f"{result.avg_power_mW:.3f} mW",
        f"{result.avg_power_uW:.1f} µW",
        f"{result.fluence_mJ_cm2:.3f} mJ/cm²",
        f"{result.n_photons_per_pulse:.3e}",
        f"{result.fexc_front:.5f}",
        f"{result.fexc_back:.5f}",
        f"{result.peak_intensity_W_cm2:.3e} W/cm²",
        f"{result.pulse_duration_s * 1e15:.1f} fs",
        shared["sample_name"],
        f"{target_absorbance:.4f}",
        fig_depth,
        fig_fexc,
        fig_fluence,
        fig_od,
    )


# ---------------------------------------------------------------------------
# Callback 3 — Load config: populate all input fields
# ---------------------------------------------------------------------------

@app.callback(
    Output("input-sample-name", "value"),
    Output("input-extinction-coeff", "value"),
    Output("input-molecular-weight", "value"),
    Output("input-solvent-ratio", "value"),
    Output("input-jet-diameter", "value"),
    Output("input-reservoir-volume", "value"),
    Output("input-target-absorbance", "value"),
    Output("input-wavelength", "value"),
    Output("input-spot-v", "value"),
    Output("input-spot-h", "value"),
    Output("input-rep-rate", "value"),
    Output("input-target-fexc", "value"),
    Output("input-pulse-duration-fs", "value"),
    Input("load-config-btn", "n_clicks"),
    State("config-dropdown", "value"),
    prevent_initial_call=True,
)
def load_config_callback(n_clicks, filepath):
    if not filepath:
        return (no_update,) * 13
    try:
        data = load_config(filepath)
    except Exception:
        return (no_update,) * 13

    return (
        data.get("sample_name", DEFAULTS["sample_name"]),
        data.get("extinction_coeff", DEFAULTS["extinction_coeff"]),
        data.get("molecular_weight", DEFAULTS["molecular_weight"]),
        data.get("solvent_ratio", DEFAULTS["solvent_ratio"]),
        data.get("jet_diameter_um", DEFAULTS["jet_diameter_um"]),
        data.get("reservoir_volume_mL", DEFAULTS["reservoir_volume_mL"]),
        data.get("target_absorbance", DEFAULTS["target_absorbance"]),
        data.get("wavelength_nm", DEFAULTS["wavelength_nm"]),
        data.get("spot_size_v_um", DEFAULTS["spot_size_v_um"]),
        data.get("spot_size_h_um", DEFAULTS["spot_size_h_um"]),
        data.get("rep_rate_Hz", DEFAULTS["rep_rate_Hz"]),
        data.get("target_fexc", DEFAULTS["target_fexc"]),
        data.get("pulse_duration_s", 50e-15) * 1e15,  # s → fs
    )


# ---------------------------------------------------------------------------
# Callback 4 — Save button: overwrite check or immediate save
# ---------------------------------------------------------------------------

@app.callback(
    Output("overwrite-modal", "is_open"),
    Output("overwrite-modal-body", "children"),
    Output("config-dropdown", "options", allow_duplicate=True),
    Output("save-status", "children"),
    Input("save-config-btn", "n_clicks"),
    State("save-name-input", "value"),
    State("all-inputs-store", "data"),
    prevent_initial_call=True,
)
def save_config_callback(n_clicks, name, all_inputs):
    if not name or not name.strip():
        return False, "", no_update, "Enter a config name first."
    if all_inputs is None:
        return False, "", no_update, "No inputs to save yet."

    if config_exists(CONFIGS_DIR, name):
        modal_body = (
            f"A config named \"{name}\" already exists. Overwrite it?"
        )
        return True, modal_body, no_update, ""

    # No collision — save immediately
    save_config(CONFIGS_DIR, name, dict(all_inputs))
    opts = list_configs(CONFIGS_DIR)
    return False, "", opts, f"Saved \"{name}\"."


# ---------------------------------------------------------------------------
# Callback 5 — Confirm overwrite
# ---------------------------------------------------------------------------

@app.callback(
    Output("overwrite-modal", "is_open", allow_duplicate=True),
    Output("config-dropdown", "options", allow_duplicate=True),
    Output("save-status", "children", allow_duplicate=True),
    Input("overwrite-confirm-btn", "n_clicks"),
    State("save-name-input", "value"),
    State("all-inputs-store", "data"),
    prevent_initial_call=True,
)
def overwrite_confirm(n_clicks, name, all_inputs):
    if not name or all_inputs is None:
        return False, no_update, ""
    save_config(CONFIGS_DIR, name, dict(all_inputs))
    opts = list_configs(CONFIGS_DIR)
    return False, opts, f"Overwritten \"{name}\"."


# ---------------------------------------------------------------------------
# Callback 6 — Cancel overwrite
# ---------------------------------------------------------------------------

@app.callback(
    Output("overwrite-modal", "is_open", allow_duplicate=True),
    Input("overwrite-cancel-btn", "n_clicks"),
    prevent_initial_call=True,
)
def overwrite_cancel(n_clicks):
    return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
