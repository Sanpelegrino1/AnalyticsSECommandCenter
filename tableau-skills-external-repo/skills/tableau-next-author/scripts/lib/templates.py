"""Per-chart-type template builders for Tableau Next visualizations.

Each ``build_<type>`` function returns a complete ``visualSpecification`` dict
(including the nested ``style`` subtree) ready to be wrapped by
``build_root_envelope``.

Templates are extracted from production packages and verified against
the Salesforce REST API.
"""

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from . import style_defaults as sd
from . import dashboard_patterns as dp

# ---------------------------------------------------------------------------
# Chart-type metadata
# ---------------------------------------------------------------------------

CHART_CONFIGS: Dict[str, Dict[str, Any]] = {
    "bar":        {"fit": "Entire",          "size_type": "Percentage", "size_val": 75,  "reverse": True,  "banding": True,  "auto_size": True},
    "line":       {"fit": "Entire",          "size_type": "Pixel",      "size_val": 3,   "reverse": False, "banding": False, "auto_size": False},
    "donut":      {"fit": "Entire",          "size_type": "Percentage", "size_val": 80,  "reverse": True,  "banding": True,  "auto_size": True},
    "scatter":    {"fit": "Standard",        "size_type": "Pixel",      "size_val": 10,  "reverse": False, "banding": False, "auto_size": False},
    "table":      {"fit": "RowHeadersWidth", "size_type": "Pixel",      "size_val": 12,  "reverse": True,  "banding": True,  "auto_size": True},
    "funnel":     {"fit": "Entire",          "size_type": "Percentage", "size_val": 75,  "reverse": True,  "banding": True,  "auto_size": True},
    "heatmap":    {"fit": "Entire",        "size_type": "Percentage", "size_val": 100, "reverse": True,  "banding": True,  "auto_size": True},
    "dot_matrix": {"fit": "Entire",          "size_type": "Pixel",      "size_val": 111, "reverse": True,  "banding": True,  "auto_size": False},
}

VALID_MARK_TYPES = {"Bar", "Line", "Donut", "Circle", "Text", "Square"}

# v66.12: visualSpecification.marks.headers must include stack (see Stacked_package minor 12).
VIZQL_MARK_HEADERS: Dict[str, Any] = {
    "encodings": [],
    "isAutomatic": True,
    "stack": {"isAutomatic": True, "isStacked": False},
    "type": "Text",
}

# Map CLI chart names to actual marks.panes.type values
CHART_TO_MARK_TYPE = {
    "bar": "Bar",
    "line": "Line",
    "donut": "Donut",
    "scatter": "Circle",
    "table": "Text",
    "funnel": "Bar",
    "heatmap": "Bar",
    "dot_matrix": "Circle",
}


def _structural_marks_panes(
    chart_key: str,
    mark_type: str,
    encodings: List[dict],
    *,
    is_automatic: bool,
    stack: Dict[str, Any],
) -> Dict[str, Any]:
    """Build ``visualSpecification.marks.panes`` (v66.12 POST).

    range and size belong in style.marks.panes only; the structural
    marks.panes must NOT include them (API rejects "Unrecognized field").
    """
    return {
        "encodings": encodings,
        "isAutomatic": is_automatic,
        "type": mark_type,
        "stack": stack,
    }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _marks_panes_style(cfg: Dict[str, Any], overrides: Dict[str, Any], *, is_funnel: bool = False) -> dict:
    """Build ``style.marks.panes``."""
    panes: Dict[str, Any] = {
        "color": {"color": ""},
        "isAutomaticSize": cfg["auto_size"],
        "label": {
            "canOverlapLabels": False,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": cfg.get("show_mark_labels", False),
        },
        "range": {"reverse": cfg["reverse"]},
        "size": {"isAutomatic": cfg["auto_size"], "type": cfg["size_type"], "value": cfg["size_val"]},
    }
    if is_funnel:
        panes["isStackingAxisCentered"] = True
        panes["connector"] = {"type": "Origami"}
    elif cfg.get("stacking_centered") is not None:
        panes["isStackingAxisCentered"] = cfg["stacking_centered"]
    else:
        panes["isStackingAxisCentered"] = False
    return panes


def _marks_headers_style(cfg: Dict[str, Any]) -> dict:
    """Build ``style.marks.headers`` (v66.12: range + size required alongside panes)."""
    return {
        "color": {"color": ""},
        "isAutomaticSize": True,
        "label": {
            "canOverlapLabels": False,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": False,
        },
        "range": {"reverse": cfg["reverse"]},
        "size": {"isAutomatic": True, "type": "Pixel", "value": 13},
    }


def _base_style(
    cfg: Dict[str, Any],
    overrides: Dict[str, Any],
    *,
    axis_fields: Optional[dict] = None,
    encoding_fields: Optional[dict] = None,
    header_fields: Optional[dict] = None,
    is_table: bool = False,
    is_funnel: bool = False,
    show_mark_labels: bool = True,
) -> dict:
    cfg_copy = dict(cfg)
    cfg_copy["show_mark_labels"] = show_mark_labels

    style: Dict[str, Any] = {
        "axis": {"fields": axis_fields or {}},
        "encodings": {"fields": encoding_fields or {}},
        "fieldLabels": sd.build_field_labels(overrides, is_table=is_table),
        "fit": sd.resolve_fit(overrides, cfg["fit"]),
        "fonts": sd.build_fonts(overrides, is_table=is_table),
        "headers": {
            "columns": {"mergeRepeatedCells": not is_table, "showIndex": False},
            "fields": header_fields or {},
            "rows": {"mergeRepeatedCells": not is_table, "showIndex": is_table},
        },
        "lines": sd.build_lines(overrides),
        "marks": {
            "fields": {},
            "headers": _marks_headers_style(cfg_copy),
            "panes": _marks_panes_style(cfg_copy, overrides, is_funnel=is_funnel),
        },
        "referenceLines": {},
        "shading": sd.build_shading(overrides, with_banding=cfg["banding"]),
        "showDataPlaceholder": False,
        "title": {"isVisible": True},
    }
    if is_table:
        style["grandTotals"] = {"rows": {"position": "Start"}}
        style.pop("showDataPlaceholder", None)
        style.pop("referenceLines", None)
    return style


def _axis_field_entry(
    fmt_type: str = "CurrencyShort",
    decimal_places: int = 2,
) -> dict:
    return {
        "isVisible": True,
        "isZeroLineVisible": True,
        "range": {"includeZero": True, "type": "Auto"},
        "scale": {"format": {"numberFormatInfo": _num_fmt(fmt_type, decimal_places)}},
        "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}},
    }


def _encoding_field_entry(fmt_type: str = "Currency", decimal_places: int = 2) -> dict:
    return {"defaults": {"format": {"numberFormatInfo": _num_fmt(fmt_type, decimal_places)}}}


def _encoding_field_empty() -> dict:
    return {"defaults": {"format": {}}}


def _header_field_entry() -> dict:
    return {"hiddenValues": [], "isVisible": True, "showMissingValues": False}


def _add_size_encoding_support(
    encodings: List[dict],
    enc_f: Dict[str, dict],
    *,
    mode: str = "heatmap",
) -> None:
    """Add Size encoding support under style.encodings.fields (v66.12: min/max, not value)."""
    for enc in encodings:
        if enc.get("type") == "Size":
            fk = enc.get("fieldKey")
            if fk and fk in enc_f:
                enc_f[fk]["isAutomaticSize"] = True
                if "size" not in enc_f[fk]:
                    if mode == "scatter":
                        enc_f[fk]["size"] = {
                            "isAutomatic": True,
                            "type": "Pixel",
                            "min": 20,
                            "max": 80,
                        }
                    else:
                        enc_f[fk]["size"] = {
                            "isAutomatic": True,
                            "type": "Percentage",
                            "min": 10,
                            "max": 75,
                        }


def _add_color_encoding_support(
    encodings: List[dict],
    enc_f: Dict[str, dict],
    fields: Dict[str, dict],
    legends: Dict[str, dict],
    columns: Optional[List[str]] = None,
    rows: Optional[List[str]] = None,
    palette: Optional[List[str]] = None,
    custom_colors: Optional[List[Dict[str, str]]] = None,
) -> None:
    """Add Color encoding support for dimension and measure fields.
    
    When a field has Color encoding, it needs a color palette:
    - Dimension fields: Discrete color palette (for stacked bars, multi-series charts)
    - Measure fields: Continuous color palette (for heatmaps)
    
    CRITICAL: Color palettes must be applied for ALL Color encodings, regardless of shelf placement.
    This ensures charts show colors instead of all appearing blue.
    
    Args:
        encodings: List of encoding definitions
        enc_f: Encoding fields dict to update
        fields: Field definitions dict
        legends: Legends dict to update (for legend configuration)
        columns: List of column field keys (to check if dimension is on shelf)
        rows: List of row field keys (to check if dimension is on shelf)
        palette: Optional custom color palette (default: diverse color palette)
    """
    # Default diverse color palette (8 colors) for discrete dimensions
    default_palette = [
        "#4992fe",  # Blue
        "#ba01ff",  # Purple
        "#06a59a",  # Teal
        "#3a49da",  # Indigo
        "#fe5c4c",  # Red
        "#024d4c",  # Dark teal
        "#3ba755",  # Green
        "#8a033e",  # Maroon
    ]
    
    color_palette = palette or default_palette
    shelf_keys = set(columns or []) | set(rows or [])
    
    for enc in encodings:
        if enc.get("type") == "Color":
            fk = enc.get("fieldKey")
            if fk and fk in fields:
                fdef = fields[fk]
                
                # Ensure encoding field entry exists
                if fk not in enc_f:
                    enc_f[fk] = {"defaults": {"format": {}}}
                
                if fdef.get("role") == "Dimension":
                    # Dimension fields: Use discrete color palette
                    # CRITICAL: Apply colors even if field is on shelf (for stacked bars)
                    if custom_colors:
                        enc_f[fk]["colors"] = {
                            "customColors": [{"color": c["color"], "value": c["value"]} for c in custom_colors],
                            "palette": {
                                "colors": color_palette,
                                "type": "Custom"
                            },
                            "type": "Discrete"
                        }
                    else:
                        enc_f[fk]["colors"] = {
                            "customColors": [],
                            "palette": {
                                "colors": color_palette,
                                "type": "Custom"
                            },
                            "type": "Discrete"
                        }
                elif fdef.get("role") == "Measure":
                    # Measure fields: Use continuous color palette (for heatmaps)
                    # Default heatmap palette if not already set
                    if "colors" not in enc_f[fk]:
                        enc_f[fk]["colors"] = {
                            "palette": {
                                "end": "#FF906E",
                                "start": "#5867E8",
                                "startToEndSteps": []
                            },
                            "type": "Continuous"
                        }


def _num_fmt(fmt_type: str = "Currency", decimal_places: int = 2) -> dict:
    return {
        "decimalPlaces": decimal_places,
        "displayUnits": "Auto",
        "includeThousandSeparator": True,
        "negativeValuesFormat": "Auto",
        "prefix": "",
        "suffix": "",
        "type": fmt_type,
    }


# ---------------------------------------------------------------------------
# Format inference
# ---------------------------------------------------------------------------

# Axis format suffixes corresponding to encoding format types
_AXIS_FORMAT_MAP = {
    "Currency": "CurrencyShort",
    "Number": "NumberShort",
    "Percentage": "Percentage",
}


def _infer_format_type(fdef: dict) -> str:
    """Infer the number format type from field properties instead of
    always defaulting to Currency."""
    ftype = fdef.get("type", "Field")
    if ftype in ("MeasureValues", "MeasureNames"):
        return "Number"
    func = fdef.get("function")
    if func in ("Count", "CountDistinct", "UserAgg"):
        return "Number"
    fn = fdef.get("fieldName", "")
    if any(kw in fn.lower() for kw in ("rate", "percent", "ratio", "probability")):
        return "Percentage"
    return "Currency"


def _infer_aggregation_type(fdef: dict) -> Optional[str]:
    """Infer the aggregation type from field properties.
    
    Some fields like Probability should be aggregated as Avg, not Sum.
    
    CRITICAL: Never override UserAgg - CLC fields with UserAgg must preserve it.
    
    Args:
        fdef: Field definition dict
        
    Returns:
        Aggregation type ("Avg", "Sum", etc.) or None to use default
    """
    # CRITICAL: Never override UserAgg - CLC fields with UserAgg must preserve it
    if fdef.get("function") == "UserAgg" or fdef.get("aggregationType") == "UserAgg":
        return None  # Don't override - preserve UserAgg
    
    fn = fdef.get("fieldName", "").lower()
    # Fields that represent rates, probabilities, or percentages should use Avg
    if any(kw in fn for kw in ("probability", "rate", "percent", "ratio", "average", "avg")):
        return "Avg"
    return None


# ---------------------------------------------------------------------------
# Per-chart-type builders
# ---------------------------------------------------------------------------

def build_bar(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
    legends: Dict[str, dict],
    overrides: Dict[str, Any],
    reference_lines: Optional[dict] = None,
    measure_values: Optional[List[str]] = None,
    sort_orders: Optional[dict] = None,
    palette: Optional[List[str]] = None,
    custom_colors: Optional[List[Dict[str, str]]] = None,
) -> dict:
    cfg = CHART_CONFIGS["bar"]
    axis_f, enc_f, hdr_f = _auto_style_fields(fields, columns, rows, encodings)

    # measureValues real-measure fields also need encoding style entries
    for mv_key in (measure_values or []):
        if mv_key in fields and mv_key not in enc_f:
            fdef = fields[mv_key]
            if fdef.get("role") == "Measure":
                enc_f[mv_key] = _encoding_field_entry(_infer_format_type(fdef))

    # Add Size encoding support
    _add_size_encoding_support(encodings, enc_f, mode="heatmap")
    
    # Add Color encoding support for dimension fields
    _add_color_encoding_support(encodings, enc_f, fields, legends, columns, rows, palette=palette, custom_colors=custom_colors)

    style = _base_style(
        cfg, overrides,
        axis_fields=axis_f,
        encoding_fields=enc_f,
        header_fields=hdr_f,
    )
    if reference_lines:
        style["referenceLines"] = reference_lines

    mv_list = measure_values or []
    # Side-by-side (MeasureValues) bars are not stacked; single-measure bars use stacked panes.
    panes_stacked = len(mv_list) < 2

    return {
        "columns": columns,
        "rows": rows,
        "forecasts": {},
        "layout": "Vizql",
        "legends": legends,
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "bar",
                "Bar",
                encodings,
                is_automatic=not bool(encodings),
                stack={"isAutomatic": True, "isStacked": panes_stacked},
            ),
        },
        "measureValues": mv_list,
        "referenceLines": reference_lines or {},
        "style": style,
    }


def build_funnel(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
    legends: Dict[str, dict],
    overrides: Dict[str, Any],
    sort_orders: Optional[dict] = None,
    palette: Optional[List[str]] = None,
    custom_colors: Optional[List[Dict[str, str]]] = None,
) -> dict:
    cfg = CHART_CONFIGS["funnel"]
    axis_f, enc_f, hdr_f = _auto_style_fields(fields, columns, rows, encodings)

    # Add Size encoding support
    _add_size_encoding_support(encodings, enc_f, mode="heatmap")
    
    # Add Color encoding support for dimension fields
    _add_color_encoding_support(encodings, enc_f, fields, legends, columns, rows, palette=palette, custom_colors=custom_colors)

    style = _base_style(
        cfg, overrides,
        axis_fields=axis_f,
        encoding_fields=enc_f,
        header_fields=hdr_f,
        is_funnel=True,
        show_mark_labels=False,
    )

    return {
        "columns": columns,
        "rows": rows,
        "forecasts": {},
        "layout": "Vizql",
        "legends": legends,
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "funnel",
                "Bar",
                encodings,
                is_automatic=not bool(encodings),
                stack={"isAutomatic": True, "isStacked": True},
            ),
        },
        "measureValues": [],
        "referenceLines": {},
        "style": style,
    }


def build_heatmap(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
    legends: Dict[str, dict],
    overrides: Dict[str, Any],
    color_field_key: Optional[str] = None,
    palette_start: str = "#5867E8",
    palette_end: str = "#FF906E",
    palette_middle: Optional[str] = None,
) -> dict:
    cfg = CHART_CONFIGS["heatmap"]
    axis_f, enc_f, hdr_f = _auto_style_fields(fields, columns, rows, encodings)

    # Add Size encoding support
    _add_size_encoding_support(encodings, enc_f, mode="heatmap")
    
    # Add Color encoding support (handles both dimensions and measures)
    _add_color_encoding_support(encodings, enc_f, fields, legends, columns, rows)
    
    # Ensure heatmap measure color is set (override if needed)
    if palette_middle:
        palette_obj = {
            "start": palette_start,
            "middle": palette_middle,
            "end": palette_end,
            "startToMiddleSteps": [],
            "middleToEndSteps": [],
        }
    else:
        palette_obj = {
            "start": palette_start,
            "end": palette_end,
            "startToEndSteps": [],
        }
    if color_field_key:
        # Find the measure field used for color encoding
        for enc in encodings:
            if enc.get("type") == "Color" and enc.get("fieldKey") == color_field_key:
                if color_field_key in enc_f:
                    enc_f[color_field_key]["colors"] = {
                        "palette": palette_obj,
                        "type": "Continuous",
                    }
                break
        # If no Color encoding found but color_field_key specified, create it
        if color_field_key in fields and color_field_key not in [e.get("fieldKey") for e in encodings if e.get("type") == "Color"]:
            if color_field_key not in enc_f:
                enc_f[color_field_key] = {"defaults": {"format": {}}}
            enc_f[color_field_key]["colors"] = {
                "palette": palette_obj,
                "type": "Continuous",
            }

    style = _base_style(cfg, overrides, axis_fields=axis_f, encoding_fields=enc_f, header_fields=hdr_f)

    return {
        "columns": columns,
        "rows": rows,
        "forecasts": {},
        "layout": "Vizql",
        "legends": legends,
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "heatmap",
                "Bar",
                encodings,
                is_automatic=False,
                stack={"isAutomatic": True, "isStacked": True},
            ),
        },
        "measureValues": [],
        "referenceLines": {},
        "style": style,
    }


def build_line(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
    legends: Dict[str, dict],
    overrides: Dict[str, Any],
    palette: Optional[List[str]] = None,
    custom_colors: Optional[List[Dict[str, str]]] = None,
) -> dict:
    cfg = CHART_CONFIGS["line"]
    axis_f, enc_f, hdr_f = _auto_style_fields(fields, columns, rows, encodings)
    
    # Add Color encoding support for dimension fields
    _add_color_encoding_support(encodings, enc_f, fields, legends, columns, rows, palette=palette, custom_colors=custom_colors)

    style = _base_style(cfg, overrides, axis_fields=axis_f, encoding_fields=enc_f, header_fields=hdr_f)

    return {
        "columns": columns,
        "rows": rows,
        "forecasts": {},
        "layout": "Vizql",
        "legends": legends,
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "line",
                "Line",
                encodings,
                is_automatic=not bool(encodings),
                stack={"isAutomatic": True, "isStacked": False},
            ),
        },
        "measureValues": [],
        "referenceLines": {},
        "style": style,
    }


def build_donut(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
    legends: Dict[str, dict],
    overrides: Dict[str, Any],
    sort_orders: Optional[dict] = None,
    palette: Optional[List[str]] = None,
    custom_colors: Optional[List[Dict[str, str]]] = None,
) -> dict:
    cfg = CHART_CONFIGS["donut"]
    _axis_f, enc_f, _hdr_f = _auto_style_fields(fields, columns, rows, encodings)
    
    # Add Color encoding support for dimension fields
    _add_color_encoding_support(encodings, enc_f, fields, legends, columns, rows, palette=palette, custom_colors=custom_colors)

    style = _base_style(
        cfg, overrides,
        axis_fields={},
        encoding_fields=enc_f,
        header_fields={},
    )

    return {
        "columns": [],
        "rows": [],
        "forecasts": {},
        "layout": "Vizql",
        "legends": legends,
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "donut",
                "Donut",
                encodings,
                is_automatic=False,
                stack={"isAutomatic": True, "isStacked": False},
            ),
        },
        "measureValues": [],
        "referenceLines": {},
        "style": style,
    }


def build_scatter(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
    legends: Dict[str, dict],
    overrides: Dict[str, Any],
    palette: Optional[List[str]] = None,
    custom_colors: Optional[List[Dict[str, str]]] = None,
) -> dict:
    cfg = CHART_CONFIGS["scatter"]
    axis_f, enc_f, hdr_f = _auto_style_fields(fields, columns, rows, encodings)

    # Add Size encoding support
    _add_size_encoding_support(encodings, enc_f, mode="scatter")
    
    # Add Color encoding support for dimension fields
    _add_color_encoding_support(encodings, enc_f, fields, legends, columns, rows, palette=palette, custom_colors=custom_colors)

    # Enable mark labels when Label encoding is present (e.g., label_measure)
    show_mark_labels = any(e.get("type") == "Label" for e in encodings)
    style = _base_style(cfg, overrides, axis_fields=axis_f, encoding_fields=enc_f, header_fields=hdr_f, show_mark_labels=show_mark_labels)

    return {
        "columns": columns,
        "rows": rows,
        "forecasts": {},
        "layout": "Vizql",
        "legends": legends,
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "scatter",
                "Circle",
                encodings,
                is_automatic=False,
                stack={"isAutomatic": True, "isStacked": False},
            ),
        },
        "measureValues": [],
        "referenceLines": {},
        "style": style,
    }


def build_dot_matrix(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
    legends: Dict[str, dict],
    overrides: Dict[str, Any],
    size_field_key: Optional[str] = None,
) -> dict:
    cfg = CHART_CONFIGS["dot_matrix"]
    axis_f, enc_f, hdr_f = _auto_style_fields(fields, columns, rows, encodings)

    _add_size_encoding_support(encodings, enc_f, mode="heatmap")
    if size_field_key and size_field_key in enc_f:
        enc_f[size_field_key]["isAutomaticSize"] = True
        enc_f[size_field_key]["size"] = {
            "isAutomatic": True,
            "type": "Percentage",
            "min": 10,
            "max": 75,
        }

    # Add Color encoding support for dimension fields
    _add_color_encoding_support(encodings, enc_f, fields, legends, columns, rows)

    style = _base_style(cfg, overrides, axis_fields={}, encoding_fields=enc_f, header_fields=hdr_f)

    return {
        "columns": columns,
        "rows": rows,
        "forecasts": {},
        "layout": "Vizql",
        "legends": legends,
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "dot_matrix",
                "Circle",
                encodings,
                is_automatic=False,
                stack={"isAutomatic": True, "isStacked": False},
            ),
        },
        "measureValues": [],
        "referenceLines": {},
        "style": style,
    }


def build_table(
    fields: Dict[str, dict],
    rows: List[str],
    overrides: Dict[str, Any],
    columns: Optional[List[str]] = None,
) -> dict:
    """Build table visualSpecification.
    
    For tables, ALL fields (dimensions AND measures) should be in rows.
    Tables don't support a columns field - measures go in rows along with dimensions.
    """
    cfg = CHART_CONFIGS["table"]
    enc_f: Dict[str, dict] = {}
    hdr_f: Dict[str, dict] = {}
    
    columns = columns or []
    
    # For tables, if measures are specified in columns, add them to rows instead
    # Tables don't support columns - all fields must be in rows
    final_rows = list(rows)
    if columns:
        # Add measures from columns to rows
        for fk in columns:
            if fk not in final_rows and fk in fields:
                final_rows.append(fk)
    
    # Process all fields that will be in rows
    for fk in final_rows:
        if fk not in fields:
            continue
        fdef = fields[fk]
        role = fdef.get("role", "Dimension")
        
        if role == "Measure":
            enc_entry = _encoding_field_entry(_infer_format_type(fdef))
            enc_f[fk] = enc_entry
            display_category = fdef.get("displayCategory")
            if display_category is None:
                display_category = "Continuous"
            if display_category == "Discrete":
                hdr_f[fk] = {**_header_field_entry(), **enc_entry}
        else:
            # Dimensions in rows get header styles (dimensions are discrete by default)
            hdr_f[fk] = _header_field_entry()

    style = _base_style(
        cfg, overrides,
        encoding_fields=enc_f,
        header_fields=hdr_f,
        is_table=True,
    )
    style.pop("axis", None)

    return {
        "layout": "Table",
        "legends": {},
        "marks": {
            "fields": {},
            "headers": copy.deepcopy(VIZQL_MARK_HEADERS),
            "panes": _structural_marks_panes(
                "table",
                "Text",
                [],
                is_automatic=False,
                stack={"isAutomatic": True, "isStacked": False},
            ),
        },
        "rows": final_rows,  # Include measures from columns in rows
        "style": style,
    }


def _sdm_field_to_viz_field(sdm_field: Dict[str, Any]) -> Dict[str, Any]:
    """Build a standard Field entry from SDM field metadata."""
    field_def: Dict[str, Any] = {
        "type": "Field",
        "displayCategory": sdm_field.get(
            "displayCategory",
            "Discrete" if sdm_field.get("role") == "Dimension" else "Continuous",
        ),
        "role": sdm_field.get("role"),
        "fieldName": sdm_field.get("fieldName"),
        "objectName": sdm_field.get("objectName"),
        "function": sdm_field.get("function"),
    }
    if field_def.get("role") == "Measure":
        if field_def.get("function") == "UserAgg" or sdm_field.get("aggregationType") == "UserAgg":
            field_def["function"] = "UserAgg"
        else:
            inferred_agg = _infer_aggregation_type(field_def)
            if inferred_agg:
                field_def["function"] = inferred_agg
            elif not field_def.get("function"):
                field_def["function"] = sdm_field.get("aggregationType", "Sum")
    return field_def


def _soft_blue_continuous_palette() -> Dict[str, Any]:
    # Sequential 2-color palette (empty startToEndSteps only; no startToMiddleSteps per validator)
    return {
        "palette": {
            "end": "#066AFE",
            "start": "#EEF4FF",
            "startToEndSteps": [],
        },
        "type": "Continuous",
    }


def _map_diverging_palette() -> Dict[str, Any]:
    """3-stop continuous palette (matches common map Color exports)."""
    return {
        "palette": {
            "end": "#066AFE",
            "middle": "#feb8ab",
            "middleToEndSteps": [],
            "start": "#EEF4FF",
            "startToEndSteps": [],
            "startToMiddleSteps": [],
        },
        "type": "Continuous",
    }


def _map_background(overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Basemap for layout Map. Default nested style (API v66.12); opt into styleName via map_background_format=modern."""
    if overrides.get("map_background_format") == "modern":
        style_name = overrides.get("map_style_name", overrides.get("map_basemap", "light"))
        return {"type": "Map", "styleName": style_name}
    name = overrides.get("map_style_name", overrides.get("map_basemap", "light"))
    return {"type": "Map", "style": {"type": "Name", "value": name}}


def _flow_level_bar_marks_style(*, reverse: bool = True, size_pct: int = 75) -> Dict[str, Any]:
    return {
        "color": {"color": "#F9E3B6"} if size_pct == 75 else {"color": ""},
        "isAutomaticSize": True,
        "label": {
            "canOverlapLabels": False,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": True,
        },
        "range": {"reverse": reverse},
        "size": {"isAutomatic": True, "type": "Percentage", "value": size_pct},
    }


def _build_viz_map(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    lat = field_mappings["latitude"]
    lon = field_mappings["longitude"]
    meas = field_mappings["measure"]
    lab = field_mappings["label_dim"]
    pos_label = overrides.get("position_name") or "Location"
    fields: Dict[str, Any] = {
        "F1": {
            "type": "MapPosition",
            "displayCategory": "Continuous",
            "positionName": pos_label,
            "positional": {
                "type": "Xy",
                "latitudeOrY": {"fieldName": lat["fieldName"], "objectName": lat.get("objectName")},
                "longitudeOrX": {"fieldName": lon["fieldName"], "objectName": lon.get("objectName")},
            },
            "role": "Dimension",
        },
        "F2": _sdm_field_to_viz_field(meas),
        "F3": _sdm_field_to_viz_field(lab),
    }
    fmt_m = _infer_format_type(fields["F2"])
    enc_f2: Dict[str, Any] = {**_encoding_field_entry(fmt_m), "colors": _soft_blue_continuous_palette()}
    visual_spec: Dict[str, Any] = {
        "layout": "Map",
        "legends": {
            "F2": {"isVisible": True, "position": "Right", "title": {"isVisible": True}},
        },
        "locations": ["F1"],
        "marks": {
            "fields": {},
            "panes": {
                "encodings": [
                    {"fieldKey": "F2", "type": "Color"},
                    {"fieldKey": "F3", "type": "Label"},
                ],
                "isAutomatic": True,
                "stack": {"isAutomatic": True, "isStacked": False},
                "type": "Circle",
            },
        },
        "style": {
            "background": _map_background(overrides),
            "encodings": {"fields": {"F2": enc_f2}},
            "fieldLabels": {
                "columns": {"showDividerLine": False, "showLabels": True},
                "rows": {"showDividerLine": False, "showLabels": True},
            },
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {},
                "panes": {
                    "color": {"color": ""},
                    "isAutomaticSize": False,
                    "label": {
                        "canOverlapLabels": False,
                        "marksToLabel": {"type": "All"},
                        "showMarkLabels": True,
                    },
                    "range": {"reverse": True},
                    "size": {"isAutomatic": False, "type": "Pixel", "value": int(overrides.get("map_point_size_px", 36))},
                },
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_map_location_only(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    lat = field_mappings["latitude"]
    lon = field_mappings["longitude"]
    pos_label = overrides.get("position_name") or "Location"
    fields: Dict[str, Any] = {
        "F1": {
            "type": "MapPosition",
            "displayCategory": "Continuous",
            "positionName": pos_label,
            "positional": {
                "type": "Xy",
                "latitudeOrY": {"fieldName": lat["fieldName"], "objectName": lat.get("objectName")},
                "longitudeOrX": {"fieldName": lon["fieldName"], "objectName": lon.get("objectName")},
            },
            "role": "Dimension",
        },
    }
    px = int(overrides.get("map_point_size_px", 12))
    visual_spec: Dict[str, Any] = {
        "layout": "Map",
        "legends": {},
        "locations": ["F1"],
        "marks": {
            "fields": {},
            "panes": {
                "encodings": [],
                "isAutomatic": True,
                "stack": {"isAutomatic": True, "isStacked": False},
                "type": "Circle",
            },
        },
        "style": {
            "background": _map_background(overrides),
            "encodings": {"fields": {}},
            "fieldLabels": {
                "columns": {"showDividerLine": False, "showLabels": False},
                "rows": {"showDividerLine": False, "showLabels": True},
            },
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {},
                "panes": {
                    "color": {"color": ""},
                    "isAutomaticSize": True,
                    "label": {
                        "canOverlapLabels": False,
                        "marksToLabel": {"type": "All"},
                        "showMarkLabels": True,
                    },
                    "range": {"reverse": True},
                    "size": {"isAutomatic": True, "type": "Pixel", "value": px},
                },
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_map_advanced(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    lat = field_mappings["latitude"]
    lon = field_mappings["longitude"]
    meas = field_mappings["measure"]
    lab = field_mappings["label_dim"]
    pos_label = overrides.get("position_name") or "Location"
    mdef = _sdm_field_to_viz_field(meas)
    fields: Dict[str, Any] = {
        "F1": {
            "type": "MapPosition",
            "displayCategory": "Continuous",
            "positionName": pos_label,
            "positional": {
                "type": "Xy",
                "latitudeOrY": {"fieldName": lat["fieldName"], "objectName": lat.get("objectName")},
                "longitudeOrX": {"fieldName": lon["fieldName"], "objectName": lon.get("objectName")},
            },
            "role": "Dimension",
        },
        "F2": _sdm_field_to_viz_field(lab),
        "F3": copy.deepcopy(mdef),
        "F4": copy.deepcopy(mdef),
        "F5": copy.deepcopy(mdef),
    }
    fmt_m = _infer_format_type(fields["F3"])
    enc_entry = _encoding_field_entry(fmt_m)
    enc_f: Dict[str, Any] = {
        "F3": {**enc_entry, "colors": _map_diverging_palette()},
        "F4": dict(enc_entry),
        "F5": {
            **enc_entry,
            "isAutomaticSize": True,
            "size": {"isAutomatic": True, "type": "Pixel", "min": 20, "max": 80},
        },
    }
    legend_visible = overrides.get("map_color_legend_visible", False)
    visual_spec: Dict[str, Any] = {
        "layout": "Map",
        "legends": {
            "F3": {
                "isVisible": legend_visible,
                "position": "Right",
                "title": {"isVisible": True},
            },
        },
        "locations": ["F1"],
        "marks": {
            "fields": {},
            "panes": {
                "encodings": [
                    {"fieldKey": "F2", "type": "Label"},
                    {"fieldKey": "F3", "type": "Color"},
                    {"fieldKey": "F4", "type": "Label"},
                    {"fieldKey": "F5", "type": "Size"},
                ],
                "isAutomatic": False,
                "stack": {"isAutomatic": True, "isStacked": False},
                "type": "Circle",
            },
        },
        "style": {
            "background": _map_background(overrides),
            "encodings": {"fields": enc_f},
            "fieldLabels": {
                "columns": {"showDividerLine": False, "showLabels": False},
                "rows": {"showDividerLine": False, "showLabels": True},
            },
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {},
                "panes": {
                    "color": {"color": "#5A1BA9"},
                    "isAutomaticSize": False,
                    "label": {
                        "canOverlapLabels": False,
                        "marksToLabel": {"type": "All"},
                        "showMarkLabels": True,
                    },
                    "range": {"reverse": True},
                    "size": {
                        "isAutomatic": False,
                        "type": "Pixel",
                        "value": int(overrides.get("map_point_size_px", 50)),
                    },
                },
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _flow_bar_marks_style_fill(fill: str, *, size_pct: int, reverse: bool = True) -> Dict[str, Any]:
    """Flow level bar style with explicit mark fill (matches New_Dashboard1_package exports)."""
    return {
        "color": {"color": fill},
        "isAutomaticSize": True,
        "label": {
            "canOverlapLabels": False,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": True,
        },
        "range": {"reverse": reverse},
        "size": {"isAutomatic": True, "type": "Percentage", "value": size_pct},
    }


def _flow_links_nodes_style(*, link_line_color: str = "", nodes_fill: str = "") -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Static style.marks.links and style.marks.nodes blocks."""
    links = {
        "color": {"color": link_line_color},
        "isAutomaticSize": True,
        "label": {
            "canOverlapLabels": False,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": True,
        },
        "range": {"reverse": True},
        "size": {"isAutomatic": True, "type": "Pixel", "value": 3},
    }
    nodes = {
        "color": {"color": nodes_fill},
        "isAutomaticSize": True,
        "label": {
            "canOverlapLabels": False,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": True,
        },
        "range": {"reverse": True},
        "size": {"isAutomatic": True, "type": "Percentage", "value": 75},
    }
    return links, nodes


def _build_viz_flow_package_minimal(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    """Measure-first F1=link, F2/F3=levels; empty encodings (Base_Flow / single-color shell)."""
    level1 = field_mappings["level1"]
    level2 = field_mappings["level2"]
    link_m = field_mappings["link_measure"]
    fill = overrides.get("flow_uniform_fill", "")
    fields: Dict[str, Any] = {
        "F1": _sdm_field_to_viz_field(link_m),
        "F2": _sdm_field_to_viz_field(level1),
        "F3": _sdm_field_to_viz_field(level2),
    }
    bar_stack = {"isAutomatic": True, "isStacked": False}
    bar_none: List[dict] = []
    links_st, nodes_st = _flow_links_nodes_style(link_line_color="", nodes_fill=fill)
    fmt = _infer_format_type(fields["F1"])
    visual_spec: Dict[str, Any] = {
        "layout": "Flow",
        "legends": {},
        "levels": ["F2", "F3"],
        "link": "F1",
        "marks": {
            "fields": {
                "F2": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
                "F3": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
            },
            "links": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Line"},
            "nodes": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
        },
        "style": {
            "encodings": {"fields": {"F1": _encoding_field_entry(fmt)}},
            "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {
                    "F2": _flow_bar_marks_style_fill(fill, size_pct=75),
                    "F3": _flow_bar_marks_style_fill(fill, size_pct=75),
                },
                "links": links_st,
                "nodes": nodes_st,
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_flow_package_link_nodes_color(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    """Copy_of_Base_Flow_*: link Color(dup measure), nodes Color(dup level2); F4 defined (fixes broken export)."""
    level1 = field_mappings["level1"]
    level2 = field_mappings["level2"]
    link_m = field_mappings["link_measure"]
    fill = overrides.get("flow_uniform_fill", "#F9E3B6")
    fields: Dict[str, Any] = {
        "F1": _sdm_field_to_viz_field(link_m),
        "F2": _sdm_field_to_viz_field(level1),
        "F3": _sdm_field_to_viz_field(level2),
        "F4": copy.deepcopy(_sdm_field_to_viz_field(level2)),
        "F5": copy.deepcopy(_sdm_field_to_viz_field(link_m)),
    }
    fmt = _infer_format_type(fields["F1"])
    enc_f: Dict[str, Any] = {
        "F1": _encoding_field_entry(fmt),
        "F5": _encoding_field_entry(fmt),
    }
    leg_vis = overrides.get("flow_dup_measure_legend_visible", False)
    legends = {
        "F5": {
            "isVisible": leg_vis,
            "position": "Right",
            "title": {"isVisible": True},
        },
    }
    bar_stack = {"isAutomatic": True, "isStacked": False}
    bar_none: List[dict] = []
    links_st, nodes_st = _flow_links_nodes_style(link_line_color="", nodes_fill=fill)
    visual_spec: Dict[str, Any] = {
        "layout": "Flow",
        "legends": legends,
        "levels": ["F2", "F3"],
        "link": "F1",
        "marks": {
            "fields": {
                "F2": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
                "F3": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
            },
            "links": {
                "encodings": [{"fieldKey": "F5", "type": "Color"}],
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Line",
            },
            "nodes": {
                "encodings": [{"fieldKey": "F4", "type": "Color"}],
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Bar",
            },
        },
        "style": {
            "encodings": {"fields": enc_f},
            "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {
                    "F2": _flow_bar_marks_style_fill(fill, size_pct=75),
                    "F3": _flow_bar_marks_style_fill(fill, size_pct=75),
                },
                "links": links_st,
                "nodes": {
                    **nodes_st,
                    "color": {"color": fill},
                    "size": {"isAutomatic": True, "type": "Percentage", "value": 100},
                },
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_flow_package_colors_variations(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    """Base_Flow_colors_variations_measure_on_marks: F2 Color(F6 dup L1), links F5, nodes F4 dup L2."""
    level1 = field_mappings["level1"]
    level2 = field_mappings["level2"]
    link_m = field_mappings["link_measure"]
    fill_bars = overrides.get("flow_uniform_fill", "#F9E3B6")
    fields: Dict[str, Any] = {
        "F1": _sdm_field_to_viz_field(link_m),
        "F2": _sdm_field_to_viz_field(level1),
        "F3": _sdm_field_to_viz_field(level2),
        "F4": copy.deepcopy(_sdm_field_to_viz_field(level2)),
        "F5": copy.deepcopy(_sdm_field_to_viz_field(link_m)),
        "F6": copy.deepcopy(_sdm_field_to_viz_field(level1)),
    }
    fmt = _infer_format_type(fields["F1"])
    fmt_f5 = _infer_format_type(fields["F5"])
    enc_f: Dict[str, Any] = {
        "F1": _encoding_field_entry(fmt),
        "F5": _encoding_field_entry(fmt_f5),
    }
    hide = overrides.get("flow_package_hide_color_legends", True)
    legends = {
        "F5": {
            "isVisible": not hide,
            "position": "Right",
            "title": {"isVisible": True},
        },
        "F6": {
            "isVisible": not hide,
            "position": "Right",
            "title": {"isVisible": True},
        },
    }
    bar_stack = {"isAutomatic": True, "isStacked": False}
    bar_none: List[dict] = []
    links_st, nodes_st = _flow_links_nodes_style(link_line_color="", nodes_fill=fill_bars)
    visual_spec: Dict[str, Any] = {
        "layout": "Flow",
        "legends": legends,
        "levels": ["F2", "F3"],
        "link": "F1",
        "marks": {
            "fields": {
                "F2": {
                    "encodings": [{"fieldKey": "F6", "type": "Color"}],
                    "isAutomatic": True,
                    "stack": bar_stack,
                    "type": "Bar",
                },
                "F3": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
            },
            "links": {
                "encodings": [{"fieldKey": "F5", "type": "Color"}],
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Line",
            },
            "nodes": {
                "encodings": [{"fieldKey": "F4", "type": "Color"}],
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Bar",
            },
        },
        "style": {
            "encodings": {"fields": enc_f},
            "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {
                    "F2": _flow_bar_marks_style_fill(fill_bars, size_pct=100),
                    "F3": _flow_bar_marks_style_fill(fill_bars, size_pct=75),
                },
                "links": links_st,
                "nodes": {
                    **nodes_st,
                    "color": {"color": fill_bars},
                    "size": {"isAutomatic": True, "type": "Percentage", "value": 100},
                },
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_flow_package_three_level(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    """Three dimensions on flow; link measure F1; link Color via duplicate measure F5 (marks1 export)."""
    level1 = field_mappings["level1"]
    level2 = field_mappings["level2"]
    level3 = field_mappings["level3"]
    link_m = field_mappings["link_measure"]
    fill = overrides.get("flow_uniform_fill", "")
    fields: Dict[str, Any] = {
        "F1": _sdm_field_to_viz_field(link_m),
        "F2": _sdm_field_to_viz_field(level1),
        "F3": _sdm_field_to_viz_field(level2),
        "F4": _sdm_field_to_viz_field(level3),
        "F5": copy.deepcopy(_sdm_field_to_viz_field(link_m)),
    }
    fmt = _infer_format_type(fields["F1"])
    enc_f: Dict[str, Any] = {
        "F1": _encoding_field_entry(fmt),
        "F5": _encoding_field_entry(fmt),
    }
    use_palette = overrides.get("flow_link_color_continuous_palette", False)
    if use_palette:
        enc_f["F5"] = {**enc_f["F5"], "colors": _soft_blue_continuous_palette()}
    link_leg = overrides.get("flow_link_legend_visible", False)
    legends = {
        "F5": {
            "isVisible": link_leg,
            "position": "Right",
            "title": {"isVisible": True},
        },
    }
    bar_stack = {"isAutomatic": True, "isStacked": False}
    bar_none: List[dict] = []
    links_st, nodes_st = _flow_links_nodes_style(link_line_color="", nodes_fill=fill)
    visual_spec: Dict[str, Any] = {
        "layout": "Flow",
        "legends": legends,
        "levels": ["F2", "F3", "F4"],
        "link": "F1",
        "marks": {
            "fields": {
                "F2": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
                "F3": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
                "F4": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
            },
            "links": {
                "encodings": [{"fieldKey": "F5", "type": "Color"}],
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Line",
            },
            "nodes": {"encodings": bar_none, "isAutomatic": True, "stack": bar_stack, "type": "Bar"},
        },
        "style": {
            "encodings": {"fields": enc_f},
            "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {
                    "F2": _flow_bar_marks_style_fill(fill, size_pct=75),
                    "F3": _flow_bar_marks_style_fill(fill, size_pct=75),
                    "F4": _flow_bar_marks_style_fill(fill, size_pct=75),
                },
                "links": links_st,
                "nodes": nodes_st,
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_flow_simple(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    """Flow with F1–F3 only: fixed bar/link colors, no Color/Size encodings (Base_Flow-style)."""
    level1 = field_mappings["level1"]
    level2 = field_mappings["level2"]
    link_m = field_mappings["link_measure"]
    fields: Dict[str, Any] = {
        "F1": _sdm_field_to_viz_field(level1),
        "F2": _sdm_field_to_viz_field(level2),
        "F3": _sdm_field_to_viz_field(link_m),
    }
    bar_stack = {"isAutomatic": True, "isStacked": False}
    bar_enc_none: List[dict] = []
    visual_spec: Dict[str, Any] = {
        "layout": "Flow",
        "legends": {},
        "levels": ["F1", "F2"],
        "link": "F3",
        "marks": {
            "fields": {
                "F1": {
                    "encodings": bar_enc_none,
                    "isAutomatic": True,
                    "stack": bar_stack,
                    "type": "Bar",
                },
                "F2": {
                    "encodings": bar_enc_none,
                    "isAutomatic": True,
                    "stack": bar_stack,
                    "type": "Bar",
                },
            },
            "links": {
                "encodings": bar_enc_none,
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Line",
            },
            "nodes": {
                "encodings": bar_enc_none,
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Bar",
            },
        },
        "style": {
            "encodings": {"fields": {}},
            "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {
                    "F1": _flow_level_bar_marks_style(size_pct=75),
                    "F2": _flow_level_bar_marks_style(size_pct=100),
                },
                "links": {
                    "color": {"color": ""},
                    "isAutomaticSize": True,
                    "label": {
                        "canOverlapLabels": False,
                        "marksToLabel": {"type": "All"},
                        "showMarkLabels": True,
                    },
                    "range": {"reverse": True},
                    "size": {"isAutomatic": True, "type": "Pixel", "value": 3},
                },
                "nodes": {
                    "color": {"color": ""},
                    "isAutomaticSize": True,
                    "label": {
                        "canOverlapLabels": False,
                        "marksToLabel": {"type": "All"},
                        "showMarkLabels": True,
                    },
                    "range": {"reverse": True},
                    "size": {"isAutomatic": True, "type": "Percentage", "value": 75},
                },
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_flow_simple_measure_on_marks(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    """Template alias for simple flow; API v66.12 rejects Size encoding on flow nodes."""
    return _build_viz_flow_simple(
        sdm_name,
        sdm_label,
        workspace_name,
        workspace_label,
        field_mappings,
        name,
        label,
        overrides,
    )


def _build_viz_flow_colors(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    level1 = field_mappings["level1"]
    level2 = field_mappings["level2"]
    link_m = field_mappings["link_measure"]
    link_color_src = field_mappings.get("link_color_measure") or link_m
    level2_color_src = field_mappings.get("level2_color_dim") or level2

    fields: Dict[str, Any] = {
        "F1": _sdm_field_to_viz_field(level1),
        "F2": _sdm_field_to_viz_field(level2),
        "F3": _sdm_field_to_viz_field(link_m),
        "F4": copy.deepcopy(_sdm_field_to_viz_field(link_color_src)),
        "F5": copy.deepcopy(_sdm_field_to_viz_field(level2_color_src)),
    }
    fmt_link = _infer_format_type(fields["F3"])
    enc_f: Dict[str, Any] = {
        "F3": _encoding_field_entry(fmt_link),
        "F4": {**_encoding_field_entry(fmt_link), "colors": _soft_blue_continuous_palette()},
    }
    link_leg_vis = overrides.get("flow_link_legend_visible", True)
    legends = {
        "F4": {
            "isVisible": link_leg_vis,
            "position": "Right",
            "title": {"isVisible": True},
        },
        "F5": {"isVisible": True, "position": "Right", "title": {"isVisible": True}},
    }
    bar_stack = {"isAutomatic": True, "isStacked": False}
    bar_enc_none: List[dict] = []
    visual_spec: Dict[str, Any] = {
        "layout": "Flow",
        "legends": legends,
        "levels": ["F1", "F2"],
        "link": "F3",
        "marks": {
            "fields": {
                "F1": {
                    "encodings": bar_enc_none,
                    "isAutomatic": True,
                    "stack": bar_stack,
                    "type": "Bar",
                },
                "F2": {
                    "encodings": [{"fieldKey": "F5", "type": "Color"}],
                    "isAutomatic": True,
                    "stack": bar_stack,
                    "type": "Bar",
                },
            },
            "links": {
                "encodings": [{"fieldKey": "F4", "type": "Color"}],
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Line",
            },
            "nodes": {
                "encodings": bar_enc_none,
                "isAutomatic": True,
                "stack": bar_stack,
                "type": "Bar",
            },
        },
        "style": {
            "encodings": {"fields": enc_f},
            "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
            "fonts": sd.build_fonts(overrides),
            "lines": sd.build_lines(overrides),
            "marks": {
                "fields": {
                    "F1": _flow_level_bar_marks_style(size_pct=75),
                    "F2": _flow_level_bar_marks_style(size_pct=100),
                },
                "links": {
                    "color": {"color": ""},
                    "isAutomaticSize": True,
                    "label": {
                        "canOverlapLabels": False,
                        "marksToLabel": {"type": "All"},
                        "showMarkLabels": True,
                    },
                    "range": {"reverse": True},
                    "size": {"isAutomatic": True, "type": "Pixel", "value": 3},
                },
                "nodes": {
                    "color": {"color": ""},
                    "isAutomaticSize": True,
                    "label": {
                        "canOverlapLabels": False,
                        "marksToLabel": {"type": "All"},
                        "showMarkLabels": True,
                    },
                    "range": {"reverse": True},
                    "size": {"isAutomatic": True, "type": "Percentage", "value": 75},
                },
            },
            "shading": sd.build_shading(overrides, with_banding=True),
            "title": {"isVisible": True},
        },
    }
    return build_root_envelope(
        name=name,
        label=label,
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=workspace_name,
        workspace_label=workspace_label,
        fields=fields,
        visual_spec=visual_spec,
        sort_orders={"columns": [], "fields": {}, "rows": []},
    )


def _build_viz_flow_colors_measure_on_marks(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
) -> dict:
    """Template alias for full-color flow; API v66.12 rejects Size encoding on flow nodes."""
    return _build_viz_flow_colors(
        sdm_name,
        sdm_label,
        workspace_name,
        workspace_label,
        field_mappings,
        name,
        label,
        overrides,
    )


def _build_viz_flow(
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],
    name: str,
    label: str,
    overrides: Dict[str, Any],
    *,
    flow_mode: str = "colors",
) -> dict:
    if flow_mode == "simple":
        return _build_viz_flow_simple(
            sdm_name,
            sdm_label,
            workspace_name,
            workspace_label,
            field_mappings,
            name,
            label,
            overrides,
        )
    if flow_mode == "simple_measure_on_marks":
        return _build_viz_flow_simple_measure_on_marks(
            sdm_name,
            sdm_label,
            workspace_name,
            workspace_label,
            field_mappings,
            name,
            label,
            overrides,
        )
    if flow_mode == "colors_measure_on_marks":
        return _build_viz_flow_colors_measure_on_marks(
            sdm_name,
            sdm_label,
            workspace_name,
            workspace_label,
            field_mappings,
            name,
            label,
            overrides,
        )
    if flow_mode == "package_minimal":
        return _build_viz_flow_package_minimal(
            sdm_name,
            sdm_label,
            workspace_name,
            workspace_label,
            field_mappings,
            name,
            label,
            overrides,
        )
    if flow_mode == "package_link_nodes_color":
        return _build_viz_flow_package_link_nodes_color(
            sdm_name,
            sdm_label,
            workspace_name,
            workspace_label,
            field_mappings,
            name,
            label,
            overrides,
        )
    if flow_mode == "package_colors_variations":
        return _build_viz_flow_package_colors_variations(
            sdm_name,
            sdm_label,
            workspace_name,
            workspace_label,
            field_mappings,
            name,
            label,
            overrides,
        )
    if flow_mode == "package_three_level":
        return _build_viz_flow_package_three_level(
            sdm_name,
            sdm_label,
            workspace_name,
            workspace_label,
            field_mappings,
            name,
            label,
            overrides,
        )
    return _build_viz_flow_colors(
        sdm_name,
        sdm_label,
        workspace_name,
        workspace_label,
        field_mappings,
        name,
        label,
        overrides,
    )


# ---------------------------------------------------------------------------
# Root envelope
# ---------------------------------------------------------------------------

def _top_n_view_specification_fragment(
    *,
    filter_dimension_fkey: str,
    dimension_object_name: str,
    dimension_field_name: str,
    measure_object_name: str,
    measure_field_name: str,
    rank_aggregation: str,
    limit: int,
    is_top: bool,
) -> Dict[str, Any]:
    """viewSpecification extras for Top / Bottom N (AdvancedDimension + topBottomCriteria).

    Live API expects ``topBottomCriteria.expression`` on the *measure*, e.g.
    ``SUM([Order].[total_amount])``, not ``COUNT`` on the dimension (invalid reference).
    """
    dim_model = f"{dimension_object_name}.{dimension_field_name}"
    bracket_m = f"[{measure_object_name}].[{measure_field_name}]"
    expression = f"{rank_aggregation}({bracket_m})"
    return {
        "advancedDimensionFilters": [
            {
                "fieldKeys": [filter_dimension_fkey],
                "filter": {
                    "fields": [{"model": dim_model}],
                    "operator": "AdvancedDimension",
                    "topBottomCriteria": {
                        "expression": expression,
                        "isTop": is_top,
                        "topBottomLimit": limit,
                    },
                    "values": [],
                },
            }
        ],
        "filter": {
            "filters": [
                {
                    "fieldKeys": [filter_dimension_fkey],
                    "filter": {
                        "fields": [{"model": dim_model}],
                        "includeNulls": False,
                        "operator": "In",
                        "values": [],
                    },
                    "includeAllValues": True,
                },
                {
                    "fieldKeys": [filter_dimension_fkey],
                    "filter": {
                        "fields": [{"model": dim_model}],
                        "operator": "ContainsIgnoreCase",
                        "values": [""],
                    },
                    "includeAllValues": True,
                },
            ]
        },
    }


def _normalize_view_sort_orders(sort_orders: Optional[dict]) -> dict:
    """Ensure sortOrders.fields entries include polymorphic type (v66.12 BaseVisualizationSortInputRepresentation)."""
    base = sort_orders or {"columns": [], "fields": {}, "rows": []}
    out = copy.deepcopy(base)
    for _fk, cfg in list(out.get("fields", {}).items()):
        if isinstance(cfg, dict) and "type" not in cfg:
            cfg["type"] = "Field"
    return out


def build_root_envelope(
    name: str,
    label: str,
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    fields: Dict[str, dict],
    visual_spec: dict,
    sort_orders: Optional[dict] = None,
    view_specification_extras: Optional[Dict[str, Any]] = None,
) -> dict:
    """Wrap a visualSpecification in the required root structure."""
    layout = visual_spec.get("layout", "Vizql")
    view_specification: Dict[str, Any] = {
        "sortOrders": _normalize_view_sort_orders(sort_orders),
    }
    # API v66.12: legacy top-level viewSpecification.filters is rejected; use unified filter.filters.
    # Flow posts successfully without a filter block; other layouts use empty nested filters.
    if layout != "Flow":
        view_specification["filter"] = {"filters": []}
    if view_specification_extras:
        view_specification.update(view_specification_extras)
    return {
        "name": name,
        "label": label,
        "dataSource": {"name": sdm_name, "label": sdm_label, "type": "SemanticModel"},
        "workspace": {"name": workspace_name, "label": workspace_label},
        "interactions": [],
        "fields": fields,
        "visualSpecification": visual_spec,
        "view": {
            "label": "default",
            "name": f"{name}_default",
            "viewSpecification": view_specification,
        },
    }


def _maybe_hide_legends(
    envelope: Dict[str, Any], overrides: Dict[str, Any]
) -> Dict[str, Any]:
    """When ``hide_legends`` is set in overrides, turn off all chart legends."""
    if not overrides.get("hide_legends"):
        return envelope
    vs = envelope.get("visualSpecification")
    if not isinstance(vs, dict):
        return envelope
    legs = vs.get("legends")
    if not isinstance(legs, dict):
        return envelope
    for k, v in list(legs.items()):
        if isinstance(v, dict):
            nv = copy.deepcopy(v)
            nv["isVisible"] = False
            tit = nv.get("title")
            if isinstance(tit, dict):
                nv["title"] = {**copy.deepcopy(tit), "isVisible": False}
            legs[k] = nv
    vs["legends"] = legs
    return envelope


def build_viz_from_template_def(
    template_def: Dict[str, Any],
    sdm_name: str,
    sdm_label: str,
    workspace_name: str,
    workspace_label: str,
    field_mappings: Dict[str, Dict[str, Any]],  # Maps template field names to SDM fields
    name: str,
    label: str,
    overrides: Optional[Dict[str, Any]] = None,
) -> dict:
    """Build visualization from a template definition.
    
    Bridges high-level templates to low-level chart builders.
    
    Args:
        template_def: Template definition from viz_templates.py
        sdm_name: SDM API name
        sdm_label: SDM display label
        workspace_name: Workspace API name
        workspace_label: Workspace display label
        field_mappings: Dict mapping template field names to SDM field definitions
        name: Visualization API name
        label: Visualization display label
        overrides: Optional style overrides
        
    Returns:
        Complete visualization JSON payload
    """
    overrides = overrides or {}
    chart_type = template_def["chart_type"]
    
    # Merge template style overrides with user overrides
    template_style = template_def.get("style", {})
    if template_style:
        overrides = {**template_style, **overrides}

    if chart_type == "map":
        mode = template_def.get("map_build_mode", "standard")
        if mode == "location_only":
            return _maybe_hide_legends(
                _build_viz_map_location_only(
                    sdm_name,
                    sdm_label,
                    workspace_name,
                    workspace_label,
                    field_mappings,
                    name,
                    label,
                    overrides,
                ),
                overrides,
            )
        if mode == "advanced":
            return _maybe_hide_legends(
                _build_viz_map_advanced(
                    sdm_name,
                    sdm_label,
                    workspace_name,
                    workspace_label,
                    field_mappings,
                    name,
                    label,
                    overrides,
                ),
                overrides,
            )
        return _maybe_hide_legends(
            _build_viz_map(
                sdm_name,
                sdm_label,
                workspace_name,
                workspace_label,
                field_mappings,
                name,
                label,
                overrides,
            ),
            overrides,
        )
    if chart_type == "flow":
        flow_mode = template_def.get("flow_build_mode", "colors")
        return _maybe_hide_legends(
            _build_viz_flow(
                sdm_name,
                sdm_label,
                workspace_name,
                workspace_label,
                field_mappings,
                name,
                label,
                overrides,
                flow_mode=flow_mode,
            ),
            overrides,
        )

    # Build fields dict (F1, F2, etc.) in order of field_mapping
    fields: Dict[str, dict] = {}
    field_counter = 1
    
    # Get ordered list of fields from field_mapping
    all_template_fields = template_def["field_mapping"].get("columns", []) + template_def["field_mapping"].get("rows", [])
    
    # Handle date_functions (for Year+Month hierarchy) - map template field names to actual SDM date field
    date_functions = template_def.get("date_functions", {})
    if template_def.get("date_function") and not date_functions:
        # Backward compatibility: single date_function maps to "date" field
        date_functions = {"date": template_def["date_function"]}
    
    # Map template field names to F keys
    template_to_fkey: Dict[str, str] = {}
    for template_field_name in all_template_fields:
        # Check if this is a date hierarchy field (date_year, date_month) that maps to same SDM field
        actual_sdm_field_name = template_field_name
        if template_field_name in date_functions:
            # This is a date hierarchy field - find the base date field from field_mappings
            # The base date field is mapped as "date" in template requirements
            if "date" in field_mappings:
                actual_sdm_field_name = "date"
            else:
                # Try to find any date field in field_mappings
                date_fields = [k for k in field_mappings.keys() if "date" in k.lower()]
                if date_fields:
                    actual_sdm_field_name = date_fields[0]
                else:
                    # If no date field found, skip this template field
                    continue
        
        if actual_sdm_field_name in field_mappings:
            field_key = f"F{field_counter}"
            template_to_fkey[template_field_name] = field_key
            
            sdm_field = field_mappings[actual_sdm_field_name]
            field_def: Dict[str, Any] = {
                "type": "Field",
                "displayCategory": sdm_field.get("displayCategory", "Discrete" if sdm_field.get("role") == "Dimension" else "Continuous"),
                "role": sdm_field.get("role"),
                "fieldName": sdm_field.get("fieldName"),
                "objectName": sdm_field.get("objectName"),
                "function": sdm_field.get("function"),
            }
            
            # Apply aggregation type override for measures (e.g., Probability → Avg)
            if field_def.get("role") == "Measure":
                # CRITICAL: Never override UserAgg for CLC fields
                if field_def.get("function") == "UserAgg" or sdm_field.get("aggregationType") == "UserAgg":
                    # Preserve UserAgg - don't override
                    field_def["function"] = "UserAgg"
                else:
                    inferred_agg = _infer_aggregation_type(field_def)
                    if inferred_agg:
                        field_def["function"] = inferred_agg
                    elif not field_def.get("function"):
                        # Use default from SDM field if available
                        field_def["function"] = sdm_field.get("aggregationType", "Sum")
            
            # Apply date function if specified (for Year+Month hierarchy)
            if template_field_name in date_functions:
                field_def["function"] = date_functions[template_field_name]
            elif template_def.get("date_function") and "date" in template_field_name.lower():
                # Backward compatibility
                field_def["function"] = template_def["date_function"]
            
            fields[field_key] = field_def
            field_counter += 1
    
    # Map template field references to F1/F2/F3
    columns = [template_to_fkey[f] for f in template_def["field_mapping"].get("columns", []) if f in template_to_fkey]
    rows = [template_to_fkey[f] for f in template_def["field_mapping"].get("rows", []) if f in template_to_fkey]
    
    # Check for fields that need to be duplicated (on shelves AND in encodings)
    shelf_template_fields = set(template_def["field_mapping"].get("columns", []) + template_def["field_mapping"].get("rows", []))
    encoding_template_fields = {enc_def["field"] for enc_def in template_def.get("encodings", [])}
    fields_to_duplicate = shelf_template_fields & encoding_template_fields
    
    # Create duplicate field definitions for encoding-only use
    encoding_field_map: Dict[str, str] = {}  # Maps template field name to encoding field key
    for template_field_name in fields_to_duplicate:
        if template_field_name in template_to_fkey:
            shelf_key = template_to_fkey[template_field_name]
            # Create duplicate field for encoding (same SDM field, different F key)
            encoding_key = f"F{field_counter}"
            field_counter += 1
            # Copy field definition from shelf field
            fields[encoding_key] = fields[shelf_key].copy()
            encoding_field_map[template_field_name] = encoding_key
    
    # Build encodings
    # First, collect all encoding fields that aren't on shelves
    encoding_only_fields = set()
    for enc_def in template_def.get("encodings", []):
        template_field_name = enc_def["field"]
        if template_field_name not in shelf_template_fields:
            encoding_only_fields.add(template_field_name)
    
    # Add encoding-only fields to fields dict (e.g., category for scatter plots)
    for template_field_name in encoding_only_fields:
        if template_field_name in field_mappings and template_field_name not in template_to_fkey:
            field_key = f"F{field_counter}"
            template_to_fkey[template_field_name] = field_key
            field_counter += 1
            
            sdm_field = field_mappings[template_field_name]
            field_def: Dict[str, Any] = {
                "type": "Field",
                "displayCategory": sdm_field.get("displayCategory", "Discrete" if sdm_field.get("role") == "Dimension" else "Continuous"),
                "role": sdm_field.get("role"),
                "fieldName": sdm_field.get("fieldName"),
                "objectName": sdm_field.get("objectName"),
                "function": sdm_field.get("function"),
            }
            fields[field_key] = field_def
    
    # Handle measure_values fields (for bar_multi_measure) - add to fields dict
    # These fields are required but not in field_mapping or encodings
    measure_values_template_fields = template_def.get("measure_values", [])
    for template_field_name in measure_values_template_fields:
        if template_field_name in field_mappings and template_field_name not in template_to_fkey:
            field_key = f"F{field_counter}"
            template_to_fkey[template_field_name] = field_key
            field_counter += 1
            
            sdm_field = field_mappings[template_field_name]
            field_def: Dict[str, Any] = {
                "type": "Field",
                "displayCategory": sdm_field.get("displayCategory", "Continuous"),
                "role": sdm_field.get("role", "Measure"),
                "fieldName": sdm_field.get("fieldName"),
                "objectName": sdm_field.get("objectName"),
                "function": sdm_field.get("function") or sdm_field.get("aggregationType", "Sum"),
            }
            # Apply aggregation type override for measures
            if field_def.get("role") == "Measure":
                # CRITICAL: Never override UserAgg for CLC fields
                if field_def.get("function") == "UserAgg" or sdm_field.get("aggregationType") == "UserAgg":
                    field_def["function"] = "UserAgg"
                else:
                    inferred_agg = _infer_aggregation_type(field_def)
                    if inferred_agg:
                        field_def["function"] = inferred_agg
            fields[field_key] = field_def
    
    # Handle optional_fields (e.g., color_dim) - add to encodings and legends if provided
    optional_fields = template_def.get("optional_fields", {})
    for optional_field_name, optional_field_def in optional_fields.items():
        if optional_field_name in field_mappings and optional_field_name not in template_to_fkey:
            # Optional field provided - add it
            field_key = f"F{field_counter}"
            template_to_fkey[optional_field_name] = field_key
            field_counter += 1
            
            sdm_field = field_mappings[optional_field_name]
            field_def: Dict[str, Any] = {
                "type": "Field",
                "displayCategory": sdm_field.get("displayCategory", "Discrete" if sdm_field.get("role") == "Dimension" else "Continuous"),
                "role": sdm_field.get("role"),
                "fieldName": sdm_field.get("fieldName"),
                "objectName": sdm_field.get("objectName"),
                "function": sdm_field.get("function"),
            }
            fields[field_key] = field_def
    
    # Build encodings from template definition
    encodings: List[dict] = []
    for enc_def in template_def.get("encodings", []):
        template_field_name = enc_def["field"]
        # Use encoding-specific field key if duplicated, otherwise use shelf key, or encoding-only key
        if template_field_name in encoding_field_map:
            field_key = encoding_field_map[template_field_name]
        elif template_field_name in template_to_fkey:
            field_key = template_to_fkey[template_field_name]
        else:
            if not enc_def.get("optional", False):
                # Required encoding field not found - skip silently for now
                pass
            continue
        
        encodings.append({
            "fieldKey": field_key,
            "type": enc_def["type"]
        })
    
    # Build legends from template definition
    legends: Dict[str, dict] = {}
    template_legends = template_def.get("legends", {})
    for legend_field_name, legend_config in template_legends.items():
        # Find the field key for this legend field
        if legend_field_name in template_to_fkey:
            field_key = template_to_fkey[legend_field_name]
        elif legend_field_name in encoding_field_map:
            field_key = encoding_field_map[legend_field_name]
        else:
            # Try to find encoding-only field
            continue
        
        legends[field_key] = legend_config
    
    # Add Color encoding for optional color_dim fields (test harness pattern)
    # This must happen after encodings are built so we can append to the list
    for optional_field_name in optional_fields.keys():
        if optional_field_name in field_mappings and optional_field_name == "color_dim":
            if optional_field_name in template_to_fkey:
                field_key = template_to_fkey[optional_field_name]
                # Add Color encoding if not already present
                has_color_encoding = any(e.get("fieldKey") == field_key and e.get("type") == "Color" for e in encodings)
                if not has_color_encoding:
                    encodings.append({
                        "fieldKey": field_key,
                        "type": "Color"
                    })
                    # Add legend configuration (test harness pattern)
                    legends[field_key] = {"isVisible": True, "position": "Right", "title": {"isVisible": True}}
    
    # Add Size encoding for optional size_measure fields (test harness pattern for heatmaps)
    # If size_measure not provided, use main measure (test harness duplicates measure for Size)
    # Check if Size encoding already exists (from template definition)
    has_size_encoding = any(e.get("type") == "Size" for e in encodings)
    if not has_size_encoding:
        for optional_field_name in optional_fields.keys():
            if optional_field_name == "size_measure":
                if optional_field_name in field_mappings and optional_field_name in template_to_fkey:
                    # size_measure provided - use it
                    field_key = template_to_fkey[optional_field_name]
                else:
                    # size_measure not provided - use main measure (test harness pattern)
                    # Find the main measure field key (first measure in field_mappings)
                    main_measure_key = None
                    for template_field_name, fkey in template_to_fkey.items():
                        if template_field_name in field_mappings:
                            sdm_field = field_mappings[template_field_name]
                            if sdm_field.get("role") == "Measure" and template_field_name == "measure":
                                main_measure_key = fkey
                                break
                    if main_measure_key:
                        field_key = main_measure_key
                    else:
                        continue  # No measure found, skip Size encoding
                
                # Add Size encoding
                encodings.append({
                    "fieldKey": field_key,
                    "type": "Size"
                })
                break  # Only add one Size encoding
    
    # Build sort orders if specified (support both "sort" and "sort_orders" formats)
    sort_orders: Optional[dict] = None
    if "sort_orders" in template_def:
        # New format: sort_orders dict with fields structure
        template_sort_orders = template_def["sort_orders"]
        sort_orders = {
            "columns": template_sort_orders.get("columns", []),
            "rows": template_sort_orders.get("rows", []),
            "fields": {}
        }
        # Map template field names to field keys
        for template_field_name, sort_config in template_sort_orders.get("fields", {}).items():
            if template_field_name in template_to_fkey:
                field_key = template_to_fkey[template_field_name]
                # Handle both simple format and nested format
                if isinstance(sort_config, dict):
                    sort_orders["fields"][field_key] = sort_config.copy()
                    # Map byField template name to field key if present
                    if "byField" in sort_config:
                        by_field_name = sort_config["byField"]
                        # First try template field name mapping
                        if by_field_name in template_to_fkey:
                            sort_orders["fields"][field_key]["byField"] = template_to_fkey[by_field_name]
                        elif by_field_name in field_mappings:
                            # byField might be a measure field name - find its key in fields dict
                            for fk, fdef in fields.items():
                                if fdef.get("fieldName") == field_mappings[by_field_name].get("fieldName"):
                                    sort_orders["fields"][field_key]["byField"] = fk
                                    break
                        else:
                            # Try to find by SDM field name directly
                            for fk, fdef in fields.items():
                                if fdef.get("fieldName") == by_field_name:
                                    sort_orders["fields"][field_key]["byField"] = fk
                                    break
                else:
                    # Simple format: just order string
                    sort_orders["fields"][field_key] = {"order": sort_config}
    elif "sort" in template_def:
        # Legacy format: simple sort specification
        sort_field_name = template_def["sort"]["field"]
        if sort_field_name in template_to_fkey:
            sort_field_key = template_to_fkey[sort_field_name]
            sort_orders = {
                "columns": [],
                "fields": {
                    sort_field_key: {
                        "order": "Descending" if template_def["sort"].get("descending", False) else "Ascending"
                    }
                },
                "rows": []
            }
    
    # Top N: extra dimension field key + viewSpecification (advancedDimensionFilters + filter)
    view_specification_extras: Optional[Dict[str, Any]] = None
    top_n_cfg = template_def.get("top_n")
    if top_n_cfg:
        dim_template = top_n_cfg.get("rank_dimension", "label_field")
        if dim_template in template_to_fkey and dim_template in field_mappings:
            sdm_dim = field_mappings[dim_template]
            obj = (sdm_dim.get("objectName") or "").strip()
            fn = (sdm_dim.get("fieldName") or "").strip()
            if obj and fn:
                shelf_dim_fk = template_to_fkey[dim_template]
                limit = int(top_n_cfg.get("limit", 5))
                is_top = bool(top_n_cfg.get("is_top", True))
                rank_by_template = top_n_cfg.get("rank_by", "amount")
                rank_agg = str(top_n_cfg.get("rank_aggregation", "SUM")).strip().upper() or "SUM"
                measure_shell_fk = template_to_fkey.get(rank_by_template)
                sdm_meas = field_mappings.get(rank_by_template) if rank_by_template in field_mappings else None
                meas_obj = (sdm_meas.get("objectName") or "").strip() if sdm_meas else ""
                meas_fn = (sdm_meas.get("fieldName") or "").strip() if sdm_meas else ""
                if not meas_obj and meas_fn:
                    meas_obj = obj
                if measure_shell_fk and meas_obj and meas_fn:
                    filter_fk = f"F{field_counter}"
                    field_counter += 1
                    fields[filter_fk] = copy.deepcopy(fields[shelf_dim_fk])
                    # Extra measure copy (matches round-trip Top N payloads from the product UI).
                    measure_dup_fk = f"F{field_counter}"
                    field_counter += 1
                    fields[measure_dup_fk] = copy.deepcopy(fields[measure_shell_fk])
                    view_specification_extras = _top_n_view_specification_fragment(
                        filter_dimension_fkey=filter_fk,
                        dimension_object_name=obj,
                        dimension_field_name=fn,
                        measure_object_name=meas_obj,
                        measure_field_name=meas_fn,
                        rank_aggregation=rank_agg,
                        limit=limit,
                        is_top=is_top,
                    )
    
    # Extract discrete palette and customColors from overrides (for bar, line, donut, scatter, funnel)
    palette_cfg = overrides.get("palette", {})
    discrete_palette = None
    custom_colors = None
    if palette_cfg.get("type") == "discrete":
        if palette_cfg.get("colors"):
            discrete_palette = palette_cfg["colors"]
        if palette_cfg.get("customColors"):
            custom_colors = palette_cfg["customColors"]

    # Call appropriate chart builder
    # Extract measure_values from template if present (for bar_multi_measure)
    measure_values_list = None
    if "measure_values" in template_def:
        # Map template field names (measure_1, measure_2) to field keys (F1, F2, etc.)
        measure_values_list = []
        for template_field_name in template_def["measure_values"]:
            if template_field_name in template_to_fkey:
                measure_values_list.append(template_to_fkey[template_field_name])
    
    if chart_type == "bar":
        visual_spec = build_bar(fields, columns, rows, encodings, legends, overrides, sort_orders=sort_orders, measure_values=measure_values_list, palette=discrete_palette, custom_colors=custom_colors)
    elif chart_type == "line":
        visual_spec = build_line(fields, columns, rows, encodings, legends, overrides, palette=discrete_palette, custom_colors=custom_colors)
    elif chart_type == "donut":
        visual_spec = build_donut(fields, columns, rows, encodings, legends, overrides, sort_orders=sort_orders, palette=discrete_palette, custom_colors=custom_colors)
    elif chart_type == "scatter":
        visual_spec = build_scatter(fields, columns, rows, encodings, legends, overrides, palette=discrete_palette, custom_colors=custom_colors)
    elif chart_type == "table":
        visual_spec = build_table(fields, rows, overrides, columns=columns)
    elif chart_type == "funnel":
        visual_spec = build_funnel(fields, columns, rows, encodings, legends, overrides, sort_orders=sort_orders, palette=discrete_palette, custom_colors=custom_colors)
    elif chart_type == "heatmap":
        # Find color encoding field key (should be a measure)
        color_fk = None
        for e in encodings:
            if e.get("type") == "Color":
                color_fk = e.get("fieldKey")
                # Verify it's a measure field
                if color_fk and color_fk in fields and fields[color_fk].get("role") == "Measure":
                    break
                else:
                    color_fk = None
        # If no Color encoding found, look for measure fields in encodings
        if not color_fk:
            for e in encodings:
                fk = e.get("fieldKey")
                if fk and fk in fields and fields[fk].get("role") == "Measure":
                    color_fk = fk
                    break
        palette_cfg = overrides.get("palette", {})
        palette_start = palette_cfg.get("start", "#5867E8")
        palette_end = palette_cfg.get("end", "#FF906E")
        palette_middle = palette_cfg.get("middle")
        visual_spec = build_heatmap(
            fields, columns, rows, encodings, legends, overrides,
            color_field_key=color_fk,
            palette_start=palette_start,
            palette_end=palette_end,
            palette_middle=palette_middle,
        )
    elif chart_type == "dot_matrix":
        # Find size encoding field key
        size_fk = None
        for e in encodings:
            if e.get("type") == "Size":
                size_fk = e.get("fieldKey")
                break
        visual_spec = build_dot_matrix(fields, columns, rows, encodings, legends, overrides, size_field_key=size_fk)
    else:
        raise ValueError(f"Unknown chart type: {chart_type}")
    
    return _maybe_hide_legends(
        build_root_envelope(
            name=name,
            label=label,
            sdm_name=sdm_name,
            sdm_label=sdm_label,
            workspace_name=workspace_name,
            workspace_label=workspace_label,
            fields=fields,
            visual_spec=visual_spec,
            sort_orders=sort_orders,
            view_specification_extras=view_specification_extras,
        ),
        overrides,
    )


# ---------------------------------------------------------------------------
# Auto-populate axis / encoding / header style fields from field definitions
# ---------------------------------------------------------------------------

def _auto_style_fields(
    fields: Dict[str, dict],
    columns: List[str],
    rows: List[str],
    encodings: List[dict],
) -> tuple:
    """Derive ``axis_fields``, ``encoding_fields``, and ``header_fields``
    from the field definitions and shelf placement.

    Rules (from the Tableau Next API):
    - ``style.axis.fields``: measure fields on rows or columns
    - ``style.encodings.fields``: measure fields used in encodings
      (dimensions MUST NOT appear here)
    - ``style.headers.fields``: dimension fields on rows or columns
      (NOT color/detail-only dimensions)
    """
    axis_f: Dict[str, dict] = {}
    enc_f: Dict[str, dict] = {}
    hdr_f: Dict[str, dict] = {}

    shelf_keys = set(columns) | set(rows)
    encoding_keys = {e["fieldKey"] for e in encodings if "fieldKey" in e}

    date_functions = {"DatePartYear", "DatePartMonth", "DatePartQuarter", "DatePartDay"}

    for fk, fdef in fields.items():
        role = fdef.get("role", "Dimension")
        fn = fdef.get("function")
        # Date-part functions on dimensions do NOT make them measures
        is_measure = role == "Measure" or (fn is not None and fn not in date_functions and role != "Dimension")
        ftype = fdef.get("type", "Field")

        if is_measure:
            fmt = _infer_format_type(fdef)
            axis_fmt = _AXIS_FORMAT_MAP.get(fmt, "CurrencyShort")
            # Axis entry for measures on shelves
            if fk in shelf_keys:
                axis_f[fk] = _axis_field_entry(axis_fmt)
            # Encoding style entry for any measure referenced in encodings
            if fk in encoding_keys or fk in shelf_keys:
                enc_f[fk] = _encoding_field_entry(fmt)
            # MeasureValues / MeasureNames virtual fields also get entries
            if ftype in ("MeasureValues", "MeasureNames"):
                enc_f[fk] = _encoding_field_entry(fmt)
        else:
            # Header entry only for dimensions on shelves
            if fk in shelf_keys:
                hdr_f[fk] = _header_field_entry()
            # Dimensions MUST NOT appear in style.encodings.fields — the API
            # rejects them with "encodings can have only measure fields"

    return axis_f, enc_f, hdr_f


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_visualization_spec(
    visual_spec: dict,
    fields: Dict[str, dict],
    chart_type: str = "unknown",
) -> Tuple[bool, List[str]]:
    """Validate visualization specification before API submission.
    
    Checks for common errors that cause API failures:
    - Missing encoding styles for measures in encodings
    - Measures incorrectly in headers.fields
    - Missing required style entries
    
    Args:
        visual_spec: The visualSpecification dict
        fields: Field definitions dict
        chart_type: Chart type name for better error messages
        
    Returns:
        (is_valid, list_of_error_messages)
    """
    errors: List[str] = []
    
    # Get encodings from marks.panes
    panes = visual_spec.get("marks", {}).get("panes", {})
    encodings = panes.get("encodings", [])
    
    # Get encoding style fields
    encoding_fields = visual_spec.get("style", {}).get("encodings", {}).get("fields", {})
    
    # Check: All measures in encodings must have encoding style entries
    for enc in encodings:
        fk = enc.get("fieldKey")
        if fk and fk in fields:
            fdef = fields[fk]
            if fdef.get("role") == "Measure":
                if fk not in encoding_fields:
                    errors.append(
                        f"[{chart_type}] Missing encoding style for measure '{fk}' "
                        f"({fdef.get('fieldName', 'unknown')}). "
                        f"Measures in encodings require style.encodings.fields entries."
                    )
    
    # Check: Measures on rows/columns also need encoding styles (for bar/line charts)
    columns = visual_spec.get("columns", [])
    rows = visual_spec.get("rows", [])
    shelf_keys = set(columns) | set(rows)
    
    # Note: Fields CAN be on shelves AND in encodings - this is valid for the API
    # For example, a measure on rows can also have a Label encoding
    # The previous validation was incorrectly flagging this as an error
    
    for fk in shelf_keys:
        if fk in fields:
            fdef = fields[fk]
            if fdef.get("role") == "Measure":
                # For bar/line charts, measures on shelves need encoding styles
                mark_type = panes.get("type", "")
                if mark_type in ("Bar", "Line") and fk not in encoding_fields:
                    errors.append(
                        f"[{chart_type}] Missing encoding style for measure '{fk}' "
                        f"on {'columns' if fk in columns else 'rows'}. "
                        f"Measures on shelves require style.encodings.fields entries."
                    )
    
    # Check: headers.fields should only contain dimensions (especially for tables)
    header_fields = visual_spec.get("style", {}).get("headers", {}).get("fields", {})
    for fk in header_fields:
        if fk in fields:
            fdef = fields[fk]
            if fdef.get("role") == "Measure":
                errors.append(
                    f"[{chart_type}] Measure '{fk}' incorrectly in headers.fields. "
                    f"headers.fields can only contain dimensions on rows/columns."
                )
    
    # Check: Scatter charts need measures on both axes to have proper styles
    if panes.get("type") == "Circle" and len(columns) > 0 and len(rows) > 0:
        # Scatter chart - both axes can be measures
        axis_fields = visual_spec.get("style", {}).get("axis", {}).get("fields", {})
        for fk in columns + rows:
            if fk in fields:
                fdef = fields[fk]
                if fdef.get("role") == "Measure":
                    # Columns need axis style, rows need encoding style
                    if fk in columns and fk not in axis_fields and fk not in encoding_fields:
                        errors.append(
                            f"[{chart_type}] Scatter chart measure '{fk}' on columns "
                            f"needs axis or encoding style entry."
                        )
                    elif fk in rows and fk not in encoding_fields:
                        errors.append(
                            f"[{chart_type}] Scatter chart measure '{fk}' on rows "
                            f"needs encoding style entry."
                        )
    
    # Check: Donut charts must have Color(dimension) + Angle(measure) encodings
    if panes.get("type") == "Donut":
        encoding_types = {e.get("type"): e.get("fieldKey") for e in encodings if "fieldKey" in e}
        has_color_dim = False
        has_angle_measure = False
        
        for enc_type, fk in encoding_types.items():
            if enc_type == "Color" and fk in fields:
                fdef = fields[fk]
                if fdef.get("role") == "Dimension":
                    has_color_dim = True
            elif enc_type == "Angle" and fk in fields:
                fdef = fields[fk]
                if fdef.get("role") == "Measure":
                    has_angle_measure = True
        
        if not has_color_dim:
            errors.append(
                f"[{chart_type}] Donut charts require a Color encoding with a dimension field."
            )
        if not has_angle_measure:
            errors.append(
                f"[{chart_type}] Donut charts require an Angle encoding with a measure field."
            )
    
    return len(errors) == 0, errors


def validate_full_visualization(payload: dict) -> Tuple[bool, List[str]]:
    """Validate complete visualization payload (including root envelope).
    
    Args:
        payload: Complete visualization payload dict
        
    Returns:
        (is_valid, list_of_error_messages)
    """
    errors: List[str] = []
    
    # Extract components
    visual_spec = payload.get("visualSpecification", {})
    fields = payload.get("fields", {})
    
    # Determine chart type from marks.panes.type
    panes = visual_spec.get("marks", {}).get("panes", {})
    chart_type = panes.get("type", "unknown")
    
    # Validate visual spec
    is_valid, spec_errors = validate_visualization_spec(visual_spec, fields, chart_type)
    errors.extend(spec_errors)
    
    # Additional root-level validations
    if not payload.get("name"):
        errors.append("Missing required field: 'name'")
    if not payload.get("dataSource", {}).get("name"):
        errors.append("Missing required field: 'dataSource.name'")
    if not payload.get("workspace", {}).get("name"):
        errors.append("Missing required field: 'workspace.name'")
    
    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Dashboard builder
# ---------------------------------------------------------------------------

_DEFAULT_WIDGET_STYLE = {
    "backgroundColor": "#ffffff",
    "borderColor": "#cccccc",
    "borderEdges": [],
    "borderRadius": 0,
    "borderWidth": 1,
}


@dataclass
class FilterDef:
    """Definition for a filter (list) widget on a dashboard."""
    field_name: str
    object_name: Optional[str]  # None for calculated fields (_clc)
    data_type: str = "Text"
    label: str = ""
    selection_type: str = "multiple"


@dataclass
class MetricDef:
    """Definition for a metric widget on a dashboard."""
    metric_api_name: str
    sdm_api_name: str


@dataclass
class VizDef:
    """Definition for a visualization widget on a dashboard."""
    viz_api_name: str
    page_index: int = 0  # Which page this visualization should appear on (for multi-page dashboards)


@dataclass
class PageDef:
    """Definition for a dashboard page."""
    label: str
    name: str = ""


@dataclass
class ButtonDef:
    """Definition for a navigation button widget."""
    text: str
    target_page: str


@dataclass
class ContainerDef:
    """Definition for a container (grouping box) widget."""
    column: int = 0
    row: int = 0
    colspan: int = 48
    rowspan: int = 10
    navigate_to_page: Optional[str] = None
    border_color: str = "#cccccc"
    border_edges: Optional[List[str]] = None
    page_index: int = 0


def _generate_uuid() -> str:
    import uuid
    return str(uuid.uuid4())


def build_dashboard(
    name: str,
    label: str,
    workspace_name: str,
    title_text: str,
    viz_defs: List[VizDef],
    filter_defs: Optional[List[FilterDef]] = None,
    metric_defs: Optional[List[MetricDef]] = None,
    sdm_name: Optional[str] = None,
    column_count: int = 48,
    row_height: int = 20,
    overrides: Optional[Dict[str, Any]] = None,
    page_defs: Optional[List[PageDef]] = None,
    container_defs: Optional[List[ContainerDef]] = None,
) -> dict:
    """Build a complete dashboard JSON payload with auto-layout.

    Single-page (default, ``page_defs`` is None):
      Title -> Filters -> Metrics -> Vizzes

    Multi-page (``page_defs`` provided):
      Each page gets: title, nav buttons, filters.
      Page 0 gets metrics; vizzes are distributed across pages.
    """
    ov = overrides or {}
    bg = ov.get("backgroundColor", "#ffffff")
    widget_style = dict(_DEFAULT_WIDGET_STYLE)
    widget_style["backgroundColor"] = bg

    widgets: Dict[str, dict] = {}
    filters = filter_defs or []
    metrics = metric_defs or []
    containers = container_defs or []
    
    # Deduplicate filters to prevent using the same field twice
    if filters:
        filters = dp.deduplicate_filter_defs(filters)

    # --- Resolve pages ---
    if page_defs and len(page_defs) > 1:
        pages = []
        for pd in page_defs:
            pages.append(PageDef(label=pd.label, name=pd.name or _generate_uuid()))
    else:
        pages = None

    # --- Build shared widget definitions ---

    # Title
    title_key = "title"
    widgets[title_key] = {
        "actions": [],
        "name": title_key,
        "type": "text",
        "parameters": {
            "content": [
                {"attributes": {"bold": True, "size": "16px"}, "insert": title_text},
                {"attributes": {"align": "center"}, "insert": "\n"},
            ]
        },
    }

    # Filters
    filter_keys: List[str] = []
    for i, fd in enumerate(filters):
        fkey = f"filter_{i + 1}"
        filter_keys.append(fkey)
        widgets[fkey] = {
            "actions": [],
            "label": fd.label or fd.field_name.replace("_", " "),
            "name": fkey,
            "type": "filter",
            "source": {"name": sdm_name or ""},
            "parameters": {
                "filterOption": {
                    "dataType": fd.data_type,
                    "fieldName": fd.field_name,
                    "objectName": fd.object_name,
                    "selectionType": fd.selection_type,
                },
                "viewType": "list",
                "isLabelHidden": False,
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": dict(widget_style),
            },
        }

    # Metrics
    metric_keys: List[str] = []
    for i, md in enumerate(metrics):
        mkey = f"metric_{i + 1}"
        metric_keys.append(mkey)
        widgets[mkey] = {
            "actions": [],
            "name": mkey,
            "type": "metric",
            "source": {"name": md.metric_api_name},
            "parameters": {
                "metricOption": {
                    "sdmApiName": md.sdm_api_name,
                    "layout": {
                        "componentVisibility": {
                            "chart": True, "value": True, "title": True,
                            "details": True, "comparison": True, "insights": False,
                        },
                    },
                },
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
                "widgetStyle": dict(widget_style),
            },
        }

    # Visualizations
    viz_keys: List[str] = []
    for i, vd in enumerate(viz_defs):
        vkey = f"viz_{i + 1}"
        viz_keys.append(vkey)
        widgets[vkey] = {
            "actions": [],
            "name": vkey,
            "type": "visualization",
            "source": {"name": vd.viz_api_name},
            "parameters": {
                "legendPosition": "Right",
                "receiveFilterSource": {"filterMode": "all", "widgetIds": []},
            },
        }

    # Containers
    container_keys: List[str] = []
    for i, cd in enumerate(containers):
        ckey = f"container_{i + 1}"
        container_keys.append(ckey)
        actions: List[dict] = []
        if cd.navigate_to_page:
            actions.append({
                "actionType": "navigate",
                "eventType": "click",
                "parameters": {
                    "destination": {"target": cd.navigate_to_page, "type": "page"},
                },
            })
        widgets[ckey] = {
            "actions": actions,
            "name": ckey,
            "type": "container",
            "parameters": {
                "widgetStyle": {
                    "backgroundColor": "#00000000",
                    "borderColor": cd.border_color,
                    "borderEdges": cd.border_edges or [],
                    "borderRadius": 0,
                    "borderWidth": 1,
                },
            },
        }

    # --- Build layout ---
    if pages is None:
        # Single-page mode (original behaviour)
        layout_widgets: List[dict] = []
        row = 0

        layout_widgets.append({
            "name": title_key, "column": 0, "row": row,
            "colspan": column_count, "rowspan": 3,
        })
        row += 3

        if filter_keys:
            fw = column_count // len(filter_keys)
            for i, fk in enumerate(filter_keys):
                layout_widgets.append({
                    "name": fk, "column": i * fw, "row": row,
                    "colspan": fw, "rowspan": 4,
                })
            row += 4

        if metric_keys:
            mw = column_count // len(metric_keys)
            for i, mk in enumerate(metric_keys):
                layout_widgets.append({
                    "name": mk, "column": i * mw, "row": row,
                    "colspan": mw, "rowspan": 8,
                })
            row += 8

        if viz_keys:
            vw = column_count // len(viz_keys)
            for i, vk in enumerate(viz_keys):
                layout_widgets.append({
                    "name": vk, "column": i * vw, "row": row,
                    "colspan": vw, "rowspan": 12,
                })

        for ci, cd in enumerate(containers):
            layout_widgets.append({
                "name": container_keys[ci], "column": cd.column, "row": cd.row,
                "colspan": cd.colspan, "rowspan": cd.rowspan,
            })

        all_pages = [{"name": "page_1", "label": label, "widgets": layout_widgets}]
    else:
        # Multi-page mode
        # Generate nav buttons - create buttons per page so each page has correctly styled buttons
        # Each page needs its own set of buttons where the current page button is active
        nav_button_keys_per_page: List[List[str]] = []
        for page_idx, pg in enumerate(pages):
            page_button_keys: List[str] = []
            for btn_idx, target_page in enumerate(pages):
                # Button key includes page index to make them unique per page
                bkey = f"nav_btn_p{page_idx}_to_{btn_idx + 1}"
                page_button_keys.append(bkey)
                
                # Active button (current page) has no action, inactive buttons navigate
                actions = []
                if btn_idx != page_idx:  # Not the current page, add navigation
                    actions.append({
                        "actionType": "navigate",
                        "eventType": "click",
                        "parameters": {
                            "destination": {"target": target_page.name, "type": "page"},
                        },
                    })
                
                # Style: active page button gets border, inactive gets no border
                if btn_idx == page_idx:
                    # Active page button style
                    widget_style = {
                        "backgroundColor": "#ffffff",
                        "borderColor": "#747474",
                        "borderEdges": [],
                        "borderRadius": 4,
                        "borderWidth": 1,
                    }
                else:
                    # Inactive page button style (link-like)
                    widget_style = {
                        "backgroundColor": "#ffffff",
                        "borderColor": "#ffffff",
                        "borderEdges": ["all"],
                        "borderRadius": 4,
                        "borderWidth": 1,
                    }
                
                widgets[bkey] = {
                    "actions": actions,
                    "name": bkey,
                    "type": "button",
                    "parameters": {
                        "text": target_page.label,
                        "alignmentX": "center",
                        "alignmentY": "center",
                        "fontSize": 18,
                        "widgetStyle": widget_style,
                    },
                }
            nav_button_keys_per_page.append(page_button_keys)

        # Distribute vizzes across pages
        # If VizDef has page_index, use it; otherwise distribute round-robin
        vizzes_per_page: List[List[str]] = [[] for _ in pages]
        for vi, vk in enumerate(viz_keys):
            # Check if this viz has a specific page_index
            viz_def = viz_defs[vi] if vi < len(viz_defs) else None
            if viz_def and hasattr(viz_def, 'page_index'):
                target_page = min(viz_def.page_index, len(pages) - 1)
                vizzes_per_page[target_page].append(vk)
            else:
                # Round-robin distribution
                vizzes_per_page[vi % len(pages)].append(vk)

        # Distribute containers to their specified pages
        containers_per_page: List[List[tuple]] = [[] for _ in pages]
        for ci, cd in enumerate(containers):
            pi = min(cd.page_index, len(pages) - 1)
            containers_per_page[pi].append((container_keys[ci], cd))

        all_pages = []
        for pi, pg in enumerate(pages):
            pw: List[dict] = []
            row = 0

            # Title
            pw.append({
                "name": title_key, "column": 0, "row": row,
                "colspan": column_count, "rowspan": 3,
            })
            row += 3

            # Nav buttons (use buttons specific to this page)
            page_nav_buttons = nav_button_keys_per_page[pi]
            btn_w = column_count // len(page_nav_buttons)
            for bi, bk in enumerate(page_nav_buttons):
                pw.append({
                    "name": bk, "column": bi * btn_w, "row": row,
                    "colspan": btn_w, "rowspan": 2,
                })
            row += 2

            # Filters (every page)
            if filter_keys:
                fw = column_count // len(filter_keys)
                for fi, fk in enumerate(filter_keys):
                    pw.append({
                        "name": fk, "column": fi * fw, "row": row,
                        "colspan": fw, "rowspan": 4,
                    })
                row += 4

            # Metrics (page 0 only)
            if pi == 0 and metric_keys:
                mw = column_count // len(metric_keys)
                for mi, mk in enumerate(metric_keys):
                    pw.append({
                        "name": mk, "column": mi * mw, "row": row,
                        "colspan": mw, "rowspan": 8,
                    })
                row += 8

            # Vizzes for this page
            page_vizzes = vizzes_per_page[pi]
            if page_vizzes:
                vw = column_count // len(page_vizzes)
                for vi, vk in enumerate(page_vizzes):
                    pw.append({
                        "name": vk, "column": vi * vw, "row": row,
                        "colspan": vw, "rowspan": 12,
                    })

            # Containers for this page
            for ckey, cd in containers_per_page[pi]:
                pw.append({
                    "name": ckey, "column": cd.column, "row": cd.row,
                    "colspan": cd.colspan, "rowspan": cd.rowspan,
                })

            all_pages.append({"name": pg.name, "label": pg.label, "widgets": pw})

    return {
        "name": name,
        "label": label,
        "workspaceIdOrApiName": workspace_name,
        "style": {"widgetStyle": dict(widget_style)},
        "layouts": [{
            "name": "default",
            "columnCount": column_count,
            "rowHeight": row_height,
            "maxWidth": 1200,
            "style": {
                "backgroundColor": bg,
                "cellSpacingX": 4,
                "cellSpacingY": 4,
                "gutterColor": "#f3f3f3",
            },
            "pages": all_pages,
        }],
        "widgets": widgets,
    }


def build_dashboard_from_pattern(
    name: str,
    label: str,
    workspace_name: str,
    pattern: str,
    viz_defs: List[VizDef],
    filter_defs: Optional[List[FilterDef]] = None,
    metric_defs: Optional[List[MetricDef]] = None,
    sdm_name: Optional[str] = None,
    column_count: int = 72,
    row_height: int = 20,
    overrides: Optional[Dict[str, Any]] = None,
    page_defs: Optional[List[PageDef]] = None,
    validate_requirements: bool = False,
    **pattern_specific_args
) -> dict:
    """Build dashboard using a predefined layout pattern.
    
    Available patterns:
    - "f_layout": Metrics in left sidebar, visualizations in F-pattern
    - "z_layout": Metrics in top row, visualizations in Z-pattern
    - "performance_overview": Large metric left, smaller metrics right, time navigation
    
    Args:
        name: Dashboard API name
        label: Dashboard display label
        workspace_name: Workspace API name
        pattern: Pattern name (see above)
        viz_defs: List of visualization definitions
        filter_defs: Optional list of filter definitions
        metric_defs: Optional list of metric definitions
        sdm_name: SDM API name (required for filters/metrics)
        column_count: Total columns (default 72)
        row_height: Row height in pixels (default 20)
        overrides: Style overrides
        page_defs: Optional page definitions (for multi-page patterns)
        **pattern_specific_args: Pattern-specific arguments:
            - f_layout/z_layout: title_text (str)
            - performance_overview: primary_metric (str), secondary_metrics (List[str])
    
    Returns:
        Complete dashboard JSON payload
    """
    if not sdm_name:
        raise ValueError("sdm_name is required for pattern-based dashboards")
    
    ov = overrides or {}
    bg = ov.get("backgroundColor", "#ffffff")
    
    filters = filter_defs or []
    metrics = metric_defs or []
    visualizations = [vd.viz_api_name for vd in viz_defs]
    metric_names = [md.metric_api_name for md in metrics]
    
    # Resolve pages
    if page_defs and len(page_defs) > 1:
        pages = [PageDef(label=pd.label, name=pd.name or _generate_uuid()) for pd in page_defs]
    else:
        pages = [PageDef(label=label, name="page_1")]
    
    # Build widgets and layout using pattern
    # For patterns with templates, use template loader (much simpler and ensures perfect alignment)
    if pattern == "f_layout":
        from .dashboard_template_loader import load_dashboard_template, customize_dashboard_template
        
        template = load_dashboard_template("f_layout")
        if not template:
            raise ValueError("f_layout template not found. Check templates/dashboards/F_layout.json exists.")
        
        # Convert filter_defs to dict format expected by customize_dashboard_template
        filter_dicts = []
        for fd in filters:
            filter_dicts.append({
                "fieldName": fd.field_name,
                "objectName": fd.object_name,
                "dataType": fd.data_type,
                "selectionType": fd.selection_type or "multiple",
                "label": fd.label,
            })
        
        # Build visualization slot mapping if viz_defs have template info
        # AI can intelligently map chart types to slots (e.g., funnel → visualization_3)
        visualization_slot_map = None
        if viz_defs:
            from .dashboard_template_loader import recommend_viz_slot_mapping
            # Extract template info from viz_defs if available
            viz_specs = []
            for vd in viz_defs:
                # Try to get template from viz_def (might be stored in metadata or name pattern)
                template_name = getattr(vd, "template", None) or getattr(vd, "chart_type", None) or ""
                viz_specs.append({"name": vd.viz_api_name, "template": template_name})
            visualization_slot_map = recommend_viz_slot_mapping(viz_specs, pattern="f_layout")
            # Only use slot mapping if we got recommendations (otherwise fall back to order)
            if not visualization_slot_map:
                visualization_slot_map = None
        
        # Build visualization specs for text widget generation
        visualization_specs = []
        if viz_defs:
            for vd in viz_defs:
                template_name = getattr(vd, "template", None) or getattr(vd, "chart_type", None) or ""
                visualization_specs.append({
                    "name": vd.viz_api_name,
                    "template": template_name,
                    "label": getattr(vd, "label", vd.viz_api_name.replace("_", " "))
                })
        
        dashboard = customize_dashboard_template(
            template=template,
            name=name,
            label=label,
            workspace_name=workspace_name,
            visualization_names=visualizations,
            visualization_slot_map=visualization_slot_map,
            visualization_specs=visualization_specs,
            metric_names=metric_names,
            filter_defs=filter_dicts,
            sdm_name=sdm_name,
        )
        return dashboard
    
    elif pattern == "z_layout":
        from .dashboard_template_loader import load_dashboard_template, customize_dashboard_template
        
        template = load_dashboard_template("z_layout")
        if not template:
            raise ValueError("z_layout template not found. Check templates/dashboards/Z_Layout.json exists.")
        
        # Convert filter_defs to dict format expected by customize_dashboard_template
        filter_dicts = []
        for fd in filters:
            filter_dicts.append({
                "fieldName": fd.field_name,
                "objectName": fd.object_name,
                "dataType": fd.data_type,
                "selectionType": fd.selection_type or "multiple",
                "label": fd.label,
            })
        
        dashboard = customize_dashboard_template(
            template=template,
            name=name,
            label=label,
            workspace_name=workspace_name,
            visualization_names=visualizations,
            metric_names=metric_names,
            filter_defs=filter_dicts,
            sdm_name=sdm_name,
        )
        return dashboard
    
    elif pattern == "performance_overview":
        primary_metric = pattern_specific_args.get("primary_metric")
        secondary_metrics = pattern_specific_args.get("secondary_metrics", [])
        if not primary_metric:
            raise ValueError("performance_overview pattern requires 'primary_metric' argument")
        widgets, all_pages = dp.build_performance_overview_pattern(
            column_count=column_count,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics,
            visualizations=visualizations,
            filters=filters,
            pages=pages,
            sdm_name=sdm_name,
        )
    
    else:
        raise ValueError(
            f"Unknown pattern: {pattern}. Available: f_layout, z_layout, performance_overview"
        )
    
    # Validate pattern output
    is_valid, validation_errors = dp.validate_pattern_output(widgets, all_pages, column_count)
    if not is_valid:
        error_msg = "Pattern validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
        raise ValueError(error_msg)
    
    return {
        "name": name,
        "label": label,
        "workspaceIdOrApiName": workspace_name,
        "style": {"widgetStyle": {"backgroundColor": bg}},
        "layouts": [{
            "name": "default",
            "columnCount": column_count,
            "rowHeight": row_height,
            "maxWidth": 1200,
            "style": {
                "backgroundColor": bg,
                "cellSpacingX": 4,
                "cellSpacingY": 4,
                "gutterColor": "#f3f3f3",
            },
            "pages": all_pages,
        }],
        "widgets": widgets,
    }
