"""
plots.py
--------
Plotly figure-generating functions for the Sample & Laser Calculations Dash app.

Each function accepts calculation results / raw inputs and returns a
plotly.graph_objects.Figure. No Dash imports — pure Plotly.

Functions
---------
plot_od_vs_concentration(config, result, target_absorbance, jet_diameter_um)
plot_fexc_vs_depth(config, result, jet_diameter_um, target_absorbance)
plot_pulse_energy_vs_fexc(config, target_absorbance, wavelength_nm,
                           spot_size_v_um, spot_size_h_um, rep_rate_Hz,
                           pulse_duration_s, current_fexc, current_result,
                           fexc_max=2.0)
plot_fluence_vs_pulse_energy(config, target_absorbance, wavelength_nm,
                              spot_size_v_um, spot_size_h_um, rep_rate_Hz,
                              pulse_duration_s, current_fexc, current_result,
                              fexc_max=2.0)
"""

import numpy as np
import plotly.graph_objects as go

from .models import SampleConfig, ConcentrationResult, FluenceResult
from .calculations import calculate_fluence

# ---------------------------------------------------------------------------
# Shared visual constants
# ---------------------------------------------------------------------------

PLOT_TEMPLATE = "plotly_dark"
LINE_COLOR = "#636EFA"       # Plotly default blue — sweep line
MARKER_COLOR = "#EF553B"     # Red/orange — current operating point
MARKER_SIZE = 12
N_SWEEP = 300                # Number of points in sweep curves


def _base_figure(title: str, xaxis_title: str, yaxis_title: str) -> go.Figure:
    """Return a figure with shared layout settings applied."""
    fig = go.Figure()
    fig.update_layout(
        template=PLOT_TEMPLATE,
        title=dict(text=title, x=0.5, xanchor="center"),
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        margin=dict(l=60, r=30, t=60, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ---------------------------------------------------------------------------
# Plot 1 — OD vs. Concentration
# ---------------------------------------------------------------------------

def plot_od_vs_concentration(
    config: SampleConfig,
    result: ConcentrationResult,
    target_absorbance: float,
    jet_diameter_um: float,
) -> go.Figure:
    """
    Beer-Lambert curve: absorbance vs. concentration for the current jet
    geometry and sample.

    The sweep covers 0 to 3× the current operating concentration.
    The current operating point is shown as a highlighted dot.

    Parameters
    ----------
    config : SampleConfig
    result : ConcentrationResult
        Output of calculate_concentration() at the current inputs.
    target_absorbance : float
        Target OD (used for the operating point marker).
    jet_diameter_um : float
        Jet diameter / optical path length (µm).

    Returns
    -------
    go.Figure
    """
    path_length_cm = jet_diameter_um * 1e-4

    # Sweep concentration from 0 to 3× operating point (avoid divide-by-zero at 0)
    c_max_mM = max(result.concentration_mM * 3.0, 1.0)
    c_sweep_mM = np.linspace(0.0, c_max_mM, N_SWEEP)
    od_sweep = config.extinction_coeff * (c_sweep_mM / 1000.0) * path_length_cm

    fig = _base_figure(
        title=f"OD vs. Concentration — {config.sample_name}",
        xaxis_title="Concentration (mM)",
        yaxis_title="Absorbance (OD)",
    )

    # Sweep line
    fig.add_trace(go.Scatter(
        x=c_sweep_mM,
        y=od_sweep,
        mode="lines",
        line=dict(color=LINE_COLOR, width=2),
        name="Beer-Lambert",
    ))

    # Operating point
    fig.add_trace(go.Scatter(
        x=[result.concentration_mM],
        y=[target_absorbance],
        mode="markers",
        marker=dict(color=MARKER_COLOR, size=MARKER_SIZE, symbol="circle"),
        name=f"Operating point ({result.concentration_mM:.1f} mM, OD {target_absorbance:.4f})",
    ))

    return fig


# ---------------------------------------------------------------------------
# Plot 2 — fexc vs. Jet Depth
# ---------------------------------------------------------------------------

def plot_fexc_vs_depth(
    config: SampleConfig,
    result: FluenceResult,
    jet_diameter_um: float,
    target_absorbance: float,
) -> go.Figure:
    """
    Excitation fraction as a function of depth through the jet, showing
    Beer-Lambert attenuation from front face to back face.

    Special markers are placed at the front face, midpoint, and back face.
    A horizontal dashed line shows the target <fexc>.

    Parameters
    ----------
    config : SampleConfig
    result : FluenceResult
        Output of calculate_fluence() at the current inputs.
    jet_diameter_um : float
        Total jet diameter (µm); defines the x-axis range.
    target_absorbance : float
        OD of the sample; used to compute attenuation at each depth.

    Returns
    -------
    go.Figure
    """
    depths_um = np.linspace(0.0, jet_diameter_um, N_SWEEP)
    # fexc(z) = fexc_front * 10^(-A * z / jet_diameter_um)
    fexc_z = result.fexc_front * 10.0 ** (-target_absorbance * depths_um / jet_diameter_um)

    target_fexc = result.fexc_front * 10.0 ** (-target_absorbance / 2.0)  # midpoint = <fexc>

    fig = _base_figure(
        title=f"fexc vs. Jet Depth — {config.sample_name}",
        xaxis_title="Depth into jet (µm)",
        yaxis_title="fexc(z)",
    )

    # Continuous curve
    fig.add_trace(go.Scatter(
        x=depths_um,
        y=fexc_z,
        mode="lines",
        line=dict(color=LINE_COLOR, width=2),
        name="fexc(z)",
    ))

    # Horizontal dashed line at <fexc>
    fig.add_hline(
        y=target_fexc,
        line=dict(color="grey", dash="dash", width=1),
        annotation_text=f"⟨fexc⟩ = {target_fexc:.5f}",
        annotation_position="top right",
    )

    # Special markers: front, midpoint, back
    marker_x = [0.0, jet_diameter_um / 2.0, jet_diameter_um]
    marker_y = [result.fexc_front, target_fexc, result.fexc_back]
    marker_labels = [
        f"Front: {result.fexc_front:.5f}",
        f"Mid ⟨fexc⟩: {target_fexc:.5f}",
        f"Back: {result.fexc_back:.5f}",
    ]

    fig.add_trace(go.Scatter(
        x=marker_x,
        y=marker_y,
        mode="markers",
        marker=dict(color=MARKER_COLOR, size=MARKER_SIZE, symbol="circle"),
        name="Front / Mid / Back",
        text=marker_labels,
        hovertemplate="%{text}<extra></extra>",
    ))

    return fig


# ---------------------------------------------------------------------------
# Shared sweep helper for Plots 3 & 4
# ---------------------------------------------------------------------------

def _sweep_fexc(
    config: SampleConfig,
    target_absorbance: float,
    wavelength_nm: float,
    spot_size_v_um: float,
    spot_size_h_um: float,
    rep_rate_Hz: float,
    pulse_duration_s: float,
    fexc_max: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sweep <fexc> from near-zero to fexc_max, computing pulse_energy_uJ and
    fluence_mJ_cm2 at each point.

    Returns
    -------
    fexc_vals : np.ndarray   shape (N_SWEEP,)
    energies  : np.ndarray   shape (N_SWEEP,)   µJ
    fluences  : np.ndarray   shape (N_SWEEP,)   mJ/cm²
    """
    fexc_vals = np.linspace(1e-4, max(fexc_max, 1e-3), N_SWEEP)
    energies = np.empty(N_SWEEP)
    fluences = np.empty(N_SWEEP)

    for i, fexc in enumerate(fexc_vals):
        r = calculate_fluence(
            config=config,
            target_absorbance=target_absorbance,
            wavelength_nm=wavelength_nm,
            spot_size_v_um=spot_size_v_um,
            spot_size_h_um=spot_size_h_um,
            rep_rate_Hz=rep_rate_Hz,
            target_fexc=float(fexc),
            pulse_duration_s=pulse_duration_s,
        )
        energies[i] = r.pulse_energy_uJ
        fluences[i] = r.fluence_mJ_cm2

    return fexc_vals, energies, fluences


# ---------------------------------------------------------------------------
# Plot 3 — Pulse Energy vs. <fexc>
# ---------------------------------------------------------------------------

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
    """
    Pulse energy (µJ) on the x-axis vs. <fexc> on the y-axis.

    The y-axis runs from 0 to fexc_max. The curve is generated by sweeping
    <fexc> and computing the required pulse energy at each point, then
    plotting energy vs. fexc (i.e. x and y are swapped relative to the
    calculation sweep order).

    The current operating point is shown as a highlighted dot.

    Parameters
    ----------
    config : SampleConfig
    target_absorbance : float
    wavelength_nm : float
    spot_size_v_um : float
    spot_size_h_um : float
    rep_rate_Hz : float
    pulse_duration_s : float
    current_fexc : float
        The current target <fexc> (for the operating point marker).
    current_result : FluenceResult
        Pre-computed result at current_fexc (for the operating point marker).
    fexc_max : float
        Upper limit of the <fexc> axis (and sweep range). Default 2.0.

    Returns
    -------
    go.Figure
    """
    fexc_vals, energies, _ = _sweep_fexc(
        config, target_absorbance, wavelength_nm,
        spot_size_v_um, spot_size_h_um, rep_rate_Hz, pulse_duration_s, fexc_max,
    )

    fig = _base_figure(
        title=f"Pulse Energy vs. ⟨fexc⟩ — {config.sample_name}",
        xaxis_title="Pulse Energy (µJ)",
        yaxis_title="⟨fexc⟩",
    )

    fig.add_trace(go.Scatter(
        x=energies,
        y=fexc_vals,
        mode="lines",
        line=dict(color=LINE_COLOR, width=2),
        name="⟨fexc⟩ vs. pulse energy",
    ))

    fig.add_trace(go.Scatter(
        x=[current_result.pulse_energy_uJ],
        y=[current_fexc],
        mode="markers",
        marker=dict(color=MARKER_COLOR, size=MARKER_SIZE, symbol="circle"),
        name=f"Operating point ({current_result.pulse_energy_uJ:.2f} µJ, ⟨fexc⟩={current_fexc:.3f})",
    ))

    fig.update_yaxes(range=[0, fexc_max])

    return fig


# ---------------------------------------------------------------------------
# Plot 4 — Fluence vs. Pulse Energy
# ---------------------------------------------------------------------------

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
    """
    Fluence (mJ/cm²) vs. pulse energy (µJ).

    Uses the same fexc sweep as plot_pulse_energy_vs_fexc to generate the
    curve; extracts (pulse_energy_uJ, fluence_mJ_cm2) pairs.

    The current operating point is shown as a highlighted dot.

    Parameters
    ----------
    (same as plot_pulse_energy_vs_fexc)

    Returns
    -------
    go.Figure
    """
    _, energies, fluences = _sweep_fexc(
        config, target_absorbance, wavelength_nm,
        spot_size_v_um, spot_size_h_um, rep_rate_Hz, pulse_duration_s, fexc_max,
    )

    fig = _base_figure(
        title=f"Fluence vs. Pulse Energy — {config.sample_name}",
        xaxis_title="Pulse Energy (µJ)",
        yaxis_title="Fluence (mJ/cm²)",
    )

    fig.add_trace(go.Scatter(
        x=energies,
        y=fluences,
        mode="lines",
        line=dict(color=LINE_COLOR, width=2),
        name="Fluence vs. pulse energy",
    ))

    fig.add_trace(go.Scatter(
        x=[current_result.pulse_energy_uJ],
        y=[current_result.fluence_mJ_cm2],
        mode="markers",
        marker=dict(color=MARKER_COLOR, size=MARKER_SIZE, symbol="circle"),
        name=(
            f"Operating point ({current_result.pulse_energy_uJ:.2f} µJ, "
            f"{current_result.fluence_mJ_cm2:.2f} mJ/cm²)"
        ),
    ))

    return fig
