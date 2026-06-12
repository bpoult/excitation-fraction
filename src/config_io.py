"""
config_io.py
------------
Handles saving, loading, and listing JSON configuration files for the
Sample & Laser Calculations Dash app.

Each config file is a flat JSON object containing all input fields for both
calculation tabs plus 'name' and 'created' metadata fields.

Public API
----------
list_configs(configs_dir)  -> list[dict]   — options for dcc.Dropdown
load_config(filepath)      -> dict          — all input field values
save_config(configs_dir, name, data) -> pathlib.Path
"""

import json
import pathlib
import re
from datetime import datetime

# ---------------------------------------------------------------------------
# Required fields that must be present in every config file
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = (
    "sample_name",
    "extinction_coeff",
    "molecular_weight",
    "solvent_ratio",
    "jet_diameter_um",
    "reservoir_volume_mL",
    "target_absorbance",
    "wavelength_nm",
    "spot_size_v_um",
    "spot_size_h_um",
    "rep_rate_Hz",
    "target_fexc",
    "pulse_duration_s",
)

# Default configs directory — resolved relative to this file's location
# (src/ → parent → Excitation_Fraction/ → configs/)
CONFIGS_DIR = pathlib.Path(__file__).parent.parent / "configs"


def list_configs(configs_dir: pathlib.Path = CONFIGS_DIR) -> list[dict]:
    """
    Scan configs_dir for all *.json files and return a list of dicts suitable
    for use as dcc.Dropdown options.

    Each dict has:
        "label"  — the 'name' field from inside the JSON (display text)
        "value"  — the absolute filepath string (dropdown value)

    Results are sorted alphabetically by filename. Returns [] if the directory
    does not exist or contains no JSON files.

    Parameters
    ----------
    configs_dir : pathlib.Path
        Directory to scan. Defaults to CONFIGS_DIR.

    Returns
    -------
    list[dict]
        List of {"label": str, "value": str} dicts.
    """
    if not configs_dir.exists():
        return []

    options = []
    for path in sorted(configs_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            label = data.get("name", path.stem)
            options.append({"label": label, "value": str(path)})
        except (json.JSONDecodeError, OSError):
            # Skip malformed or unreadable files silently
            continue

    return options


def load_config(filepath: str | pathlib.Path) -> dict:
    """
    Load and validate a config JSON file.

    Parameters
    ----------
    filepath : str or pathlib.Path
        Path to the JSON config file.

    Returns
    -------
    dict
        Full config dict including 'name', 'created', and all input fields.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the JSON is malformed or any required field is missing.
    """
    filepath = pathlib.Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in config file '{filepath}': {exc}") from exc

    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        raise ValueError(
            f"Config file '{filepath}' is missing required fields: {missing}"
        )

    return data


def save_config(
    configs_dir: pathlib.Path = CONFIGS_DIR,
    name: str = "",
    data: dict = None,
) -> pathlib.Path:
    """
    Save a configuration dict as a named JSON file.

    The filename is derived from `name` by lowercasing, collapsing non-word
    characters to underscores, and appending '.json'.
    Example: "My Config #2" -> "my_config__2.json"

    The 'name' and 'created' keys in `data` are set/overwritten by this function.
    `configs_dir` is created if it does not exist.

    This function does NOT check for existing files — the overwrite confirmation
    is handled at the Dash callback level before this function is called.

    Parameters
    ----------
    configs_dir : pathlib.Path
        Directory in which to save the file. Created if absent.
    name : str
        Human-readable config name (stored in JSON and used for the filename).
    data : dict
        Dict of all input field values. Modified in place to add 'name' and
        'created'.

    Returns
    -------
    pathlib.Path
        Absolute path of the written file.
    """
    if data is None:
        data = {}

    configs_dir.mkdir(parents=True, exist_ok=True)

    filename = re.sub(r"[^\w]+", "_", name.strip().lower()) + ".json"
    filepath = configs_dir / filename

    data["name"] = name
    data["created"] = datetime.now().isoformat()

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return filepath


def config_exists(configs_dir: pathlib.Path = CONFIGS_DIR, name: str = "") -> bool:
    """
    Return True if a config file derived from `name` already exists in configs_dir.

    Parameters
    ----------
    configs_dir : pathlib.Path
        Directory to check.
    name : str
        Human-readable config name.

    Returns
    -------
    bool
    """
    filename = re.sub(r"[^\w]+", "_", name.strip().lower()) + ".json"
    return (configs_dir / filename).exists()
