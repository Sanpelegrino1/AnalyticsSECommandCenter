"""Default style configuration and user-override system for Tableau Next visualizations.

Provides a small set of user-facing style knobs (e.g. backgroundColor, fontColor)
that map to deeply-nested JSON paths in the visualization payload.
"""

from typing import Any, Dict, Optional
import copy

# User-facing defaults.  Keys here are the ones accepted by --style on the CLI.
STYLE_DEFAULTS: Dict[str, Any] = {
    "backgroundColor": "#FFFFFF",
    "bandingColor": "#E5E5E5",
    "fontColor": "#2E2E2E",
    "fontSize": 13,
    "actionableHeaderColor": "#0250D9",
    "lineColor": "#C9C9C9",
    "fit": None,  # None = chart-type default
}

# The seven standard font keys present in every non-Table chart.
FONT_KEYS = [
    "actionableHeaders",
    "axisTickLabels",
    "fieldLabels",
    "headers",
    "legendLabels",
    "markLabels",
    "marks",
]

# Table adds two extra font keys.
TABLE_EXTRA_FONT_KEYS = ["grandTotalLabel", "grandTotalValues"]

LINE_KEYS = ["axisLine", "fieldLabelDividerLine", "separatorLine", "zeroLine"]


def build_fonts(overrides: Dict[str, Any], *, is_table: bool = False) -> dict:
    """Build the complete ``style.fonts`` object."""
    color = overrides.get("fontColor", STYLE_DEFAULTS["fontColor"])
    size = int(overrides.get("fontSize", STYLE_DEFAULTS["fontSize"]))
    ah_color = overrides.get("actionableHeaderColor", STYLE_DEFAULTS["actionableHeaderColor"])

    fonts: Dict[str, dict] = {}
    keys = FONT_KEYS + (TABLE_EXTRA_FONT_KEYS if is_table else [])
    for key in keys:
        fonts[key] = {
            "color": ah_color if key == "actionableHeaders" else color,
            "size": size,
        }
    return fonts


def build_lines(overrides: Dict[str, Any]) -> dict:
    """Build the complete ``style.lines`` object."""
    color = overrides.get("lineColor", STYLE_DEFAULTS["lineColor"])
    return {k: {"color": color} for k in LINE_KEYS}


def build_shading(overrides: Dict[str, Any], *, with_banding: bool = True) -> dict:
    """Build the complete ``style.shading`` object."""
    bg = overrides.get("backgroundColor", STYLE_DEFAULTS["backgroundColor"])
    shading: Dict[str, Any] = {"backgroundColor": bg}
    if with_banding:
        banding_color = overrides.get("bandingColor", STYLE_DEFAULTS["bandingColor"])
        shading["banding"] = {"rows": {"color": banding_color}}
    else:
        shading["banding"] = {}
    return shading


def build_field_labels(overrides: Dict[str, Any], *, is_table: bool = False) -> dict:
    """Build the ``style.fieldLabels`` object."""
    base = {"showDividerLine": False, "showLabels": True}
    if is_table:
        bg = overrides.get("bandingColor", STYLE_DEFAULTS["bandingColor"])
        base["backgroundColor"] = bg
    return {"columns": dict(base), "rows": dict(base)}


def resolve_fit(overrides: Dict[str, Any], chart_default: str) -> str:
    """Return the effective ``fit`` value (user override or chart-type default)."""
    return overrides.get("fit", None) or chart_default


def parse_style_args(style_args: Optional[list]) -> Dict[str, Any]:
    """Parse ``--style key=value`` CLI arguments into a dict.

    Accepts strings like ``backgroundColor=#1A1A1A`` or ``fontSize=12``.
    """
    if not style_args:
        return {}
    overrides: Dict[str, Any] = {}
    for arg in style_args:
        if "=" not in arg:
            continue
        key, value = arg.split("=", 1)
        key = key.strip()
        if key not in STYLE_DEFAULTS:
            continue
        if key == "fontSize":
            value = int(value)
        overrides[key] = value
    return overrides
