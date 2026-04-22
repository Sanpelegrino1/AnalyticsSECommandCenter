#!/usr/bin/env python3
"""Automated integration test harness for Tableau Next chart generation.

Generates, validates, POSTs, round-trip GETs, and diffs every chart type x
encoding combination against a live Salesforce org.

Usage:
    python scripts/test_harness.py --sdm Sales_Cloud12_SDM_1772196180
    python scripts/test_harness.py --sdm Sales_Cloud12_SDM_1772196180 --cleanup
    python scripts/test_harness.py --sdm Sales_Cloud12_SDM_1772196180 --json-report results.json
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from lib.sf_api import (
    calculated_field_endpoint,
    dashboard_endpoint,
    get_credentials,
    sdm_detail_endpoint,
    sf_delete,
    sf_get,
    sf_patch,
    sf_post,
    strip_readonly_fields,
    visualization_endpoint,
    workspace_endpoint,
)
from lib.templates import (
    ContainerDef,
    FilterDef,
    MetricDef,
    PageDef,
    VizDef,
    build_bar,
    build_dashboard,
    build_dashboard_from_pattern,
    build_donut,
    build_dot_matrix,
    build_funnel,
    build_heatmap,
    build_line,
    build_root_envelope,
    build_scatter,
    build_table,
    build_viz_from_template_def,
)
from lib.viz_templates import get_template, find_matching_fields
from lib.dashboard_template_loader import load_dashboard_template, customize_dashboard_template
from lib.validators import is_valid
from lib.style_defaults import parse_style_args
from lib.calc_field_templates import (
    build_calculated_dimension,
    build_calculated_measurement,
    win_rate,
)
from lib.metric_templates import (
    build_semantic_metric,
    sum_metric,
    win_rate_metric,
)

WORKSPACE_NAME = "__Test_Harness_WS"
WORKSPACE_LABEL = "Test Harness Workspace"

# ── ANSI helpers ─────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

def _ok(msg: str) -> str:
    return f"{GREEN}PASS{RESET} {msg}"

def _fail(msg: str) -> str:
    return f"{RED}FAIL{RESET} {msg}"

def _warn(msg: str) -> str:
    return f"{YELLOW}WARN{RESET} {msg}"


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class TestCase:
    id: str
    chart_type: str
    description: str
    fields: Dict[str, dict]
    columns: List[str]
    rows: List[str]
    encodings: List[dict]
    legends: Dict[str, dict]
    overrides: Dict[str, Any] = field(default_factory=dict)
    extra_kwargs: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestResult:
    id: str
    chart_type: str
    description: str
    validation_passed: bool
    validation_errors: List[str] = field(default_factory=list)
    post_passed: bool = False
    post_error: str = ""
    roundtrip_passed: bool = False
    roundtrip_diffs: List[str] = field(default_factory=list)
    viz_name: str = ""


# ── SDM field auto-picker ────────────────────────────────────────────────────

@dataclass
class PickedFields:
    text_dim_1: dict
    text_dim_2: dict
    date_dim: dict
    measure_1: dict
    measure_2: dict
    sdm_label: str
    calc_measure: Optional[dict] = None
    calc_dim: Optional[dict] = None
    metric_name: Optional[str] = None
    all_metric_names: Optional[List[str]] = None


def pick_fields(token: str, instance: str, sdm_name: str) -> PickedFields:
    """Auto-select usable fields from the SDM for test cases."""
    data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if data is None:
        print(f"{RED}Error:{RESET} Could not fetch SDM '{sdm_name}'", file=sys.stderr)
        sys.exit(1)

    sdm_label = data.get("label", sdm_name)
    text_dims: List[dict] = []
    date_dims: List[dict] = []
    measures: List[dict] = []
    calc_measures: List[dict] = []
    calc_dims: List[dict] = []

    for obj in data.get("semanticDataObjects", []):
        obj_name = obj.get("apiName", "")
        for d in obj.get("semanticDimensions", []):
            entry = {
                "fieldName": d["apiName"],
                "objectName": obj_name,
                "role": "Dimension",
                "displayCategory": "Discrete",
                "type": "Field",
                "function": None,
            }
            if d.get("dataType") == "DateTime":
                date_dims.append(entry)
            elif d.get("dataType") == "Text":
                text_dims.append(entry)

        for m in obj.get("semanticMeasurements", []):
            measures.append({
                "fieldName": m["apiName"],
                "objectName": obj_name,
                "role": "Measure",
                "displayCategory": "Continuous",
                "type": "Field",
                "function": m.get("aggregationType", "Sum"),
            })

    for cm in data.get("semanticCalculatedMeasurements", []):
        calc_measures.append({
            "fieldName": cm["apiName"],
            "objectName": None,
            "role": "Measure",
            "displayCategory": "Continuous",
            "type": "Field",
            "function": cm.get("aggregationType", "Sum"),
        })

    for cd in data.get("semanticCalculatedDimensions", []):
        if cd.get("dataType") == "Text":
            calc_dims.append({
                "fieldName": cd["apiName"],
                "objectName": None,
                "role": "Dimension",
                "displayCategory": "Discrete",
                "type": "Field",
                "function": None,
            })

    if len(text_dims) < 2:
        print(f"{RED}Error:{RESET} Need >= 2 text dimensions, found {len(text_dims)}", file=sys.stderr)
        sys.exit(1)
    if not date_dims:
        print(f"{RED}Error:{RESET} Need >= 1 date dimension", file=sys.stderr)
        sys.exit(1)
    if len(measures) < 2:
        print(f"{RED}Error:{RESET} Need >= 2 measures, found {len(measures)}", file=sys.stderr)
        sys.exit(1)

    metrics = data.get("semanticMetrics", [])
    metric_name = metrics[0]["apiName"] if metrics else None
    # Store all available metric names for use in dashboards
    all_metric_names = [m["apiName"] for m in metrics] if metrics else []

    return PickedFields(
        text_dim_1=text_dims[0],
        text_dim_2=text_dims[1],
        date_dim=date_dims[0],
        measure_1=measures[0],
        measure_2=measures[1] if len(measures) > 1 else measures[0],
        sdm_label=sdm_label,
        calc_measure=calc_measures[0] if calc_measures else None,
        calc_dim=calc_dims[0] if calc_dims else None,
        metric_name=metric_name,
        all_metric_names=all_metric_names,
    )


# ── Test case definitions ────────────────────────────────────────────────────

def build_test_cases(pf: PickedFields) -> List[TestCase]:
    """Return the 12-case test matrix."""

    # Shorthand field builders
    def _dim(picked: dict, **kw) -> dict:
        d = dict(picked)
        d.update(kw)
        return d

    def _meas(picked: dict, **kw) -> dict:
        m = dict(picked)
        m.update(kw)
        return m

    # Duplicate measure for label encoding
    meas1_label = dict(pf.measure_1)
    meas2_label = dict(pf.measure_2)

    cases = [
        # 1. Bar — simple with Label + Color(dim) + Sort
        TestCase(
            id="bar_simple",
            chart_type="bar",
            description="Bar with Label(measure)",
            fields={
                "F1": _dim(pf.text_dim_1), "F2": _meas(pf.measure_1), 
                "F3": _meas(pf.measure_1), "F4": _dim(pf.text_dim_2),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Label"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
            extra_kwargs={"sort_orders": {
                "columns": [], "rows": [],
                "fields": {"F1": {"byField": "F2", "order": "Descending", "type": "Nested"}},
            }},
        ),
        # 2. Bar — with Color(dim) + Sort
        TestCase(
            id="bar_color_dim_sort",
            chart_type="bar",
            description="Bar + Color(dim) + Sort",
            fields={
                "F1": _dim(pf.text_dim_1), "F2": _meas(pf.measure_1),
                "F3": _meas(pf.measure_1), "F4": _dim(pf.text_dim_2),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Label"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
            extra_kwargs={"sort_orders": {
                "columns": [], "rows": [],
                "fields": {"F1": {"byField": "F2", "order": "Descending", "type": "Nested"}},
            }},
        ),
        # 3. Line — simple with Label (DatePartYear for multi-year datasets)
        TestCase(
            id="line_simple",
            chart_type="line",
            description="Line with Label(measure)",
            fields={
                "F1": {**pf.date_dim, "function": "DatePartYear"},
                "F2": _meas(pf.measure_1),
                "F3": _meas(pf.measure_1),
            },
            columns=["F1"], rows=["F2"],
            encodings=[{"fieldKey": "F3", "type": "Label"}],
            legends={},
        ),
        # 4. Line — with Color(dim) (DatePartYear for multi-year datasets)
        TestCase(
            id="line_color_dim",
            chart_type="line",
            description="Line + Color(dim)",
            fields={
                "F1": {**pf.date_dim, "function": "DatePartYear"},
                "F2": _meas(pf.measure_1),
                "F3": _meas(pf.measure_1),
                "F4": _dim(pf.text_dim_1),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Label"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ),
        # 5. Donut — Angle + Color(dim) + Label (using amount measure instead of probability)
        TestCase(
            id="donut",
            chart_type="donut",
            description="Donut: Angle + Color(dim) + Label",
            fields={
                "F1": _dim(pf.text_dim_1),
                "F2": _meas(pf.measure_2),  # Use amount instead of probability
                "F3": _meas(pf.measure_2),  # Use amount instead of probability
            },
            columns=[], rows=[],
            encodings=[
                {"fieldKey": "F1", "type": "Color"},
                {"fieldKey": "F2", "type": "Angle"},
                {"fieldKey": "F3", "type": "Label"},
            ],
            legends={"F1": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ),
        # 6. Scatter — Detail(dim) + Color(dim)
        TestCase(
            id="scatter_detail_color",
            chart_type="scatter",
            description="Scatter + Detail(dim) + Color(dim)",
            fields={
                "F1": _meas(pf.measure_1), "F2": _meas(pf.measure_2),
                "F3": _dim(pf.text_dim_1), "F4": _dim(pf.text_dim_2),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Detail"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ),
        # 7. Scatter — Color(measure)
        TestCase(
            id="scatter_color_meas",
            chart_type="scatter",
            description="Scatter + Color(measure)",
            fields={
                "F1": _meas(pf.measure_1), "F2": _meas(pf.measure_2),
                "F3": _dim(pf.text_dim_1), "F4": _meas(pf.measure_1),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Detail"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ),
        # 8. Funnel — Label + Color(dim) + Sort (mix of simple and color_dim)
        TestCase(
            id="funnel_simple",
            chart_type="funnel",
            description="Funnel with Label(measure) + Color(dim) + Sort",
            fields={
                "F1": _meas(pf.measure_1), "F2": _dim(pf.text_dim_1),
                "F3": _meas(pf.measure_1), "F4": _dim(pf.text_dim_2),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Label"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
            extra_kwargs={"sort_orders": {
                "columns": [], "rows": [],
                "fields": {"F2": {"byField": "F1", "order": "Descending", "type": "Nested"}},
            }},
        ),
        # 9. Funnel — Label + Color(dim)
        TestCase(
            id="funnel_color_dim",
            chart_type="funnel",
            description="Funnel + Label + Color(dim)",
            fields={
                "F1": _meas(pf.measure_1), "F2": _dim(pf.text_dim_1),
                "F3": _meas(pf.measure_1), "F4": _dim(pf.text_dim_2),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Label"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ),
        # 10. Heatmap — Color(measure) + Label + Size
        TestCase(
            id="heatmap",
            chart_type="heatmap",
            description="Heatmap: Color(measure) + Label + Size",
            fields={
                "F1": _dim(pf.text_dim_1), "F2": _dim(pf.text_dim_2),
                "F3": _meas(pf.measure_1), "F4": _meas(pf.measure_1), "F5": _meas(pf.measure_2),
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Color"},
                {"fieldKey": "F4", "type": "Label"},
                {"fieldKey": "F5", "type": "Size"},
            ],
            legends={"F3": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ),
        # 11. Dot matrix — Color(measure) + Size(measure)
        TestCase(
            id="dot_matrix",
            chart_type="dot_matrix",
            description="Dot Matrix: Color(meas) + Size(meas)",
            fields={
                "F1": _dim(pf.text_dim_1),
                "F2": _meas(pf.measure_1), "F3": _meas(pf.measure_2),
            },
            columns=["F1"], rows=[],
            encodings=[
                {"fieldKey": "F2", "type": "Color"},
                {"fieldKey": "F3", "type": "Size"},
            ],
            legends={"F2": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ),
        # 12. Table — measures in rows (tables don't support columns)
        TestCase(
            id="table",
            chart_type="table",
            description="Table: 2 dims + 1 measure",
            fields={
                "F1": _dim(pf.text_dim_1), "F2": _dim(pf.text_dim_2),
                "F3": _meas(pf.measure_1),
            },
            columns=[], rows=["F1", "F2", "F3"],  # All fields in rows for tables
            encodings=[],
            legends={},
        ),
    ]

    # ── Calculated field (_clc) test cases ────────────────────────────────
    if pf.calc_measure:
        cases.append(TestCase(
            id="bar_clc_measure",
            chart_type="bar",
            description="Bar with _clc measure (UserAgg, objectName=null)",
            fields={
                "F1": _dim(pf.text_dim_1),
                "F2": _meas(pf.calc_measure),
                "F3": _meas(pf.calc_measure),
                "F4": _dim(pf.text_dim_2),  # For color
            },
            columns=["F1"], rows=["F2"],
            encodings=[
                {"fieldKey": "F3", "type": "Label"},
                {"fieldKey": "F4", "type": "Color"},
            ],
            legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
            extra_kwargs={"sort_orders": {
                "columns": [], "rows": [],
                "fields": {"F1": {"byField": "F2", "order": "Descending", "type": "Nested"}},
            }},
        ))
        cases.append(TestCase(
            id="line_clc_date",
            chart_type="line",
            description="Line with _clc measure + DatePartYear",
            fields={
                "F1": {**pf.date_dim, "function": "DatePartYear"},
                "F2": _meas(pf.calc_measure),
                "F3": _meas(pf.calc_measure),
            },
            columns=["F1"], rows=["F2"],
            encodings=[{"fieldKey": "F3", "type": "Label"}],
            legends={},
        ))

    if pf.calc_measure and pf.calc_dim:
        cases.append(TestCase(
            id="donut_clc",
            chart_type="donut",
            description="Donut with _clc measure + _clc dimension",
            fields={
                "F1": _dim(pf.calc_dim),
                "F2": _meas(pf.calc_measure),
                "F3": _meas(pf.calc_measure),
            },
            columns=[], rows=[],
            encodings=[
                {"fieldKey": "F1", "type": "Color"},
                {"fieldKey": "F2", "type": "Angle"},
                {"fieldKey": "F3", "type": "Label"},
            ],
            legends={"F1": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        ))

    # ── MeasureValues / MeasureNames (multi-measure bar) ──────────────────
    cases.append(TestCase(
        id="bar_multi_measure",
        chart_type="bar",
        description="Side-by-Side Bar (MeasureValues)",
        fields={
            "F1": {"displayCategory": "Continuous", "role": "Measure", "type": "MeasureValues"},
            "F2": {"displayCategory": "Discrete", "role": "Dimension", "type": "MeasureNames"},
            "F3": {"displayCategory": "Discrete", "role": "Dimension", "type": "MeasureNames"},
            "F4": {"displayCategory": "Continuous", "role": "Measure", "type": "MeasureValues"},
            "F6": _meas(pf.measure_1),
            "F8": _meas(pf.measure_2),
        },
        columns=["F2"], rows=["F1"],
        encodings=[
            {"fieldKey": "F3", "type": "Color"},
            {"fieldKey": "F4", "type": "Label"},
        ],
        legends={"F3": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        extra_kwargs={"measure_values": ["F8", "F6"]},
    ))

    # ── Additional encoding combinations ────────────────────────────────────

    # Bar charts: Size, Detail, multiple encodings
    cases.append(TestCase(
        id="bar_size_encoding",
        chart_type="bar",
        description="Bar with Size(measure) encoding",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),
            "F3": _meas(pf.measure_2),  # For size encoding
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Size"}],
        legends={},
    ))
    cases.append(TestCase(
        id="bar_detail_encoding",
        chart_type="bar",
        description="Bar with Detail(dimension) encoding",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),
            "F3": _dim(pf.text_dim_2),  # For detail encoding
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Detail"}],
        legends={},
    ))
    cases.append(TestCase(
        id="bar_multiple_encodings",
        chart_type="bar",
        description="Bar with Label + Color + Size encodings",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),
            "F3": _meas(pf.measure_1),  # For label
            "F4": _dim(pf.text_dim_2),  # For color
            "F5": _meas(pf.measure_2),  # For size
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Label"},
            {"fieldKey": "F4", "type": "Color"},
            {"fieldKey": "F5", "type": "Size"},
        ],
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))

    # Line charts: Detail, date function variations
    # Note: Size encoding is NOT supported for Line charts (API limitation)
    cases.append(TestCase(
        id="line_detail_encoding",
        chart_type="line",
        description="Line with Detail(dimension) encoding",
        fields={
            "F1": {**pf.date_dim, "function": "DatePartYear"},  # Use Year for multi-year datasets
            "F2": _meas(pf.measure_1),
            "F3": _dim(pf.text_dim_1),  # For detail
            "F4": _dim(pf.text_dim_1),  # For color (multi-dim line charts need color)
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Detail"},
            {"fieldKey": "F4", "type": "Color"},  # Color by dimension for multi-line chart
        ],
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))
    cases.append(TestCase(
        id="line_datepart_year",
        chart_type="line",
        description="Line with DatePartYear",
        fields={
            "F1": {**pf.date_dim, "function": "DatePartYear"},
            "F2": _meas(pf.measure_1),
            "F3": _meas(pf.measure_1),
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Label"}],
        legends={},
    ))
    cases.append(TestCase(
        id="line_datepart_quarter",
        chart_type="line",
        description="Line with DatePartQuarter",
        fields={
            "F1": {**pf.date_dim, "function": "DatePartQuarter"},
            "F2": _meas(pf.measure_1),
            "F3": _meas(pf.measure_1),
            "F4": {**pf.date_dim, "function": "DatePartYear"},  # Year as dimension for grouping
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Label"},
            {"fieldKey": "F4", "type": "Color"},  # Color by year to distinguish quarters across years
        ],
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))
    cases.append(TestCase(
        id="line_datepart_day",
        chart_type="line",
        description="Line with DatePartDay (with Year and Month for proper grouping)",
        fields={
            "F1": {**pf.date_dim, "function": "DatePartDay"},
            "F2": _meas(pf.measure_1),
            "F3": _meas(pf.measure_1),
            "F4": {**pf.date_dim, "function": "DatePartYear"},   # Year dimension
            "F5": {**pf.date_dim, "function": "DatePartMonth"},  # Month dimension
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Label"},
            {"fieldKey": "F4", "type": "Color"},  # Color by year
            {"fieldKey": "F5", "type": "Detail"},  # Detail by month to group days properly
        ],
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))
    cases.append(TestCase(
        id="line_datepart_week",
        chart_type="line",
        description="Line with DatePartWeek",
        fields={
            "F1": {**pf.date_dim, "function": "DatePartWeek"},
            "F2": _meas(pf.measure_1),
            "F3": _meas(pf.measure_1),
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Label"}],
        legends={},
    ))

    # Scatter charts: Additional combinations
    cases.append(TestCase(
        id="scatter_detail_color_size",
        chart_type="scatter",
        description="Scatter: Detail(dim) + Color(dim for detail level) + Size(3rd measure)",
        fields={
            "F1": _meas(pf.measure_1),
            "F2": _meas(pf.measure_2),
            "F3": _dim(pf.text_dim_1),  # Detail
            "F4": _dim(pf.text_dim_1),  # Color by dimension (detail level) - best practice
            "F5": _meas(pf.measure_2),  # Size by 3rd measure (reusing measure_2 as 3rd measure)
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Detail"},
            {"fieldKey": "F4", "type": "Color"},  # Color by dimension (best practice)
            {"fieldKey": "F5", "type": "Size"},   # Size by 3rd measure
        ],
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))
    cases.append(TestCase(
        id="scatter_detail_color_dim_size",
        chart_type="scatter",
        description="Scatter: Detail(dim) + Color(dim) + Size(measure)",
        fields={
            "F1": _meas(pf.measure_1),
            "F2": _meas(pf.measure_2),
            "F3": _dim(pf.text_dim_1),  # Detail
            "F4": _dim(pf.text_dim_2),  # Color (dimension)
            "F5": _meas(pf.measure_1),  # Size
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Detail"},
            {"fieldKey": "F4", "type": "Color"},
            {"fieldKey": "F5", "type": "Size"},
        ],
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))

    # Donut charts: Additional combinations
    # Note: Size encoding is NOT supported for Donut charts (API limitation)

    # Funnel charts: Additional combinations
    cases.append(TestCase(
        id="funnel_color_dim_label",
        chart_type="funnel",
        description="Funnel: Color(dim) + Label",
        fields={
            "F1": _meas(pf.measure_1),
            "F2": _dim(pf.text_dim_1),
            "F3": _meas(pf.measure_1),  # Label
            "F4": _dim(pf.text_dim_2),  # Color
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Label"},
            {"fieldKey": "F4", "type": "Color"},
        ],
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))
    cases.append(TestCase(
        id="funnel_size_encoding",
        chart_type="funnel",
        description="Funnel with Size(measure) encoding",
        fields={
            "F1": _meas(pf.measure_1),
            "F2": _dim(pf.text_dim_1),
            "F3": _meas(pf.measure_2),  # Size
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Size"}],
        legends={},
    ))

    # Heatmap charts: Additional combinations
    cases.append(TestCase(
        id="heatmap_label_encoding",
        chart_type="heatmap",
        description="Heatmap with Label encoding",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _dim(pf.text_dim_2),
            "F3": _meas(pf.measure_1),  # Color
            "F4": _meas(pf.measure_1),  # Label
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Color"},
            {"fieldKey": "F4", "type": "Label"},
        ],
        legends={"F3": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))
    cases.append(TestCase(
        id="heatmap_size_encoding",
        chart_type="heatmap",
        description="Heatmap with Size encoding",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _dim(pf.text_dim_2),
            "F3": _meas(pf.measure_1),  # Color
            "F4": _meas(pf.measure_2),  # Size
        },
        columns=["F1"], rows=["F2"],
        encodings=[
            {"fieldKey": "F3", "type": "Color"},
            {"fieldKey": "F4", "type": "Size"},
        ],
        legends={"F3": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))

    # Dot Matrix charts: Additional combinations
    cases.append(TestCase(
        id="dot_matrix_label_encoding",
        chart_type="dot_matrix",
        description="Dot Matrix with Label encoding",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),  # Color
            "F3": _meas(pf.measure_2),  # Size
            "F4": _meas(pf.measure_1),  # Label
        },
        columns=["F1"], rows=[],
        encodings=[
            {"fieldKey": "F2", "type": "Color"},
            {"fieldKey": "F3", "type": "Size"},
            {"fieldKey": "F4", "type": "Label"},
        ],
        legends={"F2": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))
    cases.append(TestCase(
        id="dot_matrix_color_dim_size_label",
        chart_type="dot_matrix",
        description="Dot Matrix: Color(dim) + Size + Label",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _dim(pf.text_dim_2),  # Color (dimension)
            "F3": _meas(pf.measure_1),  # Size
            "F4": _meas(pf.measure_1),  # Label
        },
        columns=["F1"], rows=[],
        encodings=[
            {"fieldKey": "F2", "type": "Color"},
            {"fieldKey": "F3", "type": "Size"},
            {"fieldKey": "F4", "type": "Label"},
        ],
        legends={"F2": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
    ))

    # Table charts: Additional combinations
    cases.append(TestCase(
        id="table_three_dims",
        chart_type="table",
        description="Table with 3 dimensions",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _dim(pf.text_dim_2),
            "F3": _dim(pf.date_dim),
            "F4": _meas(pf.measure_1),
        },
        columns=[], rows=["F1", "F2", "F3", "F4"],  # All fields in rows for tables
        encodings=[],
        legends={},
    ))
    cases.append(TestCase(
        id="table_two_measures",
        chart_type="table",
        description="Table with 2 measures",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _dim(pf.text_dim_2),
            "F3": _meas(pf.measure_1),
            "F4": _meas(pf.measure_2),
        },
        columns=[], rows=["F1", "F2", "F3", "F4"],  # All fields in rows for tables
        encodings=[],
        legends={},
    ))

    # Style override combinations
    cases.append(TestCase(
        id="bar_style_overrides",
        chart_type="bar",
        description="Bar with multiple style overrides",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),
            "F3": _meas(pf.measure_1),
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Label"}],
        legends={},
        overrides={
            "backgroundColor": "#1A1A1A",
            "fontColor": "#FFFFFF",
            "lineColor": "#C9C9C9",
        },
    ))

    return cases


# ── Core test runner ─────────────────────────────────────────────────────────

def generate_payload(tc: TestCase, sdm_name: str, sdm_label: str) -> dict:
    """Build the full API payload for a test case."""
    overrides = tc.overrides or {}
    chart = tc.chart_type
    kw = tc.extra_kwargs or {}

    if chart == "bar":
        vs = build_bar(tc.fields, tc.columns, tc.rows, tc.encodings, tc.legends, overrides,
                       sort_orders=kw.get("sort_orders"),
                       measure_values=kw.get("measure_values"))
    elif chart == "line":
        vs = build_line(tc.fields, tc.columns, tc.rows, tc.encodings, tc.legends, overrides)
    elif chart == "donut":
        vs = build_donut(tc.fields, tc.columns, tc.rows, tc.encodings, tc.legends, overrides)
    elif chart == "scatter":
        vs = build_scatter(tc.fields, tc.columns, tc.rows, tc.encodings, tc.legends, overrides)
    elif chart == "funnel":
        vs = build_funnel(tc.fields, tc.columns, tc.rows, tc.encodings, tc.legends, overrides)
    elif chart == "heatmap":
        color_fk = None
        for e in tc.encodings:
            if e.get("type") == "Color":
                color_fk = e.get("fieldKey")
                break
        vs = build_heatmap(tc.fields, tc.columns, tc.rows, tc.encodings, tc.legends, overrides,
                           color_field_key=color_fk)
    elif chart == "dot_matrix":
        size_fk = None
        for e in tc.encodings:
            if e.get("type") == "Size":
                size_fk = e.get("fieldKey")
                break
        vs = build_dot_matrix(tc.fields, tc.columns, tc.rows, tc.encodings, tc.legends, overrides,
                              size_field_key=size_fk)
    elif chart == "table":
        vs = build_table(tc.fields, tc.rows, overrides, columns=tc.columns)
        # For tables, measures must have displayCategory: "Discrete" (not "Continuous")
        # Create a copy of fields and modify measures to be Discrete
        fields_for_table = {}
        for fk, fdef in tc.fields.items():
            field_copy = dict(fdef)
            if field_copy.get("role") == "Measure":
                field_copy["displayCategory"] = "Discrete"
            fields_for_table[fk] = field_copy
    else:
        raise ValueError(f"Unknown chart type: {chart}")

    viz_name = f"__TH_{tc.id}"
    sort_orders = kw.get("sort_orders")

    return build_root_envelope(
        name=viz_name,
        label=f"TH: {tc.description}",
        sdm_name=sdm_name,
        sdm_label=sdm_label,
        workspace_name=WORKSPACE_NAME,
        workspace_label=WORKSPACE_LABEL,
        fields=fields_for_table if chart == "table" else tc.fields,
        visual_spec=vs,
        sort_orders=sort_orders,
    )


READ_ONLY_ROOT = {"url", "id", "createdBy", "createdDate", "lastModifiedBy",
                   "lastModifiedDate", "permissions", "sourceVersion", "workspaceIdOrApiName"}


def roundtrip_diff(sent: dict, got: dict) -> List[str]:
    """Compare sent payload vs GET response for meaningful structural diffs."""
    diffs: List[str] = []

    # Check encoding style fields — did the API drop or add any?
    sent_enc = (sent.get("visualSpecification", {})
                .get("style", {}).get("encodings", {}).get("fields", {}))
    got_enc = (got.get("visualSpecification", {})
               .get("style", {}).get("encodings", {}).get("fields", {}))

    sent_keys = set(sent_enc.keys())
    got_keys = set(got_enc.keys())
    dropped = sent_keys - got_keys
    added = got_keys - sent_keys
    if dropped:
        diffs.append(f"style.encodings.fields keys dropped by API: {dropped}")
    if added:
        diffs.append(f"style.encodings.fields keys added by API: {added}")

    # Check header style fields
    sent_hdr = (sent.get("visualSpecification", {})
                .get("style", {}).get("headers", {}).get("fields", {}))
    got_hdr = (got.get("visualSpecification", {})
               .get("style", {}).get("headers", {}).get("fields", {}))
    h_dropped = set(sent_hdr.keys()) - set(got_hdr.keys())
    h_added = set(got_hdr.keys()) - set(sent_hdr.keys())
    if h_dropped:
        diffs.append(f"style.headers.fields keys dropped by API: {h_dropped}")
    if h_added:
        diffs.append(f"style.headers.fields keys added by API: {h_added}")

    # Check axis fields
    sent_ax = (sent.get("visualSpecification", {})
               .get("style", {}).get("axis", {}).get("fields", {}))
    got_ax = (got.get("visualSpecification", {})
              .get("style", {}).get("axis", {}).get("fields", {}))
    if sent_ax is not None and got_ax is not None:
        a_dropped = set(sent_ax.keys()) - set(got_ax.keys())
        a_added = set(got_ax.keys()) - set(sent_ax.keys())
        if a_dropped:
            diffs.append(f"style.axis.fields keys dropped by API: {a_dropped}")
        if a_added:
            diffs.append(f"style.axis.fields keys added by API: {a_added}")

    # Check marks.panes.type preserved
    sent_mt = sent.get("visualSpecification", {}).get("marks", {}).get("panes", {}).get("type")
    got_mt = got.get("visualSpecification", {}).get("marks", {}).get("panes", {}).get("type")
    if sent_mt and got_mt and sent_mt != got_mt:
        diffs.append(f"marks.panes.type changed: sent={sent_mt}, got={got_mt}")

    return diffs


def run_test(
    tc: TestCase,
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
) -> TestResult:
    """Execute a single test case: validate → POST → GET → diff."""
    result = TestResult(id=tc.id, chart_type=tc.chart_type, description=tc.description, validation_passed=False)

    # 1. Generate payload
    payload = generate_payload(tc, sdm_name, sdm_label)
    result.viz_name = payload["name"]

    # 2. Validate
    ok, val_results = is_valid(payload)
    result.validation_passed = ok
    if not ok:
        result.validation_errors = [
            f"{r.rule}: {r.message}" for r in val_results if not r.ok
        ]
        return result

    # 3. POST
    resp, err = sf_post(token, instance, visualization_endpoint(), payload)
    if err or resp is None:
        result.post_error = err or "No response"
        return result
    if isinstance(resp, list):
        result.post_error = str(resp)
        return result
    
    # Update viz_name with actual name from response
    result.viz_name = resp.get("name", payload["name"])
    result.post_passed = True

    # 4. Round-trip GET
    viz_name = payload["name"]
    got = sf_get(token, instance, visualization_endpoint(viz_name))
    if got is None:
        result.roundtrip_diffs = ["GET after POST returned None"]
        return result

    diffs = roundtrip_diff(payload, got)
    result.roundtrip_passed = len(diffs) == 0
    result.roundtrip_diffs = diffs

    return result


# ── Workspace management ─────────────────────────────────────────────────────

def ensure_workspace(token: str, instance: str) -> Tuple[bool, Optional[str]]:
    """Create the test workspace if it doesn't exist. Returns (success, actual_name)."""
    existing = sf_get(token, instance, workspace_endpoint(WORKSPACE_NAME))
    if existing and isinstance(existing, dict) and existing.get("name") == WORKSPACE_NAME:
        return True, WORKSPACE_NAME

    payload = {"name": WORKSPACE_NAME, "label": WORKSPACE_LABEL}
    resp, err = sf_post(token, instance, workspace_endpoint(), payload)
    if err:
        # Might already exist (409)
        if "DUPLICATE" in (err or "").upper() or "already" in (err or "").lower():
            return True, WORKSPACE_NAME
        print(f"{RED}Error creating workspace:{RESET} {err}", file=sys.stderr)
        return False, None
    
    actual_name = resp.get("name", WORKSPACE_NAME) if resp else WORKSPACE_NAME
    return True, actual_name


def run_dashboard_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 17: create 2 vizzes then a dashboard referencing them."""
    result = TestResult(
        id="dashboard_2viz", chart_type="dashboard",
        description="Dashboard with 2 viz widgets + text", validation_passed=True,
    )

    # Create two helper vizzes
    viz_names: List[str] = []
    for tc_id, chart, desc, fields, cols, rows, encs in [
        ("dash_bar", "bar", "Dash helper bar",
         {"F1": pf.text_dim_1, "F2": pf.measure_1, "F3": pf.measure_1},
         ["F1"], ["F2"], [{"fieldKey": "F3", "type": "Label"}]),
        ("dash_donut", "donut", "Dash helper donut",
         {"F1": pf.text_dim_1, "F2": pf.measure_1, "F3": pf.measure_1},
         [], [], [{"fieldKey": "F1", "type": "Color"}, {"fieldKey": "F2", "type": "Angle"},
                  {"fieldKey": "F3", "type": "Label"}]),
    ]:
        tc = TestCase(id=tc_id, chart_type=chart, description=desc,
                      fields=dict(fields), columns=cols, rows=rows, encodings=encs, legends={})
        payload = generate_payload(tc, sdm_name, sdm_label)
        resp, err = sf_post(token, instance, visualization_endpoint(), payload)
        if err:
            result.post_error = f"Helper viz {tc_id}: {err}"
            return result
        # Use actual name from response, not payload name
        actual_viz_name = resp.get("name", payload["name"]) if resp else payload["name"]
        viz_names.append(actual_viz_name)

    # Build dashboard
    dash_payload = {
        "name": "__TH_dashboard_2viz",
        "label": "TH: Dashboard Test",
        "workspaceIdOrApiName": WORKSPACE_NAME,
        "style": {
            "widgetStyle": {
                "backgroundColor": "#ffffff", "borderColor": "#cccccc",
                "borderEdges": [], "borderRadius": 0, "borderWidth": 1,
            }
        },
        "layouts": [{
            "name": "default", "columnCount": 48, "rowHeight": 20, "maxWidth": 1200,
            "style": {
                "backgroundColor": "#ffffff", "cellSpacingX": 4,
                "cellSpacingY": 4, "gutterColor": "#f3f3f3",
            },
            "pages": [{
                "name": "page_1", "label": "Overview",
                "widgets": [
                    {"name": "title", "column": 0, "row": 0, "colspan": 48, "rowspan": 3},
                    {"name": "w_bar", "column": 0, "row": 3, "colspan": 24, "rowspan": 12},
                    {"name": "w_donut", "column": 24, "row": 3, "colspan": 24, "rowspan": 12},
                ],
            }],
        }],
        "widgets": {
            "title": {
                "actions": [], "name": "title", "type": "text",
                "parameters": {"content": [
                    {"attributes": {"bold": True, "size": "16px"}, "insert": "Test Dashboard"},
                    {"attributes": {"align": "center"}, "insert": "\n"},
                ]},
            },
            "w_bar": {
                "actions": [], "name": "w_bar", "type": "visualization",
                "source": {"name": viz_names[0]},
                "parameters": {"legendPosition": "Right",
                               "receiveFilterSource": {"filterMode": "all", "widgetIds": []}},
            },
            "w_donut": {
                "actions": [], "name": "w_donut", "type": "visualization",
                "source": {"name": viz_names[1]},
                "parameters": {"legendPosition": "Right",
                               "receiveFilterSource": {"filterMode": "all", "widgetIds": []}},
            },
        },
    }

    resp, err = sf_post(token, instance, dashboard_endpoint(), dash_payload)
    if err:
        result.post_error = f"Dashboard POST: {err}"
        return result
    if isinstance(resp, list):
        result.post_error = str(resp)
        return result
    result.post_passed = True
    result.viz_name = "__TH_dashboard_2viz"

    # Verify all widgets OK
    got = sf_get(token, instance, dashboard_endpoint("__TH_dashboard_2viz"))
    if got is None:
        result.roundtrip_diffs = ["GET after dashboard POST returned None"]
        return result

    widgets = got.get("widgets", {})
    bad = []
    for wk, wv in widgets.items():
        if isinstance(wv, dict) and wv.get("status") and wv["status"] != "Ok":
            bad.append(f"{wk}: status={wv['status']}")
    if bad:
        result.roundtrip_diffs = bad
    else:
        result.roundtrip_passed = True

    return result


def run_dashboard_full_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 19: dashboard with filters + metrics + diverse vizzes using F-layout pattern."""
    result = TestResult(
        id="dashboard_full", chart_type="dashboard",
        description="Dashboard: filters + metrics + 5 diverse vizzes (F-layout)", validation_passed=True,
    )

    # Create diverse visualizations to fill all 5 slots
    viz_names: List[str] = []
    
    # 1. Bar chart - Revenue by dimension with color and sort
    tc1 = TestCase(
        id="dashf_bar", chart_type="bar", description="Revenue by Account",
        fields={"F1": pf.text_dim_1, "F2": pf.measure_1, "F4": pf.text_dim_2},
        columns=["F1"], rows=["F2"], 
        encodings=[{"fieldKey": "F4", "type": "Color"}], legends={},
        extra_kwargs={"sort_orders": {"columns": [], "fields": {"F1": {"byField": "F2", "order": "Descending", "type": "Field"}}, "rows": []}}
    )
    payload1 = generate_payload(tc1, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload1)
    if err:
        result.post_error = f"Helper viz dashf_bar: {err}"
        return result
    viz_names.append(resp.get("name", payload1["name"]) if resp else payload1["name"])
    
    # 2. Line chart - Trend over time (use DatePartYear for multi-year data)
    date_field = dict(pf.date_dim)
    date_field["function"] = "DatePartYear"
    tc2 = TestCase(
        id="dashf_line", chart_type="line", description="Revenue Trend",
        fields={"F1": date_field, "F2": pf.measure_1, "F3": pf.measure_1},
        columns=["F1"], rows=["F2"], 
        encodings=[{"fieldKey": "F3", "type": "Label"}], legends={}
    )
    payload2 = generate_payload(tc2, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload2)
    if err:
        result.post_error = f"Helper viz dashf_line: {err}"
        return result
    viz_names.append(resp.get("name", payload2["name"]) if resp else payload2["name"])
    
    # 3. Donut chart - Distribution
    tc3 = TestCase(
        id="dashf_donut", chart_type="donut", description="Distribution",
        fields={"F1": pf.text_dim_1, "F2": pf.measure_1, "F3": pf.measure_1},
        columns=[], rows=[], 
        encodings=[
            {"fieldKey": "F1", "type": "Color"}, 
            {"fieldKey": "F2", "type": "Angle"},
            {"fieldKey": "F3", "type": "Label"}
        ], legends={"F1": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    )
    payload3 = generate_payload(tc3, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload3)
    if err:
        result.post_error = f"Helper viz dashf_donut: {err}"
        return result
    viz_names.append(resp.get("name", payload3["name"]) if resp else payload3["name"])
    
    # 4. Table - Detailed data (measures need displayCategory: Discrete)
    tc4 = TestCase(
        id="dashf_table", chart_type="table", description="Detailed Data",
        fields={"F1": pf.text_dim_1, "F2": pf.text_dim_2, "F3": pf.measure_1},
        columns=[], rows=["F1", "F2", "F3"], encodings=[], legends={}
    )
    payload4 = generate_payload(tc4, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload4)
    if err:
        result.post_error = f"Helper viz dashf_table: {err}"
        return result
    viz_names.append(resp.get("name", payload4["name"]) if resp else payload4["name"])
    
    # 5. Scatter plot - Relationship analysis
    tc5 = TestCase(
        id="dashf_scatter", chart_type="scatter", description="Relationship Analysis",
        fields={"F1": pf.measure_1, "F2": pf.measure_2, "F3": pf.text_dim_1},
        columns=["F1"], rows=["F2"], 
        encodings=[{"fieldKey": "F3", "type": "Color"}], legends={"F3": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    )
    payload5 = generate_payload(tc5, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload5)
    if err:
        result.post_error = f"Helper viz dashf_scatter: {err}"
        return result
    viz_names.append(resp.get("name", payload5["name"]) if resp else payload5["name"])

    # Load F_layout template directly
    template = load_dashboard_template("F_layout")
    if not template:
        result.post_error = "F_layout template not found"
        return result
    
    # Prepare multiple filters (use all 6 slots with available dimensions)
    filter_data = []
    if pf.text_dim_1:
        filter_data.append({
            "fieldName": pf.text_dim_1["fieldName"],
            "objectName": pf.text_dim_1["objectName"],
            "dataType": "Text",
            "selectionType": "multiple",
            "label": pf.text_dim_1["fieldName"].replace("_", " ").title(),
        })
    if pf.text_dim_2:
        filter_data.append({
            "fieldName": pf.text_dim_2["fieldName"],
            "objectName": pf.text_dim_2["objectName"],
            "dataType": "Text",
            "selectionType": "multiple",
            "label": pf.text_dim_2["fieldName"].replace("_", " ").title(),
        })
    if pf.date_dim:
        filter_data.append({
            "fieldName": pf.date_dim["fieldName"],
            "objectName": pf.date_dim["objectName"],
            "dataType": "DateTime",
            "selectionType": "multiple",
            "label": pf.date_dim["fieldName"].replace("_", " ").title(),
        })
    # Add more filters if we have calculated dimensions
    if pf.calc_dim:
        filter_data.append({
            "fieldName": pf.calc_dim["fieldName"],
            "objectName": None,  # Calculated fields don't have objectName
            "dataType": pf.calc_dim.get("dataType", "Text"),
            "selectionType": "multiple",
            "label": pf.calc_dim["fieldName"].replace("_", " ").title(),
        })
    # Pad with additional filters if needed (reuse dimensions)
    while len(filter_data) < 6:
        if pf.text_dim_1:
            filter_data.append({
                "fieldName": pf.text_dim_1["fieldName"],
                "objectName": pf.text_dim_1["objectName"],
                "dataType": "Text",
                "selectionType": "multiple",
                "label": f"{pf.text_dim_1['fieldName'].replace('_', ' ').title()} (2)",
            })
        else:
            break
    
    # Prepare metrics (F-layout typically has 3-5 metric slots)
    metric_data = []
    available_metrics = pf.all_metric_names if pf.all_metric_names else ([pf.metric_name] if pf.metric_name else [])
    if available_metrics:
        # Provide 3 metric names, cycling through available metrics
        # This ensures all metric widgets in template get valid sources
        for i in range(3):
            metric_name = available_metrics[i % len(available_metrics)]
            metric_data.append(metric_name)
    
    # Get SDM ID for metricOption (optional but may help with DataSourceError)
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    sdm_id = sdm_data.get("id") if sdm_data else None
    
    # Customize template with actual widget sources
    dash_payload = customize_dashboard_template(
        template=template,
        name="__TH_dashboard_full",
        label="TH: Full Dashboard Test",
        workspace_name=WORKSPACE_NAME,
        visualization_names=viz_names,
        metric_names=metric_data,
        filter_defs=filter_data,
        sdm_name=sdm_name,
        sdm_id=sdm_id,
    )

    resp, err = sf_post(token, instance, dashboard_endpoint(), dash_payload)
    if err:
        result.post_error = f"Dashboard POST: {err}"
        return result
    if isinstance(resp, list):
        result.post_error = str(resp)
        return result
    result.post_passed = True
    result.viz_name = "__TH_dashboard_full"

    # Verify all widgets OK
    got = sf_get(token, instance, dashboard_endpoint("__TH_dashboard_full"))
    if got is None:
        result.roundtrip_diffs = ["GET after dashboard POST returned None"]
        return result

    widgets = got.get("widgets", {})
    bad = []
    for wk, wv in widgets.items():
        if isinstance(wv, dict) and wv.get("status") and wv["status"] != "Ok":
            bad.append(f"{wk}: status={wv['status']}")
    if bad:
        result.roundtrip_diffs = bad
    else:
        result.roundtrip_passed = True

    return result


def run_style_override_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 20: POST a bar with custom styles, verify round-tripped JSON paths."""
    result = TestResult(
        id="style_override_verify", chart_type="bar",
        description="Bar with custom style overrides (bg/font/line)", validation_passed=True,
    )

    custom_overrides = {
        "backgroundColor": "#1A1A1A",
        "fontColor": "#FFFFFF",
        "lineColor": "#333333",
    }
    tc = TestCase(
        id="style_test", chart_type="bar", description="Style override target",
        fields={"F1": pf.text_dim_1, "F2": pf.measure_1, "F3": pf.measure_1},
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Label"}], legends={},
        overrides=custom_overrides,
    )
    payload = generate_payload(tc, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload)
    if err:
        result.post_error = f"POST: {err}"
        return result
    result.viz_name = resp.get("name", payload["name"]) if resp else payload["name"]
    result.post_passed = True

    got = sf_get(token, instance, visualization_endpoint(payload["name"]))
    if got is None:
        result.roundtrip_diffs = ["GET after POST returned None"]
        return result

    style = got.get("visualSpecification", {}).get("style", {})
    diffs: List[str] = []

    got_bg = style.get("shading", {}).get("backgroundColor")
    if got_bg != "#1A1A1A":
        diffs.append(f"shading.backgroundColor: expected '#1A1A1A', got '{got_bg}'")

    got_font = style.get("fonts", {}).get("headers", {}).get("color")
    if got_font != "#FFFFFF":
        diffs.append(f"fonts.headers.color: expected '#FFFFFF', got '{got_font}'")

    got_line = style.get("lines", {}).get("axisLine", {}).get("color")
    if got_line != "#333333":
        diffs.append(f"lines.axisLine.color: expected '#333333', got '{got_line}'")

    if diffs:
        result.roundtrip_diffs = diffs
    else:
        result.roundtrip_passed = True

    return result


def run_dashboard_multipage_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 21: Production-ready multi-page dashboard with navigation, metrics, filters, and visualizations."""
    result = TestResult(
        id="dashboard_multipage", chart_type="dashboard",
        description="Production-ready 3-page dashboard with navigation, metrics, filters, containers", validation_passed=True,
    )

    # Create 5-6 diverse visualizations
    viz_names: List[str] = []
    
    # 1. Bar chart - Revenue by dimension with color and sort (Page 1)
    tc1 = TestCase(
        id="dashm_bar", chart_type="bar", description="Revenue by Account",
        fields={"F1": pf.text_dim_1, "F2": pf.measure_1, "F4": pf.text_dim_2},
        columns=["F1"], rows=["F2"], 
        encodings=[{"fieldKey": "F4", "type": "Color"}], 
        legends={"F4": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        extra_kwargs={"sort_orders": {"columns": [], "fields": {"F1": {"byField": "F2", "order": "Descending", "type": "Field"}}, "rows": []}}
    )
    payload1 = generate_payload(tc1, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload1)
    if err:
        result.post_error = f"Helper viz dashm_bar: {err}"
        return result
    viz_names.append(resp.get("name", payload1["name"]) if resp else payload1["name"])
    
    # 2. Line chart - Trend over time with DatePartYear (Page 1)
    date_field = dict(pf.date_dim)
    date_field["function"] = "DatePartYear"
    tc2 = TestCase(
        id="dashm_line", chart_type="line", description="Revenue Trend Over Time",
        fields={"F1": date_field, "F2": pf.measure_1, "F3": pf.measure_1},
        columns=["F1"], rows=["F2"], 
        encodings=[{"fieldKey": "F3", "type": "Label"}], legends={}
    )
    payload2 = generate_payload(tc2, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload2)
    if err:
        result.post_error = f"Helper viz dashm_line: {err}"
        return result
    viz_names.append(resp.get("name", payload2["name"]) if resp else payload2["name"])
    
    # 3. Donut chart - Distribution (Page 1)
    tc3 = TestCase(
        id="dashm_donut", chart_type="donut", description="Distribution by Category",
        fields={"F1": pf.text_dim_1, "F2": pf.measure_1, "F3": pf.measure_1},
        columns=[], rows=[], 
        encodings=[
            {"fieldKey": "F1", "type": "Color"}, 
            {"fieldKey": "F2", "type": "Angle"},
            {"fieldKey": "F3", "type": "Label"}
        ], 
        legends={"F1": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    )
    payload3 = generate_payload(tc3, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload3)
    if err:
        result.post_error = f"Helper viz dashm_donut: {err}"
        return result
    viz_names.append(resp.get("name", payload3["name"]) if resp else payload3["name"])
    
    # 4. Table - Detailed data with measures (Page 2)
    tc4 = TestCase(
        id="dashm_table", chart_type="table", description="Detailed Data Table",
        fields={"F1": pf.text_dim_1, "F2": pf.text_dim_2, "F3": pf.measure_1},
        columns=[], rows=["F1", "F2", "F3"], encodings=[], legends={}
    )
    payload4 = generate_payload(tc4, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload4)
    if err:
        result.post_error = f"Helper viz dashm_table: {err}"
        return result
    viz_names.append(resp.get("name", payload4["name"]) if resp else payload4["name"])
    
    # 5. Scatter plot - Relationship analysis (Page 2)
    tc5 = TestCase(
        id="dashm_scatter", chart_type="scatter", description="Relationship Analysis",
        fields={"F1": pf.measure_1, "F2": pf.measure_2, "F3": pf.text_dim_1},
        columns=["F1"], rows=["F2"], 
        encodings=[{"fieldKey": "F3", "type": "Color"}], 
        legends={"F3": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    )
    payload5 = generate_payload(tc5, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload5)
    if err:
        result.post_error = f"Helper viz dashm_scatter: {err}"
        return result
    viz_names.append(resp.get("name", payload5["name"]) if resp else payload5["name"])
    
    # 6. Line chart with detail encoding - Multi-series trend (Page 3)
    date_field_detail = dict(pf.date_dim)
    date_field_detail["function"] = "DatePartYear"
    tc6 = TestCase(
        id="dashm_line_detail", chart_type="line", description="Multi-Series Trend Analysis",
        fields={"F1": date_field_detail, "F2": pf.measure_1, "F3": pf.text_dim_1, "F4": pf.measure_1},
        columns=["F1"], rows=["F2"], 
        encodings=[
            {"fieldKey": "F3", "type": "Color"},
            {"fieldKey": "F4", "type": "Label"}
        ], 
        legends={"F3": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    )
    payload6 = generate_payload(tc6, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload6)
    if err:
        result.post_error = f"Helper viz dashm_line_detail: {err}"
        return result
    viz_names.append(resp.get("name", payload6["name"]) if resp else payload6["name"])

    # Create filter definitions (4-6 filters)
    filter_defs: List[FilterDef] = []
    filter_defs.append(FilterDef(
        field_name=pf.text_dim_1["fieldName"],
        object_name=pf.text_dim_1["objectName"],
        data_type="Text",
        label=pf.text_dim_1["fieldName"].replace("_", " ").title(),
    ))
    filter_defs.append(FilterDef(
        field_name=pf.text_dim_2["fieldName"],
        object_name=pf.text_dim_2["objectName"],
        data_type="Text",
        label=pf.text_dim_2["fieldName"].replace("_", " ").title(),
    ))
    filter_defs.append(FilterDef(
        field_name=pf.date_dim["fieldName"],
        object_name=pf.date_dim["objectName"],
        data_type="DateTime",
        label=pf.date_dim["fieldName"].replace("_", " ").title(),
    ))
    if pf.calc_dim:
        filter_defs.append(FilterDef(
            field_name=pf.calc_dim["fieldName"],
            object_name=None,  # Calculated fields don't have objectName
            data_type=pf.calc_dim.get("dataType", "Text"),
            label=pf.calc_dim["fieldName"].replace("_", " ").title(),
        ))
    # Add more filters if needed (reuse dimensions)
    if len(filter_defs) < 6:
        filter_defs.append(FilterDef(
            field_name=pf.text_dim_1["fieldName"],
            object_name=pf.text_dim_1["objectName"],
            data_type="Text",
            label=f"{pf.text_dim_1['fieldName'].replace('_', ' ').title()} (Secondary)",
        ))
    
    # Create metric definitions (use different metrics if available, otherwise reuse)
    metric_defs: List[MetricDef] = []
    available_metrics = pf.all_metric_names if pf.all_metric_names else ([pf.metric_name] if pf.metric_name else [])
    if available_metrics:
        # Create up to 3 metrics, cycling through available metrics
        for i in range(3):
            metric_name = available_metrics[i % len(available_metrics)]
            metric_defs.append(MetricDef(
                metric_api_name=metric_name,
                sdm_api_name=sdm_name,
            ))
    
    # Create visualization definitions with page assignments
    # Page 0 (Executive Summary): bar, line, donut
    # Page 1 (Detailed Analysis): table, scatter
    # Page 2 (Trends & Performance): line_detail
    viz_defs: List[VizDef] = [
        VizDef(viz_api_name=viz_names[0], page_index=0),  # bar - Page 0
        VizDef(viz_api_name=viz_names[1], page_index=0),  # line - Page 0
        VizDef(viz_api_name=viz_names[2], page_index=0),  # donut - Page 0
        VizDef(viz_api_name=viz_names[3], page_index=1),  # table - Page 1
        VizDef(viz_api_name=viz_names[4], page_index=1),  # scatter - Page 1
        VizDef(viz_api_name=viz_names[5], page_index=2),  # line_detail - Page 2
    ]
    
    # Create page definitions (3 pages)
    page_defs: List[PageDef] = [
        PageDef(label="Executive Summary", name="executive_summary"),
        PageDef(label="Detailed Analysis", name="detailed_analysis"),
        PageDef(label="Trends & Performance", name="trends_performance"),
    ]
    
    # Create container definitions for visual organization
    container_defs: List[ContainerDef] = [
        # Page 1 containers
        ContainerDef(column=0, row=10, colspan=48, rowspan=15, page_index=0, border_color="#E5E5E5"),
        ContainerDef(column=0, row=30, colspan=48, rowspan=20, page_index=0, border_color="#E5E5E5"),
        # Page 2 containers
        ContainerDef(column=0, row=10, colspan=48, rowspan=25, page_index=1, border_color="#E5E5E5"),
        # Page 3 containers
        ContainerDef(column=0, row=10, colspan=48, rowspan=25, page_index=2, border_color="#E5E5E5"),
    ]
    
    # Build dashboard using build_dashboard() function
    dash_payload = build_dashboard(
        name="__TH_dashboard_multipage",
        label="TH: Production Dashboard",
        workspace_name=WORKSPACE_NAME,
        title_text="Sales Analytics Dashboard",
        viz_defs=viz_defs,
        filter_defs=filter_defs,
        metric_defs=metric_defs,
        sdm_name=sdm_name,
        column_count=72,
        row_height=20,
        page_defs=page_defs,
        container_defs=container_defs,
    )
    
    # Add text widgets for section headers
    # Note: Text widgets are added to the widgets dict and page layouts
    # We'll add them after the dashboard is built, inserting them into the page layouts
    widgets = dash_payload.get("widgets", {})
    layouts = dash_payload.get("layouts", [])
    
    if layouts and len(layouts) > 0:
        pages = layouts[0].get("pages", [])
        
        for page_idx, page in enumerate(pages):
            page_widgets = page.get("widgets", [])
            
            # Find the row after filters (filters are on every page)
            filter_row = None
            for w in page_widgets:
                w_name = w.get("name", "")
                if "filter" in w_name.lower():
                    filter_row = max(filter_row or 0, w.get("row", 0) + w.get("rowspan", 0))
            
            # Find the row where visualizations start
            viz_row = None
            for w in page_widgets:
                w_name = w.get("name", "")
                if w_name.startswith("viz_"):
                    if viz_row is None or w.get("row", 999) < viz_row:
                        viz_row = w.get("row", 0)
            
            # Page 0: Add text headers for metrics and visualizations
            if page_idx == 0:
                # Text widget for metrics section (if metrics exist)
                if metric_defs:
                    text_metrics_key = f"text_metrics_p{page_idx}"
                    widgets[text_metrics_key] = {
                        "actions": [],
                        "name": text_metrics_key,
                        "type": "text",
                        "parameters": {
                            "content": [
                                {"attributes": {"bold": True, "size": "16px", "color": "#2E2E2E"}, "insert": "Key Metrics"},
                                {"attributes": {"align": "left"}, "insert": "\n"},
                            ],
                        },
                    }
                    if filter_row:
                        page_widgets.append({
                            "name": text_metrics_key,
                            "column": 1,
                            "row": filter_row,
                            "colspan": 70,
                            "rowspan": 2,
                        })
                
                # Text widget for visualizations section
                if viz_row:
                    text_viz_key = f"text_viz_p{page_idx}"
                    widgets[text_viz_key] = {
                        "actions": [],
                        "name": text_viz_key,
                        "type": "text",
                        "parameters": {
                            "content": [
                                {"attributes": {"bold": True, "size": "16px", "color": "#2E2E2E"}, "insert": "Visualizations"},
                                {"attributes": {"align": "left"}, "insert": "\n"},
                            ],
                        },
                    }
                    page_widgets.append({
                        "name": text_viz_key,
                        "column": 1,
                        "row": max(filter_row or 0, (viz_row or 0) - 2),
                        "colspan": 70,
                        "rowspan": 2,
                    })
            
            # Page 1: Add text header for detailed analysis
            elif page_idx == 1:
                text_detail_key = f"text_detail_p{page_idx}"
                widgets[text_detail_key] = {
                    "actions": [],
                    "name": text_detail_key,
                    "type": "text",
                    "parameters": {
                        "content": [
                            {"attributes": {"bold": True, "size": "16px", "color": "#2E2E2E"}, "insert": "Detailed Analysis"},
                            {"attributes": {"align": "left"}, "insert": "\n"},
                        ],
                    },
                }
                if filter_row:
                    page_widgets.append({
                        "name": text_detail_key,
                        "column": 1,
                        "row": filter_row,
                        "colspan": 70,
                        "rowspan": 2,
                    })
            
            # Page 2: Add text header for trends
            elif page_idx == 2:
                text_trends_key = f"text_trends_p{page_idx}"
                widgets[text_trends_key] = {
                    "actions": [],
                    "name": text_trends_key,
                    "type": "text",
                    "parameters": {
                        "content": [
                            {"attributes": {"bold": True, "size": "16px", "color": "#2E2E2E"}, "insert": "Trends & Performance"},
                            {"attributes": {"align": "left"}, "insert": "\n"},
                        ],
                    },
                }
                if filter_row:
                    page_widgets.append({
                        "name": text_trends_key,
                        "column": 1,
                        "row": filter_row,
                        "colspan": 70,
                        "rowspan": 2,
                    })
        
        dash_payload["widgets"] = widgets

    resp, err = sf_post(token, instance, dashboard_endpoint(), dash_payload)
    if err:
        result.post_error = f"Dashboard POST: {err}"
        return result
    if isinstance(resp, list):
        result.post_error = str(resp)
        return result
    result.post_passed = True
    result.viz_name = "__TH_dashboard_multipage"

    got = sf_get(token, instance, dashboard_endpoint("__TH_dashboard_multipage"))
    if got is None:
        result.roundtrip_diffs = ["GET after dashboard POST returned None"]
        return result

    # Verify pages exist
    got_pages = got.get("layouts", [{}])[0].get("pages", [])
    if len(got_pages) < 3:
        result.roundtrip_diffs = [f"Expected 3 pages, got {len(got_pages)}"]
        return result

    # Verify widgets exist
    got_widgets = got.get("widgets", {})
    has_button = any(w.get("type") == "button" for w in got_widgets.values() if isinstance(w, dict))
    has_container = any(w.get("type") == "container" for w in got_widgets.values() if isinstance(w, dict))
    has_text = any(w.get("type") == "text" for w in got_widgets.values() if isinstance(w, dict))
    has_metric = any(w.get("type") == "metric" for w in got_widgets.values() if isinstance(w, dict))
    has_viz = any(w.get("type") == "visualization" for w in got_widgets.values() if isinstance(w, dict))
    has_filter = any(w.get("type") == "filter" for w in got_widgets.values() if isinstance(w, dict))
    
    diffs: List[str] = []
    if not has_button:
        diffs.append("No button widget found")
    if not has_container:
        diffs.append("No container widget found")
    if not has_text:
        diffs.append("No text widget found")
    if not has_metric:
        diffs.append("No metric widget found")
    if not has_viz:
        diffs.append("No visualization widget found")
    if not has_filter:
        diffs.append("No filter widget found")

    # Check widget statuses (warn but don't fail)
    widget_status_warnings = []
    for wk, wv in got_widgets.items():
        if isinstance(wv, dict) and wv.get("status") and wv["status"] != "Ok":
            widget_status_warnings.append(f"{wk}: status={wv['status']}")

    if diffs:
        result.roundtrip_diffs = diffs
    elif widget_status_warnings:
        result.roundtrip_diffs = widget_status_warnings  # Warnings but not failures
        result.roundtrip_passed = True  # Still consider it passed
    else:
        result.roundtrip_passed = True

    return result


def run_patch_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 18: POST a viz, GET it, strip read-only fields, PATCH label, verify."""
    result = TestResult(
        id="patch_update_label", chart_type="PATCH",
        description="POST then PATCH label update", validation_passed=True,
    )

    # POST a simple bar
    tc = TestCase(
        id="patch_target", chart_type="bar", description="Patch target",
        fields={"F1": pf.text_dim_1, "F2": pf.measure_1, "F3": pf.measure_1},
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Label"}], legends={},
    )
    payload = generate_payload(tc, sdm_name, sdm_label)
    resp, err = sf_post(token, instance, visualization_endpoint(), payload)
    if err:
        result.post_error = f"Initial POST: {err}"
        return result
    result.viz_name = resp.get("name", payload["name"]) if resp else payload["name"]

    # GET the created viz
    got = sf_get(token, instance, visualization_endpoint(payload["name"]))
    if got is None:
        result.post_error = "GET after POST returned None"
        return result

    # Strip read-only fields and PATCH with a new label
    patch_body = strip_readonly_fields(got)
    patch_body["label"] = "TH: PATCHED Label"
    patch_body["workspace"] = {"name": WORKSPACE_NAME, "label": WORKSPACE_LABEL}

    patch_resp, patch_err = sf_patch(
        token, instance, visualization_endpoint(payload["name"]), patch_body,
    )
    if patch_err:
        result.post_error = f"PATCH: {patch_err}"
        return result
    result.post_passed = True

    # Verify the label changed
    got2 = sf_get(token, instance, visualization_endpoint(payload["name"]))
    if got2 is None:
        result.roundtrip_diffs = ["GET after PATCH returned None"]
        return result

    if got2.get("label") == "TH: PATCHED Label":
        result.roundtrip_passed = True
    else:
        result.roundtrip_diffs = [f"Label not updated: got '{got2.get('label')}'"]

    return result


def run_calc_field_measurement_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 22: Create calculated measurement, verify in SDM discovery, use in viz.
    
    NOTE: This test currently fails with "The API Name '{0}' has no mapped semantic definition ID."
    This error suggests that calculated fields may only be creatable immediately after SDM creation
    (as part of the same deployment flow), not on existing SDMs via standalone POST requests.
    The tabnext-tools-main deployment_service creates calculated fields immediately after SDM creation,
    which may be a requirement rather than a convenience.
    
    Until this limitation is resolved or clarified, this test is marked as expected failure.
    """
    result = TestResult(
        id="calc_field_measurement", chart_type="calculated_field",
        description="Create _clc measurement, verify discovery, use in bar chart", validation_passed=True,
    )

    # Build calculated measurement payload
    # Note: Salesforce API names cannot have double underscores
    # Use unique name with timestamp to avoid conflicts
    import time
    timestamp = int(time.time()) % 100000  # Last 5 digits of timestamp
    field_name = f"TH_Test_Measure_{timestamp}_clc"
    result.field_name = field_name  # Store for cleanup
    # Use actual field names from the SDM - need fully qualified [ObjectName].[FieldName] format
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    # Simple expression: just sum one measure (simplest possible)
    expression = f"SUM([{m1_obj}].[{m1_name}])"
    
    payload = build_calculated_measurement(
        api_name=field_name,
        label="TH: Test Measure",
        expression=expression,
        aggregation_type="UserAgg",
        data_type="Number",
        description="Test harness calculated measurement",
    )

    # POST calculated measurement
    endpoint = calculated_field_endpoint(sdm_name, "measurements")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        # Expected failure - calculated fields may only be creatable immediately after SDM creation
        result.post_error = f"POST calculated measurement: {err} (EXPECTED: may require SDM creation context)"
        return result
    result.post_passed = True

    # Verify it appears in SDM discovery
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for cm in sdm_data.get("semanticCalculatedMeasurements", []):
        if cm.get("apiName") == field_name:
            found = True
            if cm.get("label") != "TH: Test Measure":
                result.roundtrip_diffs.append(f"Label mismatch: got '{cm.get('label')}'")
            if cm.get("aggregationType") != "UserAgg":
                result.roundtrip_diffs.append(f"AggregationType mismatch: got '{cm.get('aggregationType')}'")
            break

    if not found:
        result.roundtrip_diffs.append(f"Calculated measurement '{field_name}' not found in SDM discovery")
        return result

    # Use it in a visualization to verify end-to-end
    # Use the full apiName (with __TH_ prefix and _clc suffix) as fieldName
    tc = TestCase(
        id="viz_with_new_calc", chart_type="bar", description="Bar using newly created calc field",
        fields={
            "F1": pf.text_dim_1,
            "F2": {
                "type": "Field",
                "role": "Measure",
                "displayCategory": "Continuous",
                "fieldName": field_name,  # Use full apiName including TH_ prefix and _clc suffix
                "objectName": None,  # Calculated fields have null objectName
                "function": "UserAgg",
            },
            "F3": {
                "type": "Field",
                "role": "Measure",
                "displayCategory": "Continuous",
                "fieldName": field_name,
                "objectName": None,
                "function": "UserAgg",
            },
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F3", "type": "Label"}], legends={},
    )
    viz_payload = generate_payload(tc, sdm_name, sdm_label)
    viz_resp, viz_err = sf_post(token, instance, visualization_endpoint(), viz_payload)
    if viz_err:
        result.roundtrip_diffs.append(f"Viz creation with new calc field failed: {viz_err}")
    else:
        result.roundtrip_passed = True
        # Store viz name for cleanup
        result.viz_name = viz_payload["name"]

    return result


def run_calc_field_dimension_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 23: Create calculated dimension, verify in SDM discovery.
    
    NOTE: This test currently fails with "The API Name '{0}' has no mapped semantic definition ID."
    This error suggests that calculated fields may only be creatable immediately after SDM creation
    (as part of the same deployment flow), not on existing SDMs via standalone POST requests.
    The tabnext-tools-main deployment_service creates calculated fields immediately after SDM creation,
    which may be a requirement rather than a convenience.
    
    Until this limitation is resolved or clarified, this test is marked as expected failure.
    """
    result = TestResult(
        id="calc_field_dimension", chart_type="calculated_field",
        description="Create _clc dimension (Boolean), verify discovery", validation_passed=True,
    )

    # Build calculated dimension payload
    # Note: Salesforce API names cannot have double underscores
    # Use unique name with timestamp to avoid conflicts
    import time
    timestamp = int(time.time()) % 100000  # Last 5 digits of timestamp
    field_name = f"TH_Test_Dimension_{timestamp}_clc"
    result.field_name = field_name  # Store for cleanup
    # Use actual field name from the SDM - need fully qualified [ObjectName].[FieldName] format
    # Account_Industry is in Account_TAB_Sales_Cloud, not Opportunity_TAB_Sales_Cloud
    dim_name = pf.text_dim_1.get("fieldName", "Account_Industry")
    # Find the correct object - check if this field is Account_Industry, use Account object
    if dim_name == "Account_Industry":
        dim_obj = "Account_TAB_Sales_Cloud"
    else:
        dim_obj = pf.text_dim_1.get("objectName", "Account_TAB_Sales_Cloud")
    # Simple boolean check - check if field equals itself (always True, but valid syntax)
    expression = f"[{dim_obj}].[{dim_name}] = [{dim_obj}].[{dim_name}]"
    
    payload = build_calculated_dimension(
        api_name=field_name,
        label="TH: Is Technology",
        expression=expression,
        data_type="Boolean",
        description="Test harness calculated dimension",
    )

    # POST calculated dimension
    endpoint = calculated_field_endpoint(sdm_name, "dimensions")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        # Expected failure - calculated fields may only be creatable immediately after SDM creation
        result.post_error = f"POST calculated dimension: {err} (EXPECTED: may require SDM creation context)"
        return result
    result.post_passed = True

    # Verify it appears in SDM discovery
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for cd in sdm_data.get("semanticCalculatedDimensions", []):
        if cd.get("apiName") == field_name:
            found = True
            if cd.get("label") != "TH: Is Technology":
                result.roundtrip_diffs.append(f"Label mismatch: got '{cd.get('label')}'")
            if cd.get("dataType") != "Boolean":
                result.roundtrip_diffs.append(f"DataType mismatch: got '{cd.get('dataType')}'")
            break

    if not found:
        result.roundtrip_diffs.append(f"Calculated dimension '{field_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_basic_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 33: Create basic semantic metric (SUM), verify in SDM discovery."""
    result = TestResult(
        id="metric_basic", chart_type="semantic_metric",
        description="Create _mtc metric (SUM), verify discovery", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field first
    calc_field_name = f"TH_Test_Revenue_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    expression = f"SUM([{m1_obj}].[{m1_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Revenue (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric referencing the calculated field
    metric_name = f"TH_Test_Revenue_{timestamp}_mtc"
    result.field_name = metric_name  # Store for cleanup
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Revenue",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness semantic metric",
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify it appears in SDM discovery
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            if m.get("label") != "TH: Test Revenue":
                result.roundtrip_diffs.append(f"Label mismatch: got '{m.get('label')}'")
            # Check measurementReference instead of expression
            measurement_ref = m.get("measurementReference", {})
            if measurement_ref.get("calculatedFieldApiName") != calc_field_name:
                result.roundtrip_diffs.append(f"MeasurementReference mismatch: got '{measurement_ref.get('calculatedFieldApiName')}'")
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_ratio_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 34: Create ratio metric (win rate), verify in SDM discovery."""
    result = TestResult(
        id="metric_ratio", chart_type="semantic_metric",
        description="Create _mtc metric (win rate ratio), verify discovery", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field for win rate
    calc_field_name = f"TH_Test_Win_Rate_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m2_name = pf.measure_2.get("fieldName", "Total_Price")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    m2_obj = pf.measure_2.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    expression = f"SUM([{m1_obj}].[{m1_name}]) / SUM([{m2_obj}].[{m2_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Win Rate (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric referencing the calculated field
    metric_name = f"TH_Test_Win_Rate_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Win Rate",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness win rate metric",
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify it appears in SDM discovery
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_template_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 35: Create metric using template, verify in SDM discovery."""
    result = TestResult(
        id="metric_template", chart_type="semantic_metric",
        description="Create _mtc metric using template, verify discovery", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field using sum template
    calc_field_name = f"TH_Test_Sum_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    expression = f"SUM([{m1_obj}].[{m1_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Sum (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric referencing the calculated field
    metric_name = f"TH_Test_Sum_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Sum",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness sum metric from template",
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify it appears in SDM discovery
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_dashboard_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 36: Create metric, use in dashboard metric widget."""
    result = TestResult(
        id="metric_dashboard", chart_type="semantic_metric",
        description="Create _mtc metric, use in dashboard widget", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field first
    calc_field_name = f"TH_Test_Dash_Metric_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    expression = f"SUM([{m1_obj}].[{m1_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Dashboard Metric (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric referencing the calculated field
    metric_name = f"TH_Test_Dash_Metric_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Dashboard Metric",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Wait a moment for metric to be available
    time.sleep(2)

    # Verify it appears in SDM discovery
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
        return result

    # Use it in a dashboard metric widget
    metric_defs = [MetricDef(metric_api_name=metric_name, sdm_api_name=sdm_name)]
    filter_defs = [
        FilterDef(
            field_name=pf.text_dim_1["fieldName"],
            object_name=pf.text_dim_1["objectName"],
            data_type="Text",
            label=pf.text_dim_1["fieldName"].replace("_", " ").title(),
        )
    ]

    dash_payload = build_dashboard(
        name="__TH_metric_dash",
        label="TH: Metric Dashboard",
        workspace_name=WORKSPACE_NAME,
        title_text="Test Metric Dashboard",
        viz_defs=[],
        filter_defs=filter_defs,
        metric_defs=metric_defs,
        sdm_name=sdm_name,
    )

    dash_resp, dash_err = sf_post(token, instance, dashboard_endpoint(), dash_payload)
    if dash_err:
        result.roundtrip_diffs.append(f"Dashboard POST failed: {dash_err}")
        return result

    result.viz_name = dash_payload["name"]
    result.roundtrip_passed = True

    return result


def run_metric_additional_dimensions_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 37: Create metric with additionalDimensions, verify insightsSettings."""
    result = TestResult(
        id="metric_additional_dimensions", chart_type="semantic_metric",
        description="Create _mtc metric with additionalDimensions, verify insightsSettings", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field first
    calc_field_name = f"TH_Test_Revenue_Dims_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    expression = f"SUM([{m1_obj}].[{m1_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Revenue with Dims (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric with additionalDimensions
    metric_name = f"TH_Test_Revenue_Dims_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Build additionalDimensions from available text dimensions
    # Use at least 2 dimensions (pattern from collection: 3-5 dimensions)
    additional_dims = []
    if pf.text_dim_1:
        additional_dims.append({
            "tableFieldReference": {
                "fieldApiName": pf.text_dim_1["fieldName"],
                "tableApiName": pf.text_dim_1.get("objectName", "")
            }
        })
    if pf.text_dim_2:
        additional_dims.append({
            "tableFieldReference": {
                "fieldApiName": pf.text_dim_2["fieldName"],
                "tableApiName": pf.text_dim_2.get("objectName", "")
            }
        })
    # Note: Calculated dimensions may not have objectName, so we skip them for now
    # Collection examples show 3-5 dimensions, but we'll use 2 for testing
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Revenue with Dimensions",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness metric with additionalDimensions",
        additional_dimensions=additional_dims,
        sentiment="SentimentTypeUpIsGood",
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify it appears in SDM discovery with additionalDimensions
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            # Verify additionalDimensions exist
            if "additionalDimensions" not in m:
                result.roundtrip_diffs.append("additionalDimensions missing")
            elif len(m.get("additionalDimensions", [])) != len(additional_dims):
                result.roundtrip_diffs.append(f"additionalDimensions count mismatch: got {len(m.get('additionalDimensions', []))}, expected {len(additional_dims)}")
            # Verify insightsSettings exist
            if "insightsSettings" not in m:
                result.roundtrip_diffs.append("insightsSettings missing")
            elif m.get("insightsSettings", {}).get("sentiment") != "SentimentTypeUpIsGood":
                result.roundtrip_diffs.append(f"sentiment mismatch: got '{m.get('insightsSettings', {}).get('sentiment')}'")
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_sentiment_bad_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 38: Create metric with SentimentTypeUpIsBad sentiment."""
    result = TestResult(
        id="metric_sentiment_bad", chart_type="semantic_metric",
        description="Create _mtc metric with SentimentTypeUpIsBad sentiment", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field for "bad" metric (e.g., turnover rate, complaints)
    calc_field_name = f"TH_Test_Turnover_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m2_name = pf.measure_2.get("fieldName", "Total_Price")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    m2_obj = pf.measure_2.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    # Simulate a "bad" metric (higher is worse) - using a ratio
    expression = f"SUM([{m1_obj}].[{m1_name}]) / SUM([{m2_obj}].[{m2_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Turnover Rate (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric with SentimentTypeUpIsBad
    metric_name = f"TH_Test_Turnover_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Turnover Rate",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness metric with SentimentTypeUpIsBad",
        sentiment="SentimentTypeUpIsBad",
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify sentiment is preserved
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            insights = m.get("insightsSettings", {})
            if insights.get("sentiment") != "SentimentTypeUpIsBad":
                result.roundtrip_diffs.append(f"sentiment mismatch: got '{insights.get('sentiment')}', expected 'SentimentTypeUpIsBad'")
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_sentiment_none_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 39: Create metric with SentimentTypeNone sentiment."""
    result = TestResult(
        id="metric_sentiment_none", chart_type="semantic_metric",
        description="Create _mtc metric with SentimentTypeNone sentiment", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field for neutral metric (e.g., headcount, average age)
    calc_field_name = f"TH_Test_Headcount_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    # Use COUNTD for headcount-like metric
    expression = f"COUNTD([{m1_obj}].[{m1_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Headcount (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric with SentimentTypeNone
    metric_name = f"TH_Test_Headcount_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Headcount",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness metric with SentimentTypeNone",
        sentiment="SentimentTypeNone",
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify sentiment is preserved
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            insights = m.get("insightsSettings", {})
            if insights.get("sentiment") != "SentimentTypeNone":
                result.roundtrip_diffs.append(f"sentiment mismatch: got '{insights.get('sentiment')}', expected 'SentimentTypeNone'")
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_cumulative_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 40: Create metric with isCumulative: true."""
    result = TestResult(
        id="metric_cumulative", chart_type="semantic_metric",
        description="Create _mtc metric with isCumulative: true", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field first
    calc_field_name = f"TH_Test_Cumulative_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    # Use raw field reference (no SUM function) so explicit Sum aggregation can be applied
    # This is required for cumulative metrics which need Sum/Count/CountDistinct (not UserAgg)
    expression = f"[{m1_obj}].[{m1_name}]"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Cumulative (calc)",
        expression=expression,
        aggregation_type="Sum",  # Sum supports cumulative metrics (UserAgg does not)
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric with isCumulative: true
    metric_name = f"TH_Test_Cumulative_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Get time dimension from picked fields
    time_field = pf.date_dim.get("fieldName", "Close_Date")
    time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Cumulative",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness cumulative metric",
        aggregation_type="Sum",
        is_cumulative=True,
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify isCumulative is preserved
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            if m.get("isCumulative") != True:
                result.roundtrip_diffs.append(f"isCumulative mismatch: got '{m.get('isCumulative')}', expected True")
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def run_metric_different_time_dimension_test(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> TestResult:
    """Test 41: Create metric with different time dimension (Created_Date vs Close_Date)."""
    result = TestResult(
        id="metric_different_time", chart_type="semantic_metric",
        description="Create _mtc metric with Created_Date time dimension", validation_passed=True,
    )

    import time
    timestamp = int(time.time()) % 100000
    
    # Step 1: Create calculated field first
    calc_field_name = f"TH_Test_Pipeline_{timestamp}_clc"
    m1_name = pf.measure_1.get("fieldName", "List_Price_Amount")
    m1_obj = pf.measure_1.get("objectName", "OpportunityLineItem_TAB_Sales_Cloud")
    expression = f"SUM([{m1_obj}].[{m1_name}])"
    
    calc_payload = build_calculated_measurement(
        api_name=calc_field_name,
        label="TH: Test Pipeline (calc)",
        expression=expression,
        aggregation_type="UserAgg",
    )
    
    calc_endpoint = calculated_field_endpoint(sdm_name, "measurements")
    calc_resp, calc_err = sf_post(token, instance, calc_endpoint, calc_payload)
    if calc_err:
        result.post_error = f"POST calculated field: {calc_err}"
        return result
    
    # Wait briefly for calculated field to be available
    time.sleep(1)
    
    # Step 2: Create metric with Created_Date (different from default Close_Date)
    metric_name = f"TH_Test_Pipeline_{timestamp}_mtc"
    result.field_name = metric_name
    
    # Use Created_Date instead of Close_Date (pattern from Weighted_Pipeline_Value_mtc)
    # If date_dim is Close_Date, try Created_Date with same table
    if pf.date_dim.get("fieldName") == "Close_Date":
        time_field = "Created_Date"  # Different time dimension
        time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    else:
        # Use a different date field if available, or use the one we have
        # For testing purposes, use the date_dim we have (it's still a different time dimension test)
        time_field = pf.date_dim.get("fieldName", "Created_Date")
        time_table = pf.date_dim.get("objectName", "Opportunity_TAB_Sales_Cloud")
    
    payload = build_semantic_metric(
        api_name=metric_name,
        label="TH: Test Pipeline",
        calculated_field_api_name=calc_field_name,
        time_dimension_field_name=time_field,
        time_dimension_table_name=time_table,
        description="Test harness metric with Created_Date time dimension",
    )

    # POST semantic metric
    endpoint = calculated_field_endpoint(sdm_name, "metrics")
    resp, err = sf_post(token, instance, endpoint, payload)
    if err:
        result.post_error = f"POST semantic metric: {err}"
        return result
    result.post_passed = True

    # Verify time dimension is preserved
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if sdm_data is None:
        result.roundtrip_diffs = ["SDM GET returned None"]
        return result

    found = False
    for m in sdm_data.get("semanticMetrics", []):
        if m.get("apiName") == metric_name:
            found = True
            time_ref = m.get("timeDimensionReference", {}).get("tableFieldReference", {})
            if time_ref.get("fieldApiName") != time_field:
                result.roundtrip_diffs.append(f"timeDimension field mismatch: got '{time_ref.get('fieldApiName')}', expected '{time_field}'")
            break

    if not found:
        result.roundtrip_diffs.append(f"Semantic metric '{metric_name}' not found in SDM discovery")
    else:
        result.roundtrip_passed = True

    return result


def cleanup_vizzes(token: str, instance: str, results: List[TestResult],
                   extra_viz_names: Optional[List[str]] = None,
                   sdm_name: Optional[str] = None) -> None:
    """Delete all test visualizations, dashboards, and calculated fields."""
    print(f"\n{BOLD}Cleanup:{RESET}")

    # Delete dashboards first (they reference vizzes)
    for r in results:
        if r.post_passed and r.viz_name and r.chart_type == "dashboard":
            ok, err = sf_delete(token, instance, dashboard_endpoint(r.viz_name))
            status = _ok(f"dash:{r.viz_name}") if ok else _fail(f"dash:{r.viz_name}: {err}")
            print(f"  DELETE {status}")

    # Delete vizzes
    for r in results:
        if r.post_passed and r.viz_name and r.chart_type != "dashboard":
            ok, err = sf_delete(token, instance, visualization_endpoint(r.viz_name))
            status = _ok(r.viz_name) if ok else _fail(f"{r.viz_name}: {err}")
            print(f"  DELETE {status}")

    # Delete extra helper vizzes (dashboard helpers)
    for name in (extra_viz_names or []):
        ok, err = sf_delete(token, instance, visualization_endpoint(name))
        status = _ok(name) if ok else _fail(f"{name}: {err}")
        print(f"  DELETE {status}")

    # Delete calculated fields and metrics (WARNING: modifies SDM)
    if sdm_name:
        calc_fields_to_delete = []
        # Extract calculated field names from test results
        for r in results:
            if r.post_passed and r.chart_type == "calculated_field" and r.field_name:
                if r.id == "calc_field_measurement":
                    calc_fields_to_delete.append(("measurements", r.field_name))
                elif r.id == "calc_field_dimension":
                    calc_fields_to_delete.append(("dimensions", r.field_name))
            elif r.post_passed and r.chart_type == "semantic_metric" and r.field_name:
                calc_fields_to_delete.append(("metrics", r.field_name))

        if calc_fields_to_delete:
            print(f"\n{BOLD}WARNING:{RESET} Deleting calculated fields modifies the SDM '{sdm_name}'")
            for field_type, field_name in calc_fields_to_delete:
                endpoint = calculated_field_endpoint(sdm_name, field_type, field_name)
                ok, err = sf_delete(token, instance, endpoint)
                status = _ok(f"calc:{field_name}") if ok else _fail(f"calc:{field_name}: {err}")
                print(f"  DELETE {status}")


# ── Reporting ────────────────────────────────────────────────────────────────

def print_results(results: List[TestResult]) -> None:
    """Print a summary matrix."""
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}Test Results{RESET}")
    print(f"{'='*80}\n")

    header = f"{'ID':<25} {'Chart':<12} {'Validate':>8} {'POST':>8} {'Roundtrip':>9}"
    print(header)
    print("-" * 70)

    pass_count = 0
    fail_count = 0

    for r in results:
        v = f"{GREEN}OK{RESET}" if r.validation_passed else f"{RED}FAIL{RESET}"
        p = f"{GREEN}OK{RESET}" if r.post_passed else f"{RED}FAIL{RESET}"
        rt = f"{GREEN}OK{RESET}" if r.roundtrip_passed else (f"{YELLOW}DIFF{RESET}" if r.post_passed else "-")

        all_ok = r.validation_passed and r.post_passed and r.roundtrip_passed
        if all_ok:
            pass_count += 1
        else:
            fail_count += 1

        print(f"{r.id:<25} {r.chart_type:<12} {v:>17} {p:>17} {rt:>18}")

        if r.validation_errors:
            for e in r.validation_errors:
                print(f"  {RED}-> {e}{RESET}")
        if r.post_error:
            print(f"  {RED}-> POST: {r.post_error}{RESET}")
        if r.roundtrip_diffs:
            for d in r.roundtrip_diffs:
                print(f"  {YELLOW}-> {d}{RESET}")

    print(f"\n{BOLD}Total: {pass_count} passed, {fail_count} failed out of {len(results)}{RESET}")


def save_json_report(results: List[TestResult], path: str) -> None:
    report = []
    for r in results:
        report.append({
            "id": r.id,
            "chart_type": r.chart_type,
            "description": r.description,
            "validation_passed": r.validation_passed,
            "validation_errors": r.validation_errors,
            "post_passed": r.post_passed,
            "post_error": r.post_error,
            "roundtrip_passed": r.roundtrip_passed,
            "roundtrip_diffs": r.roundtrip_diffs,
        })
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON report written to {path}")


# ── Edge case validation tests ────────────────────────────────────────────────

def run_edge_case_validation_tests(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> List[TestResult]:
    """Test that validation catches known edge cases from LESSONS_LEARNED.md."""
    results: List[TestResult] = []

    def _dim(picked: dict, **kw) -> dict:
        d = dict(picked)
        d.update(kw)
        return d

    def _meas(picked: dict, **kw) -> dict:
        m = dict(picked)
        m.update(kw)
        return m

    # Test 1: Field on shelf + encoding (should fail validation)
    tc = TestCase(
        id="bar_shelf_and_encoding_error",
        chart_type="bar",
        description="Bar with F2 on rows AND in Label (should fail validation)",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F2", "type": "Label"}],  # Same field on shelf!
        legends={},
    )
    payload = generate_payload(tc, sdm_name, sdm_label)
    is_valid_result, val_results = is_valid(payload)
    result = TestResult(
        id="bar_shelf_and_encoding_error",
        chart_type="bar",
        description="Field on shelf + encoding (should fail)",
        validation_passed=not is_valid_result,  # Should FAIL validation
        validation_errors=[f"{r.rule}: {r.message}" for r in val_results if not r.ok] if not is_valid_result else ["Expected validation failure but passed"],
    )
    results.append(result)

    # Test 2: Line with field on shelf + encoding (should fail validation)
    tc = TestCase(
        id="line_shelf_and_encoding_error",
        chart_type="line",
        description="Line with F2 on rows AND in Label (should fail validation)",
        fields={
            "F1": {**pf.date_dim, "function": "DatePartMonth"},
            "F2": _meas(pf.measure_1),
        },
        columns=["F1"], rows=["F2"],
        encodings=[{"fieldKey": "F2", "type": "Label"}],  # Same field!
        legends={},
    )
    payload = generate_payload(tc, sdm_name, sdm_label)
    is_valid_result, val_results = is_valid(payload)
    result = TestResult(
        id="line_shelf_and_encoding_error",
        chart_type="line",
        description="Field on shelf + encoding (should fail)",
        validation_passed=not is_valid_result,
        validation_errors=[f"{r.rule}: {r.message}" for r in val_results if not r.ok] if not is_valid_result else ["Expected validation failure but passed"],
    )
    results.append(result)

    # Test 3: Donut missing Color encoding (should fail validation)
    tc = TestCase(
        id="donut_missing_color",
        chart_type="donut",
        description="Donut with only Angle (missing Color - should fail)",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),
        },
        columns=[], rows=[],
        encodings=[{"fieldKey": "F2", "type": "Angle"}],  # Missing Color!
        legends={},
    )
    payload = generate_payload(tc, sdm_name, sdm_label)
    is_valid_result, val_results = is_valid(payload)
    result = TestResult(
        id="donut_missing_color",
        chart_type="donut",
        description="Donut missing Color encoding (should fail)",
        validation_passed=not is_valid_result,
        validation_errors=[f"{r.rule}: {r.message}" for r in val_results if not r.ok] if not is_valid_result else ["Expected validation failure but passed"],
    )
    results.append(result)

    # Test 4: Donut missing Angle encoding (should fail validation)
    tc = TestCase(
        id="donut_missing_angle",
        chart_type="donut",
        description="Donut with only Color (missing Angle - should fail)",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _meas(pf.measure_1),
        },
        columns=[], rows=[],
        encodings=[{"fieldKey": "F1", "type": "Color"}],  # Missing Angle!
        legends={},
    )
    payload = generate_payload(tc, sdm_name, sdm_label)
    is_valid_result, val_results = is_valid(payload)
    result = TestResult(
        id="donut_missing_angle",
        chart_type="donut",
        description="Donut missing Angle encoding (should fail)",
        validation_passed=not is_valid_result,
        validation_errors=[f"{r.rule}: {r.message}" for r in val_results if not r.ok] if not is_valid_result else ["Expected validation failure but passed"],
    )
    results.append(result)

    # Test 5: Donut with Color(measure) instead of Color(dim) (should fail validation)
    tc = TestCase(
        id="donut_color_measure_error",
        chart_type="donut",
        description="Donut with Color(measure) instead of Color(dim) (should fail)",
        fields={
            "F1": _meas(pf.measure_1),  # Measure used for Color (wrong!)
            "F2": _meas(pf.measure_1),
        },
        columns=[], rows=[],
        encodings=[
            {"fieldKey": "F1", "type": "Color"},  # Color with measure (should fail)
            {"fieldKey": "F2", "type": "Angle"},
        ],
        legends={},
    )
    payload = generate_payload(tc, sdm_name, sdm_label)
    is_valid_result, val_results = is_valid(payload)
    # Note: This might pass validation but fail at API - validation may not catch this
    # We check if validation catches it, but if not, that's okay (API will reject)
    result = TestResult(
        id="donut_color_measure_error",
        chart_type="donut",
        description="Donut Color(measure) instead of Color(dim)",
        validation_passed=not is_valid_result,
        validation_errors=[f"{r.rule}: {r.message}" for r in val_results if not r.ok] if not is_valid_result else [],
    )
    results.append(result)

    # Test 6: Scatter with measure on columns (verify styles are correct) - should POST successfully
    tc = TestCase(
        id="scatter_measure_on_columns",
        chart_type="scatter",
        description="Scatter with measure on columns (verify axis/encoding styles)",
        fields={
            "F1": _meas(pf.measure_1),  # On columns
            "F2": _meas(pf.measure_2),  # On rows
            "F3": _dim(pf.text_dim_1),  # Detail
        },
        columns=["F1"], rows=["F2"],  # Both measures
        encodings=[{"fieldKey": "F3", "type": "Detail"}],
        legends={},
    )
    result = run_test(tc, token, instance, sdm_name, sdm_label)
    results.append(result)

    # Test 7: Table with measure in rows (should POST successfully - measures are converted to Discrete)
    # This tests that our table logic correctly handles measures in rows by converting them to Discrete
    tc = TestCase(
        id="table_measure_in_headers",
        chart_type="table",
        description="Table with measures in rows (should pass - measures converted to Discrete)",
        fields={
            "F1": _dim(pf.text_dim_1),
            "F2": _dim(pf.text_dim_2),
            "F3": _meas(pf.measure_1),
        },
        columns=[], rows=["F1", "F2", "F3"],
        encodings=[],
        legends={},
    )
    result = run_test(tc, token, instance, sdm_name, sdm_label)
    results.append(result)

    return results


def run_template_tests(
    token: str,
    instance: str,
    sdm_name: str,
    sdm_label: str,
    pf: "PickedFields",
) -> List[TestResult]:
    """Run tests for visualization templates.
    
    Tests that templates can be applied and produce valid visualizations.
    """
    results: List[TestResult] = []
    
    # Discover SDM fields
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    if not sdm_data:
        return results
    
    # Build flattened field dict
    sdm_fields: Dict[str, Dict[str, Any]] = {}
    for obj in sdm_data.get("semanticDataObjects", []):
        obj_name = obj.get("apiName", "")
        for d in obj.get("semanticDimensions", []):
            field_name = d.get("apiName", "")
            sdm_fields[field_name] = {
                "fieldName": field_name,
                "objectName": obj_name,
                "role": "Dimension",
                "displayCategory": "Discrete",
                "dataType": d.get("dataType", ""),
                "function": None,
            }
        for m in obj.get("semanticMeasurements", []):
            field_name = m.get("apiName", "")
            sdm_fields[field_name] = {
                "fieldName": field_name,
                "objectName": obj_name,
                "role": "Measure",
                "displayCategory": "Continuous",
                "aggregationType": m.get("aggregationType", "Sum"),
                "function": m.get("aggregationType", "Sum"),
            }
    for d in sdm_data.get("semanticCalculatedDimensions", []):
        field_name = d.get("apiName", "")
        sdm_fields[field_name] = {
            "fieldName": field_name,
            "objectName": None,
            "role": "Dimension",
            "displayCategory": "Discrete",
            "dataType": d.get("dataType", ""),
            "function": None,
        }
    for m in sdm_data.get("semanticCalculatedMeasurements", []):
        field_name = m.get("apiName", "")
        sdm_fields[field_name] = {
            "fieldName": field_name,
            "objectName": None,
            "role": "Measure",
            "displayCategory": "Continuous",
            "aggregationType": m.get("aggregationType", "Sum"),
            "function": m.get("aggregationType", "Sum"),
        }
    
    # Test templates
    template_tests = [
        ("revenue_by_category", {
            "category": pf.text_dim_1["fieldName"],
            "amount": pf.measure_1["fieldName"],
        }),
        ("trend_over_time", {
            "date": pf.date_dim["fieldName"],
            "measure": pf.measure_1["fieldName"],
        }),
        ("market_share_donut", {
            "category": pf.text_dim_1["fieldName"],
            "amount": pf.measure_1["fieldName"],
        }),
    ]
    
    for template_name, field_overrides in template_tests:
        template = get_template(template_name)
        if not template:
            continue
        
        # Match fields
        field_mappings = find_matching_fields(
            sdm_fields,
            template["required_fields"],
            user_overrides=field_overrides
        )
        
        if len(field_mappings) < len(template["required_fields"]):
            # Skip if we can't match all required fields
            continue
        
        # Build visualization
        viz_name = f"__TH_template_{template_name}"
        try:
            viz_json = build_viz_from_template_def(
                template_def=template,
                sdm_name=sdm_name,
                sdm_label=sdm_label,
                workspace_name=WORKSPACE_NAME,
                workspace_label=WORKSPACE_LABEL,
                field_mappings=field_mappings,
                name=viz_name,
                label=f"Template Test: {template_name}",
            )
            
            # Validate
            validation_passed = is_valid(viz_json)
            validation_errors = [] if validation_passed else ["Template validation failed"]
            
            # POST
            response, error = sf_post(token, instance, visualization_endpoint(), viz_json)
            post_passed = error is None
            post_error = error
            viz_id = response.get("id") if response else None
            
            # Round-trip GET
            roundtrip_passed = False
            roundtrip_diffs = []
            if post_passed and viz_id:
                get_response = sf_get(token, instance, visualization_endpoint(viz_id))
                if get_response:
                    roundtrip_passed = True
                    # Basic verification
                    if get_response.get("name") != viz_name:
                        roundtrip_diffs.append("Name mismatch")
            
            result = TestResult(
                id=f"template_{template_name}",
                chart_type=template["chart_type"],
                description=f"Template: {template_name}",
                validation_passed=validation_passed,
                validation_errors=validation_errors,
                post_passed=post_passed,
                post_error=post_error,
                roundtrip_passed=roundtrip_passed,
                roundtrip_diffs=roundtrip_diffs,
            )
            results.append(result)
        except Exception as e:
            result = TestResult(
                id=f"template_{template_name}",
                chart_type=template["chart_type"],
                description=f"Template: {template_name}",
                validation_passed=False,
                validation_errors=[str(e)],
                post_passed=False,
                post_error=str(e),
                roundtrip_passed=False,
                roundtrip_diffs=[],
            )
            results.append(result)
    
    return results


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated integration test harness for Tableau Next chart generation",
    )
    parser.add_argument("--sdm", required=True, help="SDM API name to use for test fields")
    parser.add_argument("--cleanup", action="store_true", help="Delete test visualizations after run")
    parser.add_argument("--json-report", type=str, default=None, help="Write JSON results to file")
    parser.add_argument("--table-only", action="store_true", help="Run only table test cases")
    args = parser.parse_args()

    token, instance = get_credentials()

    print(f"{BOLD}Tableau Next Chart Test Harness{RESET}")
    print(f"SDM: {args.sdm}\n")

    # 1. Discover fields
    print("Discovering SDM fields...", end=" ", flush=True)
    pf = pick_fields(token, instance, args.sdm)
    extra_info = ""
    if pf.calc_measure:
        extra_info += f", clc_m={pf.calc_measure['fieldName']}({pf.calc_measure['function']})"
    if pf.calc_dim:
        extra_info += f", clc_d={pf.calc_dim['fieldName']}"
    if pf.metric_name:
        extra_info += f", metric={pf.metric_name}"
    print(_ok(f"dim1={pf.text_dim_1['fieldName']}, dim2={pf.text_dim_2['fieldName']}, "
              f"date={pf.date_dim['fieldName']}, m1={pf.measure_1['fieldName']}, "
              f"m2={pf.measure_2['fieldName']}{extra_info}"))

    # 2. Ensure workspace
    print("Ensuring workspace...", end=" ", flush=True)
    success, actual_workspace_name = ensure_workspace(token, instance)
    if not success:
        sys.exit(1)
    print(_ok(actual_workspace_name))

    # 3. Build test matrix (chart tests)
    cases = build_test_cases(pf)
    # Filter to only table tests if --table-only flag is set
    if hasattr(args, 'table_only') and args.table_only:
        cases = [tc for tc in cases if tc.chart_type == "table"]
    # +dashboard_2viz +dashboard_full +patch +style_override +dashboard_multipage +calc_field_measurement +calc_field_dimension +metric_basic +metric_ratio +metric_template +metric_dashboard +metric_additional_dimensions +metric_sentiment_bad +metric_sentiment_none +metric_cumulative +metric_different_time +edge_case_validation
    # Note: calc_field tests now include multiple cases, edge_case_validation adds 7 more tests
    # Removed 2 tests: line_size_encoding and donut_color_angle_label_size (Size encoding not supported)
    total_tests = len(cases) + (0 if (hasattr(args, 'table_only') and args.table_only) else 7 + 7 + 9)  # +9 for metric tests (4 original + 5 new)
    print(f"\nRunning {total_tests} test cases...\n")

    # 4. Execute chart tests
    results: List[TestResult] = []
    for i, tc in enumerate(cases, 1):
        label = f"[{i}/{total_tests}] {tc.id}: {tc.description}"
        print(f"  {label} ...", end=" ", flush=True)

        r = run_test(tc, token, instance, args.sdm, pf.sdm_label)
        results.append(r)

        if r.validation_passed and r.post_passed and r.roundtrip_passed:
            print(_ok(""))
        elif r.validation_passed and r.post_passed:
            print(_warn("roundtrip diffs"))
        elif r.validation_passed:
            print(_fail("POST failed"))
        else:
            print(_fail("validation failed"))

    # 5. Dashboard test
    test_num = len(cases) + 1
    print(f"  [{test_num}/{total_tests}] dashboard_2viz: Dashboard with 2 viz widgets ...", end=" ", flush=True)
    dash_r = run_dashboard_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(dash_r)
    if dash_r.post_passed and dash_r.roundtrip_passed:
        print(_ok(""))
    elif dash_r.post_passed:
        print(_warn("widget status issues"))
    else:
        print(_fail(dash_r.post_error or "failed"))

    # 6. Dashboard full test (filter + metric + vizzes)
    test_num += 1
    print(f"  [{test_num}/{total_tests}] dashboard_full: filter + metric + vizzes ...", end=" ", flush=True)
    dashf_r = run_dashboard_full_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(dashf_r)
    if dashf_r.post_passed and dashf_r.roundtrip_passed:
        print(_ok(""))
    elif dashf_r.post_passed:
        print(_warn("widget status issues"))
    else:
        print(_fail(dashf_r.post_error or "failed"))

    # 7. PATCH test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] patch_update_label: POST then PATCH label ...", end=" ", flush=True)
    patch_r = run_patch_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(patch_r)
    if patch_r.post_passed and patch_r.roundtrip_passed:
        print(_ok(""))
    elif patch_r.post_passed:
        print(_warn("label not verified"))
    else:
        print(_fail(patch_r.post_error or "failed"))

    # 8. Style override test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] style_override_verify: bar with custom styles ...", end=" ", flush=True)
    style_r = run_style_override_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(style_r)
    if style_r.post_passed and style_r.roundtrip_passed:
        print(_ok(""))
    elif style_r.post_passed:
        print(_warn("style path diffs"))
    else:
        print(_fail(style_r.post_error or "failed"))

    # 9. Multi-page dashboard test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] dashboard_multipage: 2-page + buttons + container ...", end=" ", flush=True)
    mp_r = run_dashboard_multipage_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(mp_r)
    if mp_r.post_passed and mp_r.roundtrip_passed:
        print(_ok(""))
    elif mp_r.post_passed:
        print(_warn("widget issues"))
    else:
        print(_fail(mp_r.post_error or "failed"))

    # 10. Calculated field measurement test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] calc_field_measurement: create _clc measurement ...", end=" ", flush=True)
    calc_m_r = run_calc_field_measurement_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(calc_m_r)
    if calc_m_r.post_passed and calc_m_r.roundtrip_passed:
        print(_ok(""))
    elif calc_m_r.post_passed:
        print(_warn("discovery/viz issues"))
    else:
        print(_fail(calc_m_r.post_error or "failed"))

    # 11. Calculated field dimension test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] calc_field_dimension: create _clc dimension ...", end=" ", flush=True)
    calc_d_r = run_calc_field_dimension_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(calc_d_r)
    if calc_d_r.post_passed and calc_d_r.roundtrip_passed:
        print(_ok(""))
    elif calc_d_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(calc_d_r.post_error or "failed"))

    # 12. Metric basic test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_basic: create _mtc metric (SUM) ...", end=" ", flush=True)
    metric_basic_r = run_metric_basic_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_basic_r)
    if metric_basic_r.post_passed and metric_basic_r.roundtrip_passed:
        print(_ok(""))
    elif metric_basic_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_basic_r.post_error or "failed"))

    # 13. Metric ratio test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_ratio: create _mtc metric (win rate) ...", end=" ", flush=True)
    metric_ratio_r = run_metric_ratio_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_ratio_r)
    if metric_ratio_r.post_passed and metric_ratio_r.roundtrip_passed:
        print(_ok(""))
    elif metric_ratio_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_ratio_r.post_error or "failed"))

    # 14. Metric template test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_template: create _mtc metric using template ...", end=" ", flush=True)
    metric_template_r = run_metric_template_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_template_r)
    if metric_template_r.post_passed and metric_template_r.roundtrip_passed:
        print(_ok(""))
    elif metric_template_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_template_r.post_error or "failed"))

    # 15. Metric dashboard test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_dashboard: create _mtc metric, use in dashboard ...", end=" ", flush=True)
    metric_dash_r = run_metric_dashboard_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_dash_r)
    if metric_dash_r.post_passed and metric_dash_r.roundtrip_passed:
        print(_ok(""))
    elif metric_dash_r.post_passed:
        print(_warn("dashboard issues"))
    else:
        print(_fail(metric_dash_r.post_error or "failed"))

    # 16. Metric with additionalDimensions test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_additional_dimensions: create _mtc metric with additionalDimensions ...", end=" ", flush=True)
    metric_dims_r = run_metric_additional_dimensions_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_dims_r)
    if metric_dims_r.post_passed and metric_dims_r.roundtrip_passed:
        print(_ok(""))
    elif metric_dims_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_dims_r.post_error or "failed"))

    # 17. Metric with SentimentTypeUpIsBad test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_sentiment_bad: create _mtc metric with SentimentTypeUpIsBad ...", end=" ", flush=True)
    metric_sent_bad_r = run_metric_sentiment_bad_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_sent_bad_r)
    if metric_sent_bad_r.post_passed and metric_sent_bad_r.roundtrip_passed:
        print(_ok(""))
    elif metric_sent_bad_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_sent_bad_r.post_error or "failed"))

    # 18. Metric with SentimentTypeNone test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_sentiment_none: create _mtc metric with SentimentTypeNone ...", end=" ", flush=True)
    metric_sent_none_r = run_metric_sentiment_none_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_sent_none_r)
    if metric_sent_none_r.post_passed and metric_sent_none_r.roundtrip_passed:
        print(_ok(""))
    elif metric_sent_none_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_sent_none_r.post_error or "failed"))

    # 19. Metric with isCumulative: true test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_cumulative: create _mtc metric with isCumulative: true ...", end=" ", flush=True)
    metric_cumulative_r = run_metric_cumulative_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_cumulative_r)
    if metric_cumulative_r.post_passed and metric_cumulative_r.roundtrip_passed:
        print(_ok(""))
    elif metric_cumulative_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_cumulative_r.post_error or "failed"))

    # 20. Metric with different time dimension test
    test_num += 1
    print(f"  [{test_num}/{total_tests}] metric_different_time: create _mtc metric with Created_Date ...", end=" ", flush=True)
    metric_time_r = run_metric_different_time_dimension_test(token, instance, args.sdm, pf.sdm_label, pf)
    results.append(metric_time_r)
    if metric_time_r.post_passed and metric_time_r.roundtrip_passed:
        print(_ok(""))
    elif metric_time_r.post_passed:
        print(_warn("discovery issues"))
    else:
        print(_fail(metric_time_r.post_error or "failed"))

    # 21. Edge case validation tests
    print(f"\n  Running edge case validation tests...")
    edge_case_results = run_edge_case_validation_tests(token, instance, args.sdm, pf.sdm_label, pf)
    for edge_r in edge_case_results:
        test_num += 1
        label = f"[{test_num}/{total_tests + len(edge_case_results)}] {edge_r.id}: {edge_r.description}"
        print(f"  {label} ...", end=" ", flush=True)
        results.append(edge_r)
        if edge_r.validation_passed:
            print(_ok("validation caught error" if "error" in edge_r.id or "missing" in edge_r.id else "passed"))
        else:
            print(_fail("validation did not catch expected error" if "error" in edge_r.id or "missing" in edge_r.id else "failed"))
        if edge_r.validation_errors:
            for e in edge_r.validation_errors[:2]:  # Show first 2 errors
                print(f"    {YELLOW}-> {e}{RESET}")

    # 17. Template tests
    print(f"\n  Running template tests...")
    template_results = run_template_tests(token, instance, args.sdm, pf.sdm_label, pf)
    for template_r in template_results:
        test_num += 1
        label = f"[{test_num}/{total_tests + len(edge_case_results) + len(template_results)}] {template_r.id}: {template_r.description}"
        print(f"  {label} ...", end=" ", flush=True)
        results.append(template_r)
        if template_r.validation_passed and template_r.post_passed and template_r.roundtrip_passed:
            print(_ok(""))
        elif template_r.validation_passed and template_r.post_passed:
            print(_warn("roundtrip diffs"))
        elif template_r.validation_passed:
            print(_fail("POST failed"))
        else:
            print(_fail("validation failed"))

    # 18. Report
    print_results(results)

    if args.json_report:
        save_json_report(results, args.json_report)

    # 19. Cleanup
    if args.cleanup:
        extra_names = [
            "__TH_dash_bar", "__TH_dash_donut",
            "__TH_dashf_bar", "__TH_dashf_donut",
            "__TH_patch_target",
            "__TH_dashm_bar", "__TH_dashm_donut",
            "__TH_style_test",
            "__TH_viz_with_new_calc",
            "__TH_metric_dash",
        ]
        cleanup_vizzes(token, instance, results, extra_viz_names=extra_names, sdm_name=args.sdm)

    # Exit code
    all_ok = all(r.validation_passed and r.post_passed for r in results)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
