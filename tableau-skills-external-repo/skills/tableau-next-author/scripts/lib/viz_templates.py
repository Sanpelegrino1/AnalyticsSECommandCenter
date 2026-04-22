"""Visualization templates for common chart patterns.

Each template defines:
- Chart type (bar, line, donut, etc.)
- Required fields (category, amount, date, etc.)
- Field matching logic (how to find fields in SDM)
- Encoding defaults (Label, Color, etc.)
- Style overrides (colors, formats)
"""

import difflib
import re
from typing import Any, Dict, List, Optional, Tuple

# Aliases: AI often generates x_dimension/y_dimension; heatmap_grid expects col_dim/row_dim
TEMPLATE_FIELD_ALIASES: Dict[str, Dict[str, str]] = {
    "heatmap_grid": {"x_dimension": "col_dim", "y_dimension": "row_dim"},
}

# Template definitions
VIZ_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "revenue_by_category": {
        "description": "Bar chart showing revenue/amount by a categorical dimension with automatic sorting (descending by measure) and optional color encoding",
        "chart_type": "bar",
        "required_fields": {
            "category": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "amount": {"role": "Measure", "aggregationType": "Sum"}
        },
        "optional_fields": {
            "color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]}
        },
        "field_mapping": {
            "columns": ["category"],
            "rows": ["amount"]
        },
        "encodings": [
            {"field": "amount", "type": "Label"}
        ],
        "sort_orders": {
            "fields": {"category": {"byField": "amount", "order": "Descending", "type": "Nested"}}
        },
        "legends": {},  # Will be populated if color_dim is provided
        "style": {
            "fit": "Entire"
        }
    },
    
    "stacked_bar_by_dimension": {
        "description": "Stacked bar chart showing part-to-whole with breakdown by second dimension",
        "chart_type": "bar",
        "required_fields": {
            "category": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "stack_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "amount": {"role": "Measure", "aggregationType": "Sum"}
        },
        "field_mapping": {
            "columns": ["category"],
            "rows": ["amount"]
        },
        "encodings": [
            {"field": "amount", "type": "Label"},
            {"field": "stack_dim", "type": "Color"}  # Color encoding creates stacked bars
        ],
        "legends": {"stack_dim": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        "style": {
            "fit": "Entire"
        }
    },
    
    "multi_series_line": {
        "description": "Multi-series line chart comparing trends across categories",
        "chart_type": "line",
        "required_fields": {
            "date": {"role": "Dimension", "dataType": ["DateTime", "Date"]},
            "measure": {"role": "Measure"},
            "color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]}
        },
        "field_mapping": {
            "columns": ["date_year", "date_month"],  # Year + Month hierarchy
            "rows": ["measure"]
        },
        "date_functions": {
            "date_year": "DatePartYear",
            "date_month": "DatePartMonth"
        },
        "encodings": [
            {"field": "measure", "type": "Label"},
            {"field": "color_dim", "type": "Color"}  # Color by category creates multiple series
        ],
        "legends": {"color_dim": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },
    
    "trend_over_time": {
        "description": "Line chart showing measure trend over time with Year+Month hierarchy (automatic). Uses DatePartYear for multi-year datasets. Optional color_dim converts to multi-series line chart.",
        "chart_type": "line",
        "required_fields": {
            "date": {"role": "Dimension", "dataType": ["DateTime", "Date"]},
            "measure": {"role": "Measure"}
        },
        "optional_fields": {
            "color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]}
        },
        "field_mapping": {
            "columns": ["date_year", "date_month"],  # Year + Month hierarchy (automatic)
            "rows": ["measure"]
        },
        "date_functions": {
            "date_year": "DatePartYear",   # Year field (for multi-year datasets)
            "date_month": "DatePartMonth"  # Month field (creates hierarchy with year)
        },
        "encodings": [
            {"field": "measure", "type": "Label"}
        ],
        "legends": {}  # Will be populated if color_dim is provided
    },
    
    "market_share_donut": {
        "description": "Donut chart showing distribution/share by category with Color + Angle + Label encodings (test harness pattern)",
        "chart_type": "donut",
        "required_fields": {
            "category": {"role": "Dimension"},
            "amount": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": ["category"],
            "rows": []
        },
        "encodings": [
            {"field": "category", "type": "Color"},
            {"field": "amount", "type": "Angle"},
            {"field": "amount", "type": "Label"}
        ],
        "legends": {"category": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },
    
    "top_n_leaderboard": {
        "description": "Top-N ranking as a horizontal Vizql bar (measure on columns, dimension on rows, sorted by measure). Table layout rejects viewSpecification.sortOrders.byField on the API.",
        "chart_type": "bar",
        "required_fields": {
            "id_field": {"role": "Dimension"},
            "label_field": {"role": "Dimension"},
            "amount": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": ["amount"],
            "rows": ["label_field"]
        },
        "encodings": [
            {"field": "amount", "type": "Label"}
        ],
        "sort_orders": {
            "fields": {
                "label_field": {
                    "byField": "amount",
                    "order": "Descending",
                    "type": "Field",
                }
            }
        },
        "top_n": {
            "limit": 5,
            "rank_dimension": "label_field",
            "rank_by": "amount",
            "rank_aggregation": "SUM",
            "is_top": True,
        },
        "legends": {},
    },
    
    "conversion_funnel": {
        "description": "Funnel chart showing stages with decreasing values. Includes automatic sorting (descending by measure) and optional color encoding.",
        "chart_type": "funnel",
        "required_fields": {
            "stage": {"role": "Dimension"},
            "count": {"role": "Measure"}
        },
        "optional_fields": {
            "color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]}
        },
        "field_mapping": {
            "columns": ["stage"],
            "rows": ["count"]
        },
        "encodings": [
            {"field": "count", "type": "Label"}
        ],
        "sort_orders": {
            "fields": {"stage": {"byField": "count", "order": "Descending", "type": "Nested"}}
        },
        "legends": {}  # Will be populated if color_dim is provided
    },
    
    "funnel_color_dim": {
        "description": "Funnel chart with Color encoding by dimension",
        "chart_type": "funnel",
        "required_fields": {
            "stage": {"role": "Dimension"},
            "count": {"role": "Measure"},
            "color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]}
        },
        "field_mapping": {
            "columns": ["stage"],
            "rows": ["count"]
        },
        "encodings": [
            {"field": "count", "type": "Label"},
            {"field": "color_dim", "type": "Color"}
        ],
        "legends": {"color_dim": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },
    
    "scatter_correlation": {
        "description": "Scatter plot showing relationship between two measures with Detail + Color encodings (test harness pattern). Detail encoding MUST come first, followed by Color encoding. Optional size_measure and label_measure for Size and Label encodings.",
        "chart_type": "scatter",
        "required_fields": {
            "x_measure": {"role": "Measure"},
            "y_measure": {"role": "Measure"}
        },
        "optional_fields": {
            "category": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "size_measure": {"role": "Measure"},
            "label_measure": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": ["x_measure"],
            "rows": ["y_measure"]
        },
        "encodings": [
            {"field": "category", "type": "Detail", "optional": True},  # Detail encoding MUST come first for scatter plots
            {"field": "category", "type": "Color", "optional": True},
            {"field": "size_measure", "type": "Size", "optional": True},
            {"field": "label_measure", "type": "Label", "optional": True}
        ],
        "legends": {"category": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },
    
    "heatmap_grid": {
        "description": "Heatmap showing two dimensions with Color(measure) + Label(measure) + Size(measure) encodings (test harness pattern)",
        "chart_type": "heatmap",
        "required_fields": {
            "row_dim": {"role": "Dimension"},
            "col_dim": {"role": "Dimension"},
            "measure": {"role": "Measure"}
        },
        "optional_fields": {
            "size_measure": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": ["col_dim"],
            "rows": ["row_dim"]
        },
        "encodings": [
            {"field": "measure", "type": "Color"},
            {"field": "measure", "type": "Label"},
            {"field": "size_measure", "type": "Size", "optional": True}  # Size encoding (test harness pattern)
        ],
        "legends": {"measure": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },
    
    "kpi_single_value": {
        "description": "Text mark showing a single metric value",
        "chart_type": "table",
        "required_fields": {
            "measure": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": [],
            "rows": ["measure"]
        },
        "encodings": []
    },
    
    "bar_multi_measure": {
        "description": "Side-by-side bar chart comparing multiple measures using MeasureValues pattern",
        "chart_type": "bar",
        "required_fields": {
            "category": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "measure_1": {"role": "Measure"},
            "measure_2": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": ["category"],
            "rows": []
        },
        "encodings": [
            {"field": "category", "type": "Color"},
            {"field": "measure_1", "type": "Label"}
        ],
        "legends": {"category": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}},
        "measure_values": ["measure_1", "measure_2"],  # Special: requires MeasureValues/MeasureNames fields
        "style": {
            "fit": "Entire"
        }
    },
    
    "line_detail_encoding": {
        "description": "Line chart with Detail encoding for breaking down by dimension (Year+Month hierarchy)",
        "chart_type": "line",
        "required_fields": {
            "date": {"role": "Dimension", "dataType": ["DateTime", "Date"]},
            "measure": {"role": "Measure"},
            "detail_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]}
        },
        "field_mapping": {
            "columns": ["date_year", "date_month"],  # Year + Month hierarchy
            "rows": ["measure"]
        },
        "date_functions": {
            "date_year": "DatePartYear",
            "date_month": "DatePartMonth"
        },
        "encodings": [
            {"field": "detail_dim", "type": "Detail"},
            {"field": "color_dim", "type": "Color"}
        ],
        "legends": {"color_dim": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },
    
    "scatter_color_meas": {
        "description": "Scatter plot with Color encoding by measure (instead of dimension)",
        "chart_type": "scatter",
        "required_fields": {
            "x_measure": {"role": "Measure"},
            "y_measure": {"role": "Measure"},
            "detail_dim": {"role": "Dimension", "optional": True},
            "color_measure": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": ["x_measure"],
            "rows": ["y_measure"]
        },
        "encodings": [
            {"field": "detail_dim", "type": "Detail", "optional": True},
            {"field": "color_measure", "type": "Color"}
        ],
        "legends": {"color_measure": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },
    
    "heatmap_label_size": {
        "description": "Heatmap with Label and Size encodings in addition to Color",
        "chart_type": "heatmap",
        "required_fields": {
            "row_dim": {"role": "Dimension"},
            "col_dim": {"role": "Dimension"},
            "color_measure": {"role": "Measure"},
            "label_measure": {"role": "Measure"},
            "size_measure": {"role": "Measure"}
        },
        "field_mapping": {
            "columns": ["col_dim"],
            "rows": ["row_dim"]
        },
        "encodings": [
            {"field": "color_measure", "type": "Color"},
            {"field": "label_measure", "type": "Label"},
            {"field": "size_measure", "type": "Size"}
        ],
        "legends": {"color_measure": {"isVisible": True, "position": "Right", "title": {"isVisible": True}}}
    },

    "geomap_location_only": {
        "description": "Map with MapPosition only: lat/lon, no measure encodings (default Circle marks)",
        "chart_type": "map",
        "map_build_mode": "location_only",
        "required_fields": {
            "latitude": {"role": "Dimension"},
            "longitude": {"role": "Dimension"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "geomap_points": {
        "description": "Map with points: MapPosition (lat/lon), measure on Color, dimension on Label",
        "chart_type": "map",
        "required_fields": {
            "latitude": {"role": "Dimension"},
            "longitude": {"role": "Dimension"},
            "measure": {"role": "Measure"},
            "label_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "geomap_advanced": {
        "description": "Map: MapPosition + label dim + same measure triplicated for Color, Label, and Size encodings",
        "chart_type": "map",
        "map_build_mode": "advanced",
        "required_fields": {
            "latitude": {"role": "Dimension"},
            "longitude": {"role": "Dimension"},
            "measure": {"role": "Measure"},
            "label_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_sankey": {
        "description": "Sankey / Flow: link Color (duplicate measure) + level-2 bar Color (duplicate dim); optional link/level2 field overrides",
        "chart_type": "flow",
        "flow_build_mode": "colors",
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "optional_fields": {
            "link_color_measure": {"role": "Measure"},
            "level2_color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_simple": {
        "description": "Flow / Sankey minimal: two levels + link measure only; fixed bar/link colors, no Color encodings",
        "chart_type": "flow",
        "flow_build_mode": "simple",
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_simple_measure_on_marks": {
        "description": "Flow minimal + duplicate link measure as Size on nodes (single-color flow with measure-driven node size)",
        "chart_type": "flow",
        "flow_build_mode": "simple_measure_on_marks",
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_sankey_measure_on_marks": {
        "description": "Full color Sankey plus a third copy of the link measure for Size on nodes (colors + measure on marks)",
        "chart_type": "flow",
        "flow_build_mode": "colors_measure_on_marks",
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "optional_fields": {
            "link_color_measure": {"role": "Measure"},
            "level2_color_dim": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_package_base": {
        "description": "Package parity: measure-first F1=link, F2/F3=levels, empty encodings (New_Dashboard1_package Base_Flow)",
        "chart_type": "flow",
        "flow_build_mode": "package_minimal",
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_package_single_color": {
        "description": "Package parity: same as flow_package_base with uniform #F9E3B6 on bars/nodes (Base_Flow_single_color_all_nodes)",
        "chart_type": "flow",
        "flow_build_mode": "package_minimal",
        "style": {"flow_uniform_fill": "#F9E3B6"},
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_package_link_color_nodes_color": {
        "description": "Package parity: link Color(dup measure) + nodes Color(dup level2); F4 defined (Copy_of_Base_Flow_*_measure_on_marks)",
        "chart_type": "flow",
        "flow_build_mode": "package_link_nodes_color",
        "style": {"flow_uniform_fill": "#F9E3B6"},
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_package_colors_variations": {
        "description": "Package parity: first-level bar Color(dup L1), link Color(dup measure), nodes Color(dup L2) (Base_Flow_colors_variations_measure_on_marks)",
        "chart_type": "flow",
        "flow_build_mode": "package_colors_variations",
        "style": {"flow_uniform_fill": "#F9E3B6", "flow_package_hide_color_legends": True},
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },

    "flow_package_three_level": {
        "description": "Package parity: three level dimensions + link; link Color on duplicate measure; hidden legend optional (Base_Flow_colors_variations_measure_on_marks1)",
        "chart_type": "flow",
        "flow_build_mode": "package_three_level",
        "required_fields": {
            "level1": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level2": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "level3": {"role": "Dimension", "dataType": ["Text", "Picklist"]},
            "link_measure": {"role": "Measure"},
        },
        "field_mapping": {"columns": [], "rows": []},
        "encodings": [],
    },
}


# Keyword lists for auto-matching
AMOUNT_KEYWORDS = ["amount", "revenue", "total", "sales", "value", "sum", "revenue", "income"]
DATE_KEYWORDS = ["date", "time", "month", "quarter", "year", "close", "created", "modified"]
CATEGORY_KEYWORDS = ["category", "type", "region", "stage", "status", "industry", "segment", "group"]
STAGE_KEYWORDS = ["stage", "status", "phase", "step", "level"]
COUNT_KEYWORDS = ["count", "number", "quantity", "qty", "total", "opportunities", "records", "items", "units", "clc"]
LATITUDE_KEYWORDS = ["lat", "latitude"]
LONGITUDE_KEYWORDS = ["lon", "longitude", "lng"]

_GEO_NUMERIC_DATATYPES = frozenset(
    {
        "Number",
        "Double",
        "Decimal",
        "Currency",
        "Integer",
        "Percent",
        "Float",
        "Geo",
        "Geolocation",
        "Location",
    }
)


def _sdm_field_datatype(field: Dict[str, Any]) -> Optional[str]:
    """Prefer dataType; fall back to type (some SDM payloads use type for primitives)."""
    return field.get("dataType") or field.get("type")


def score_field(field_name: str, keywords: List[str]) -> int:
    """Score a field name by keyword presence.
    
    Args:
        field_name: Field name to score
        keywords: List of keywords to match
        
    Returns:
        Score (number of matching keywords)
    """
    field_lower = field_name.lower()
    return sum(1 for kw in keywords if kw.lower() in field_lower)


def _latitude_longitude_score(api_name: str, field: Dict[str, Any], slot: str) -> int:
    """Score SDM fields for geomap latitude/longitude slots.

    SSOT often uses opaque apiNames with human-readable labels (e.g. label \"Latitude\");
    scoring apiName only misses those and falls back to the first dimension.
    """
    keywords = LATITUDE_KEYWORDS if slot == "latitude" else LONGITUDE_KEYWORDS
    label = str(field.get("label") or "")
    base = max(score_field(api_name, keywords), score_field(label, keywords))
    api_l = api_name.lower()
    label_l = label.strip().lower()
    want = slot
    if api_l == want or label_l == want:
        base += 40
    if slot == "latitude" and (label_l in ("lat", "y") or api_l in ("lat", "y")):
        base += 15
    if slot == "longitude" and (label_l in ("lon", "lng", "long", "x") or api_l in ("lon", "lng", "x")):
        base += 15
    return base


def _geo_field_identity(field: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    return field.get("fieldName"), field.get("objectName")


def find_matching_fields(
    sdm_fields: Dict[str, Dict[str, Any]],
    template_requirements: Dict[str, Dict[str, Any]],
    user_overrides: Optional[Dict[str, str]] = None
) -> Dict[str, Dict[str, Any]]:
    """Auto-match SDM fields to template requirements.
    
    Uses field name similarity, data types, and role matching.
    
    Args:
        sdm_fields: Dict mapping field names to SDM field definitions
        template_requirements: Template's required_fields dict
        user_overrides: Optional dict mapping template field names to user-specified field names
        
    Returns:
        Dict mapping template field names to matched SDM field definitions
    """
    user_overrides = user_overrides or {}
    matches: Dict[str, Dict[str, Any]] = {}
    
    # Flatten all SDM fields into a single list with metadata
    all_fields: List[Tuple[str, Dict[str, Any]]] = []
    for field_name, field_def in sdm_fields.items():
        all_fields.append((field_name, field_def))
    
    for template_field_name, requirements in template_requirements.items():
        # Check if user provided explicit override
        if template_field_name in user_overrides:
            user_field_name = user_overrides[template_field_name]
            if user_field_name in sdm_fields:
                matches[template_field_name] = sdm_fields[user_field_name]
                continue
            # Try fuzzy match on user-provided name
            fuzzy_matches = difflib.get_close_matches(
                user_field_name, 
                [f[0] for f in all_fields], 
                n=3, 
                cutoff=0.6
            )
            if fuzzy_matches:
                # Check role matches
                for match_name in fuzzy_matches:
                    if match_name in sdm_fields:
                        match_field = sdm_fields[match_name]
                        if match_field.get("role") == requirements.get("role"):
                            matches[template_field_name] = match_field
                            break
                if template_field_name in matches:
                    continue
            # If no match found, provide helpful error
            required_role = requirements.get("role")
            allowed_types = requirements.get("dataType", [])
            similar_fields = difflib.get_close_matches(
                user_field_name,
                [f[0] for f in all_fields],
                n=5,
                cutoff=0.4
            )
            error_msg = (
                f"Field '{user_field_name}' not found in SDM. "
                f"Required: {required_role}"
            )
            if allowed_types:
                error_msg += f" with dataType {allowed_types}"
            if similar_fields:
                error_msg += f". Similar fields: {', '.join(similar_fields[:3])}"
            raise ValueError(error_msg)
        
        # Filter by role
        required_role = requirements.get("role")
        candidates = [
            (name, field) for name, field in all_fields
            if field.get("role") == required_role
        ]

        # Geomap templates require "Dimension" in the schema, but SSOT often exposes
        # coordinates as semanticMeasurements on Store (or similar) — role Measure.
        if template_field_name in ("latitude", "longitude"):
            candidates = [
                (name, field)
                for name, field in all_fields
                if field.get("role") in ("Dimension", "Measure")
            ]

        if not candidates:
            # Special case: if looking for "count" measure and none found, try any measure
            if template_field_name == "count" and required_role == "Measure":
                # Look for ANY measure as fallback
                any_measures = [(name, field) for name, field in all_fields if field.get("role") == "Measure"]
                if any_measures:
                    matches[template_field_name] = any_measures[0][1]
                    continue
            
            # Provide helpful error message
            allowed_types = requirements.get("dataType", [])
            all_field_names = [f[0] for f in all_fields]
            similar_fields = difflib.get_close_matches(
                template_field_name,
                all_field_names,
                n=5,
                cutoff=0.4
            )
            error_msg = (
                f"No {required_role} fields found matching '{template_field_name}'"
            )
            if allowed_types:
                error_msg += f" with dataType {allowed_types}"
            if similar_fields:
                error_msg += f". Similar fields: {', '.join(similar_fields[:3])}"
            raise ValueError(error_msg)
        
        # Filter by dataType if specified
        allowed_types = requirements.get("dataType")
        if allowed_types:
            original_candidates = candidates
            candidates = [
                (name, field) for name, field in candidates
                if field.get("dataType") in allowed_types
            ]
            if not candidates:
                # Provide helpful error about data type mismatch
                found_types = {f[1].get("dataType") for f in original_candidates}
                # Filter out None values
                found_types_str = [str(t) for t in found_types if t is not None]
                error_msg = (
                    f"No {required_role} fields with dataType {allowed_types} found."
                )
                if found_types_str:
                    error_msg += f" Found types: {', '.join(sorted(found_types_str))}"
                raise ValueError(error_msg)

        if template_field_name == "longitude" and "latitude" in matches:
            lat_fn, lat_ob = _geo_field_identity(matches["latitude"])
            if lat_fn is not None:
                candidates = [
                    (n, f)
                    for n, f in candidates
                    if f.get("fieldName") != lat_fn or f.get("objectName") != lat_ob
                ]

        if template_field_name == "label_dim":
            geo_used: List[Tuple[Optional[str], Optional[str]]] = []
            if "latitude" in matches:
                lat_id = _geo_field_identity(matches["latitude"])
                if lat_id[0] is not None:
                    geo_used.append(lat_id)
            if "longitude" in matches:
                lon_id = _geo_field_identity(matches["longitude"])
                if lon_id[0] is not None:
                    geo_used.append(lon_id)
            if geo_used:
                candidates = [
                    (n, f)
                    for n, f in candidates
                    if _geo_field_identity(f) not in geo_used
                ]

        if template_field_name in ("latitude", "longitude"):
            slot = template_field_name
            scored_candidates = [
                (_latitude_longitude_score(n, f, slot), n, f) for n, f in candidates
            ]
            scored_candidates.sort(key=lambda x: x[0], reverse=True)

            if scored_candidates:
                best_score = scored_candidates[0][0]
                tied = [x for x in scored_candidates if x[0] == best_score]
                if len(tied) > 1:
                    numeric_only = [
                        t
                        for t in tied
                        if _sdm_field_datatype(t[2]) in _GEO_NUMERIC_DATATYPES
                    ]
                    if numeric_only:
                        tied = numeric_only
                tie_score, _tie_name, best_field = tied[0]
                if tie_score == 0:
                    exact_match = next(
                        (
                            name
                            for name, field in candidates
                            if name.lower() == slot
                            or str(field.get("label") or "").strip().lower() == slot
                        ),
                        None,
                    )
                    if exact_match:
                        matches[slot] = sdm_fields[exact_match]
                    else:
                        matches[slot] = best_field
                else:
                    matches[slot] = best_field
            continue

        # Score candidates by keyword matching
        scored_candidates: List[Tuple[int, str, Dict[str, Any]]] = []

        # Choose keyword list based on template field name
        keywords: List[str] = []
        if "amount" in template_field_name or "measure" in template_field_name:
            keywords = AMOUNT_KEYWORDS
        elif "date" in template_field_name or "time" in template_field_name:
            keywords = DATE_KEYWORDS
        elif "category" in template_field_name:
            keywords = CATEGORY_KEYWORDS
        elif "stage" in template_field_name:
            keywords = STAGE_KEYWORDS
        elif "count" in template_field_name:
            keywords = COUNT_KEYWORDS

        for name, field in candidates:
            score = score_field(name, keywords)
            scored_candidates.append((score, name, field))

        # Sort by score (descending) and pick best match
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        if scored_candidates:
            best_score = scored_candidates[0][0]
            tied = [x for x in scored_candidates if x[0] == best_score]

            best_score, best_name, best_field = tied[0]
            # If score is 0, try exact name match as fallback
            if best_score == 0:
                # Try exact match with template field name
                exact_match = next(
                    (name for name, field in candidates if name.lower() == template_field_name.lower()),
                    None
                )
                if exact_match:
                    matches[template_field_name] = sdm_fields[exact_match]
                else:
                    # Special handling for "count" field: use first measure as fallback
                    # (count can be derived from any measure - we'll use it as a proxy)
                    if template_field_name == "count" and required_role == "Measure":
                        matches[template_field_name] = best_field
                    else:
                        # Just use first candidate
                        matches[template_field_name] = best_field
            else:
                matches[template_field_name] = best_field

    return matches


def get_template(template_name: str) -> Optional[Dict[str, Any]]:
    """Get a template definition by name.
    
    Args:
        template_name: Name of the template
        
    Returns:
        Template definition dict or None if not found
    """
    return VIZ_TEMPLATES.get(template_name)


def list_templates() -> List[str]:
    """List all available template names.
    
    Returns:
        List of template names
    """
    return list(VIZ_TEMPLATES.keys())


def get_template_info(template_name: str) -> Optional[Dict[str, Any]]:
    """Get template info including description and required fields.
    
    Args:
        template_name: Name of the template
        
    Returns:
        Dict with description and required_fields, or None if not found
    """
    template = get_template(template_name)
    if not template:
        return None
    
    info: Dict[str, Any] = {
        "name": template_name,
        "description": template.get("description", ""),
        "chart_type": template.get("chart_type", ""),
        "required_fields": template.get("required_fields", {}),
        "field_mapping": template.get("field_mapping", {}),
        "encodings": template.get("encodings", []),
    }
    if template.get("optional_fields"):
        info["optional_fields"] = template["optional_fields"]
    return info


def _normalize_fields_for_template(viz_spec: Dict[str, Any]) -> None:
    """Rewrite fields keys using aliases when the template has aliases.
    
    Mutates viz_spec["fields"] in-place. E.g. heatmap_grid: x_dimension -> col_dim,
    y_dimension -> row_dim.
    """
    template_name = viz_spec.get("template")
    if not template_name:
        return
    aliases = TEMPLATE_FIELD_ALIASES.get(template_name)
    if not aliases:
        return
    fields = viz_spec.get("fields", {})
    if not fields:
        return
    for alias_key, canonical_key in aliases.items():
        if alias_key in fields:
            fields[canonical_key] = fields.pop(alias_key)


def validate_viz_spec_fields(viz_spec: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate that visualization spec uses correct field names for the template.
    
    Args:
        viz_spec: Visualization specification dict with:
            - template: Template name
            - name: Visualization name (for error messages)
            - fields: Dict mapping template field names to SDM field names
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if field names are valid, False otherwise
        - error_message: Error message with valid field names if invalid, None if valid
    """
    _normalize_fields_for_template(viz_spec)
    template_name = viz_spec.get("template")
    if not template_name:
        return False, "Missing 'template' field in visualization spec"
    
    template = get_template(template_name)
    if not template:
        return False, f"Unknown template: '{template_name}'"
    
    fields = viz_spec.get("fields", {})
    required_fields = template.get("required_fields", {})
    optional_fields = template.get("optional_fields", {})
    
    # Get all valid field names
    valid_field_names = set(required_fields.keys()) | set(optional_fields.keys())
    
    # Check for invalid field names
    invalid_fields = []
    for field_name in fields.keys():
        if field_name not in valid_field_names:
            invalid_fields.append(field_name)
    
    if invalid_fields:
        viz_name = viz_spec.get("name", "unknown")
        required_list = ", ".join(sorted(required_fields.keys()))
        optional_list = ", ".join(sorted(optional_fields.keys())) if optional_fields else "(none)"
        
        error_msg = (
            f"✗ Error: Invalid field names in visualization '{viz_name}':\n"
            f"  Template: {template_name}\n"
            f"  Invalid fields: {', '.join(invalid_fields)}\n"
            f"  Valid required fields: {required_list}\n"
            f"  Valid optional fields: {optional_list}"
        )
        return False, error_msg
    
    return True, None


def recommend_chart_type(
    dimensions: List[Dict[str, Any]],
    measures: List[Dict[str, Any]],
    unique_value_counts: Optional[Dict[str, int]] = None
) -> Optional[str]:
    """Recommend chart type based on data characteristics (Tableau "Show Me" logic).
    
    Decision Matrix:
    - Trend over time (1 Date Dimension + 1 Measure) → Line Chart
    - Comparison/Ranking (1 String Dimension + 1 Measure) → Bar Chart (sorted descending)
    - Part-to-Whole (1 Dimension with < 5 unique values + 1 Measure) → Donut Chart
    - Part-to-Whole (1 Dimension with >= 5 unique values + 1 Measure) → Bar Chart (stacked)
    - Correlation (2 Continuous Measures) → Scatter Plot
    - Distribution (1 Measure only) → Bar Chart (histogram-like)
    - Multiple Measures (2+ Measures) → Bar Chart (side-by-side)
    - Detailed Table (Multiple Dimensions + Measures) → Table
    
    Args:
        dimensions: List of dimension field definitions
        measures: List of measure field definitions
        unique_value_counts: Optional dict mapping dimension field names to unique value counts
        
    Returns:
        Recommended template name or None if no match
    """
    unique_value_counts = unique_value_counts or {}
    
    # Count dimensions by type
    date_dims = [d for d in dimensions if d.get("dataType") in ["DateTime", "Date"]]
    text_dims = [d for d in dimensions if d.get("dataType") in ["Text", "Picklist"]]
    # Filter out ID fields - they have too many unique values and make visualizations unreadable
    text_dims = [d for d in text_dims if not _is_id_field(d.get("fieldName", ""))]
    all_dims = date_dims + text_dims
    
    num_dimensions = len(all_dims)
    num_measures = len(measures)
    
    # Rule 1: Multi-series trend (1 Date + 1 Measure + 1 Dimension) → Multi-Series Line Chart
    # Prefer multi-series line when we have date + measure + category dimension
    if len(date_dims) == 1 and num_measures == 1 and len(text_dims) >= 1:
        return "multi_series_line"  # Multi-series line with color encoding by category
    
    # Rule 2: Trend over time (1 Date Dimension + 1 Measure) → Line Chart
    if num_dimensions == 1 and num_measures == 1 and len(date_dims) == 1:
        return "trend_over_time"
    
    # Rule 3: Stacked Bar (2 Dimensions + 1 Measure) → Stacked Bar Chart
    # Prefer stacked bar for part-to-whole with breakdown
    if num_dimensions == 2 and num_measures == 1 and len(text_dims) == 2:
        return "stacked_bar_by_dimension"  # Stacked bar with color encoding
    
    # Rule 4: Comparison/Ranking (1 String Dimension + 1 Measure) → Bar Chart
    if num_dimensions == 1 and num_measures == 1 and len(text_dims) == 1:
        return "revenue_by_category"  # Bar chart template
    
    # Rule 5: Heatmap (2 Dimensions + 1 Measure) → Heatmap
    # Prioritize heatmaps - great for two-dimensional analysis
    if num_dimensions == 2 and num_measures == 1:
        return "heatmap_grid"
    
    # Rule 6: Correlation (2 Continuous Measures) → Scatter Plot
    # Prioritize scatter plots for measure correlation
    if num_dimensions == 0 and num_measures == 2:
        return "scatter_correlation"
    
    # Rule 7: Dot Matrix (2 Dimensions + 2 Measures) → Dot Matrix
    # Great for two-dimensional analysis with size encoding
    if num_dimensions == 2 and num_measures >= 2:
        return "dot_matrix"
    
    # Rule 8: Multiple Measures with Category (1 Dimension + 2+ Measures) → Multi-Measure Bar Chart
    if num_dimensions == 1 and num_measures >= 2 and len(text_dims) == 1:
        return "bar_multi_measure"  # Side-by-side bars comparing multiple measures
    
    # Rule 9: Part-to-Whole (1 Dimension + 1 Measure)
    if num_dimensions == 1 and num_measures == 1:
        dim_name = all_dims[0].get("fieldName", "")
        unique_count = unique_value_counts.get(dim_name, 999)
        
        # < 5 unique values → Donut Chart
        if unique_count < 5:
            return "market_share_donut"
        
        # >= 5 unique values → Bar Chart (preferred over funnel)
        # Bar charts are versatile and work well for most comparisons
        return "revenue_by_category"
    
    # Rule 10: Distribution (1 Measure only) → Bar Chart
    if num_dimensions == 0 and num_measures == 1:
        return "revenue_by_category"  # Bar chart as histogram alternative
    
    # Rule 11: Multiple Measures (2+ Measures, no dimensions) → Scatter or Bar Chart
    if num_dimensions == 0 and num_measures >= 2:
        # If exactly 2 measures, prefer scatter plot for correlation
        if num_measures == 2:
            return "scatter_correlation"
        # 3+ measures → Bar chart (side-by-side) - but this case is rare without dimensions
        return "revenue_by_category"
    
    # Rule 12: Detailed Table (Multiple Dimensions + Measures) → Table
    if num_dimensions >= 2 and num_measures >= 1:
        return "top_n_leaderboard"
    
    # Default: Bar chart (most versatile) - LAST RESORT
    if num_dimensions >= 1 and num_measures >= 1:
        return "revenue_by_category"
    
    return None



def _is_id_field(field_name: str) -> bool:
    """Check if a field is an ID field (should be excluded from visualizations).
    
    ID fields like Account_Id, Contact_Id, etc. have thousands of unique values
    and make visualizations unreadable. Only use them as a last resort.
    
    Args:
        field_name: Field name to check
        
    Returns:
        True if field is an ID field, False otherwise
    """
    name_lower = field_name.lower()
    # Check for common ID patterns
    id_patterns = [
        r'_id$',           # Ends with _id
        r'_ids$',          # Ends with _ids
        r'^id$',           # Just "id"
        r'^ids$',          # Just "ids"
        r'_id_',           # Contains _id_
        r'\.id$',          # Ends with .id
    ]
    return any(re.search(pattern, name_lower) for pattern in id_patterns)


def _score_dimension_relevance(field_def: Dict[str, Any]) -> int:
    """Score dimension field by relevance for visualizations.
    
    Higher scores indicate more meaningful dimensions for business insights.
    ID fields should be filtered out before calling this function.
    
    Args:
        field_def: Field definition dict with fieldName, description, label, etc.
        
    Returns:
        Relevance score (higher is better)
    """
    field_name = field_def.get("fieldName", "")
    name_lower = field_name.lower()
    score = 0
    
    # Highest priority: CLC fields (+15)
    if name_lower.endswith("_clc"):
        score += 15
    
    # Helper function to score text with keywords
    def score_text(text: str, keywords: List[str], points: int) -> int:
        if not text:
            return 0
        text_lower = text.lower()
        return points if any(kw in text_lower for kw in keywords) else 0
    
    # High priority keywords (+10)
    high_priority = ["industry", "type", "stage", "status", "region", "segment", 
                     "category", "group", "class", "tier", "level", "phase"]
    score += score_text(field_name, high_priority, 10)
    
    # Score description if available
    description = field_def.get("description", "")
    if description:
        score += score_text(description, high_priority, 10)
    
    # Score label if available
    label = field_def.get("label", "")
    if label:
        score += score_text(label, high_priority, 10)
    
    # Medium priority keywords (+5)
    medium_priority = ["country", "state", "territory", "department", "division",
                      "account", "opportunity", "product", "service"]
    score += score_text(field_name, medium_priority, 5)
    if description:
        score += score_text(description, medium_priority, 5)
    if label:
        score += score_text(label, medium_priority, 5)
    
    # Lower priority keywords (+2)
    lower_priority = ["name"]
    score += score_text(field_name, lower_priority, 2)
    if description:
        score += score_text(description, lower_priority, 2)
    if label:
        score += score_text(label, lower_priority, 2)
    
    # Penalize generic fields (-5)
    generic_keywords = ["description", "comment", "note", "detail", "text"]
    if any(kw in name_lower for kw in generic_keywords):
        score -= 5
    
    return score


def _score_measure_relevance(field_def: Dict[str, Any]) -> int:
    """Score measure field by relevance for visualizations.
    
    Higher scores indicate more meaningful measures for business insights.
    Prioritizes CLC (calculated) fields and common business metrics.
    
    Args:
        field_def: Field definition dict with fieldName, description, label, etc.
        
    Returns:
        Relevance score (higher is better)
    """
    field_name = field_def.get("fieldName", "")
    name_lower = field_name.lower()
    score = 0
    
    # Highest priority: CLC fields (+15)
    if name_lower.endswith("_clc"):
        score += 15
    
    # Helper function to score text with keywords
    def score_text(text: str, keywords: List[str], points: int) -> int:
        if not text:
            return 0
        text_lower = text.lower()
        return points if any(kw in text_lower for kw in keywords) else 0
    
    # High priority keywords for measures (+10)
    high_priority = ["amount", "revenue", "total", "sales", "value", "sum", "income", 
                     "profit", "margin", "rate", "ratio", "percentage", "percent"]
    score += score_text(field_name, high_priority, 10)
    
    # Score description if available
    description = field_def.get("description", "")
    if description:
        score += score_text(description, high_priority, 10)
    
    # Score label if available
    label = field_def.get("label", "")
    if label:
        score += score_text(label, high_priority, 10)
    
    # Medium priority keywords (+5)
    medium_priority = ["count", "quantity", "qty", "number", "average", "avg", 
                       "mean", "minimum", "min", "maximum", "max"]
    score += score_text(field_name, medium_priority, 5)
    if description:
        score += score_text(description, medium_priority, 5)
    if label:
        score += score_text(label, medium_priority, 5)
    
    # Lower priority keywords (+2)
    lower_priority = ["price", "cost", "fee", "charge"]
    score += score_text(field_name, lower_priority, 2)
    if description:
        score += score_text(description, lower_priority, 2)
    if label:
        score += score_text(label, lower_priority, 2)
    
    return score


def _select_best_dimensions(dimensions: List[Dict[str, Any]], num: int) -> List[Dict[str, Any]]:
    """Select the best N dimensions based on relevance scoring.
    
    Args:
        dimensions: List of dimension field definitions
        num: Number of dimensions to select
        
    Returns:
        List of best dimension field definitions, sorted by relevance
    """
    if not dimensions:
        return []
    
    # Score each dimension using full field definition
    scored = [(dim, _score_dimension_relevance(dim)) for dim in dimensions]
    
    # Sort by score (descending), then by field name for consistency
    scored.sort(key=lambda x: (-x[1], x[0].get("fieldName", "")))
    
    # Return top N
    return [dim for dim, score in scored[:num]]


def _select_best_measures(measures: List[Dict[str, Any]], num: int) -> List[Dict[str, Any]]:
    """Select the best N measures based on relevance scoring.
    
    Args:
        measures: List of measure field definitions
        num: Number of measures to select
        
    Returns:
        List of best measure field definitions, sorted by relevance
    """
    if not measures:
        return []
    
    # Score each measure using full field definition
    scored = [(m, _score_measure_relevance(m)) for m in measures]
    
    # Sort by score (descending), then by field name for consistency
    scored.sort(key=lambda x: (-x[1], x[0].get("fieldName", "")))
    
    # Return top N
    return [m for m, score in scored[:num]]


def recommend_diverse_chart_types(
    sdm_fields: Dict[str, Dict[str, Any]],
    num_charts: int = 5,
    unique_value_counts: Optional[Dict[str, int]] = None
) -> List[Dict[str, Any]]:
    """Recommend diverse chart types for a dashboard to avoid repetition.
    
    Intelligently selects different chart types based on available SDM fields
    to create a varied, informative dashboard. Prioritizes diversity over repetition.
    
    Args:
        sdm_fields: Dict mapping field names to SDM field definitions
        num_charts: Number of charts to recommend (default 5)
        unique_value_counts: Optional dict mapping dimension field names to unique value counts
    
    Returns:
        List of chart recommendations with template, fields, and reasoning
    """
    dimensions = [f for f in sdm_fields.values() if f.get("role") == "Dimension"]
    measures = [f for f in sdm_fields.values() if f.get("role") == "Measure"]
    
    date_dims = [d for d in dimensions if d.get("dataType") in ["DateTime", "Date"]]
    text_dims = [d for d in dimensions if d.get("dataType") in ["Text", "Picklist"]]
    # Filter out ID fields - they have too many unique values and make visualizations unreadable
    text_dims = [d for d in text_dims if not _is_id_field(d.get("fieldName", ""))]
    
    unique_value_counts = unique_value_counts or {}
    recommendations = []
    used_field_combinations = set()
    used_templates = set()
    used_measure_names = set()
    used_dim_names = set()
    
    # Priority 1: Multi-series line chart (date + measure + dimension) - GREAT for comparing trends
    if date_dims and measures and len(text_dims) >= 1 and len(recommendations) < num_charts:
        date_field = date_dims[0]
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 1) if available_measures else []
        measure_field = best_measures[0] if best_measures else measures[0]
        color_dim = _select_best_dimensions(text_dims, 1)[0] if text_dims else None
        combo = ("multi_series_line", date_field.get("fieldName"), measure_field.get("fieldName"), color_dim.get("fieldName"))
        if combo not in used_field_combinations and "multi_series_line" not in used_templates:
            recommendations.append({
                "template": "multi_series_line",
                "fields": {"date": date_field.get("fieldName"), "measure": measure_field.get("fieldName"), "color_dim": color_dim.get("fieldName")},
                "reasoning": "Multi-series trend comparison"
            })
            used_field_combinations.add(combo)
            used_templates.add("multi_series_line")
            used_measure_names.add(measure_field.get("fieldName"))
    
    # Priority 1b: Simple trend chart (if no dimension available for multi-series)
    # Prefer multi_series_line if text dimension available, otherwise use trend_over_time
    if date_dims and measures and len(recommendations) < num_charts and "multi_series_line" not in used_templates:
        date_field = date_dims[0]
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 1) if available_measures else []
        measure_field = best_measures[0] if best_measures else measures[0]
        # Check if we can use multi_series_line instead (better with color)
        if len(text_dims) >= 1:
            color_dim = _select_best_dimensions(text_dims, 1)[0] if text_dims else None
            combo = ("multi_series_line", date_field.get("fieldName"), measure_field.get("fieldName"), color_dim.get("fieldName"))
            if combo not in used_field_combinations:
                recommendations.append({
                    "template": "multi_series_line",
                    "fields": {"date": date_field.get("fieldName"), "measure": measure_field.get("fieldName"), "color_dim": color_dim.get("fieldName")},
                    "reasoning": "Multi-series trend comparison"
                })
                used_field_combinations.add(combo)
                used_templates.add("multi_series_line")
                used_measure_names.add(measure_field.get("fieldName"))
        else:
            combo = ("trend", date_field.get("fieldName"), measure_field.get("fieldName"))
            if combo not in used_field_combinations and "trend_over_time" not in used_templates:
                recommendations.append({
                    "template": "trend_over_time",
                    "fields": {"date": date_field.get("fieldName"), "measure": measure_field.get("fieldName")},
                    "reasoning": "Trend analysis over time (Year+Month hierarchy automatic)"
                })
                used_field_combinations.add(combo)
                used_templates.add("trend_over_time")
                used_measure_names.add(measure_field.get("fieldName"))
    
    # Priority 2: Stacked Bar (2 dimensions + 1 measure) - Great for part-to-whole with breakdown
    if len(text_dims) >= 2 and measures and len(recommendations) < num_charts:
        best_dims = _select_best_dimensions(text_dims, 2)
        dim1 = best_dims[0] if len(best_dims) > 0 else text_dims[0]
        dim2 = best_dims[1] if len(best_dims) > 1 else (best_dims[0] if len(best_dims) > 0 else text_dims[1] if len(text_dims) > 1 else text_dims[0])
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 1) if available_measures else []
        measure_field = best_measures[0] if best_measures else measures[0]
        combo = ("stacked_bar", dim1.get("fieldName"), dim2.get("fieldName"), measure_field.get("fieldName"))
        if combo not in used_field_combinations and "stacked_bar_by_dimension" not in used_templates:
            recommendations.append({
                "template": "stacked_bar_by_dimension",
                "fields": {"category": dim1.get("fieldName"), "stack_dim": dim2.get("fieldName"), "amount": measure_field.get("fieldName")},
                "reasoning": "Part-to-whole with breakdown"
            })
            used_field_combinations.add(combo)
            used_templates.add("stacked_bar_by_dimension")
            used_measure_names.add(measure_field.get("fieldName"))
    
    # Priority 3: Heatmap (2 dimensions + 1 measure) - Great for two-dimensional analysis
    # Use heatmap if we have more dimensions available (after stacked bar)
    # Update used field tracking from existing recommendations
    for r in recommendations:
        for field_name in r.get("fields", {}).values():
            if isinstance(field_name, str):
                # Track dimensions that have been used
                if field_name in sdm_fields:
                    field_def = sdm_fields[field_name]
                    if field_def.get("role") == "Dimension":
                        used_dim_names.add(field_name)
                    elif field_def.get("role") == "Measure":
                        used_measure_names.add(field_name)
    
    remaining_text_dims = [d for d in text_dims if d.get("fieldName") not in used_dim_names]
    if len(remaining_text_dims) >= 2 and measures and len(recommendations) < num_charts:
        best_dims = _select_best_dimensions(remaining_text_dims, 2)
        dim1 = best_dims[0] if len(best_dims) > 0 else remaining_text_dims[0]
        dim2 = best_dims[1] if len(best_dims) > 1 else (best_dims[0] if len(best_dims) > 0 else remaining_text_dims[1] if len(remaining_text_dims) > 1 else remaining_text_dims[0])
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 1) if available_measures else []
        measure_field = best_measures[0] if best_measures else measures[0]
        combo = ("heatmap", dim1.get("fieldName"), dim2.get("fieldName"), measure_field.get("fieldName"))
        if combo not in used_field_combinations and "heatmap_grid" not in used_templates:
            recommendations.append({
                "template": "heatmap_grid",
                "fields": {"row_dim": dim1.get("fieldName"), "col_dim": dim2.get("fieldName"), "measure": measure_field.get("fieldName")},
                "reasoning": "Two-dimensional analysis"
            })
            used_field_combinations.add(combo)
            used_templates.add("heatmap_grid")
            used_measure_names.add(measure_field.get("fieldName"))
    
    # Priority 4: Multi-measure bar chart (1 dimension + 2+ measures) - Side-by-side comparison
    if text_dims and len(measures) >= 2 and len(recommendations) < num_charts:
        # Find a dimension not already used
        available_dims_filtered = [d for d in text_dims if d.get("fieldName") not in used_dim_names]
        best_available = _select_best_dimensions(available_dims_filtered, 1)
        available_dim = best_available[0] if best_available else (text_dims[0] if text_dims else None)
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 2) if len(available_measures) >= 2 else []
        if len(best_measures) >= 2:
            measure1 = best_measures[0]
            measure2 = best_measures[1]
        else:
            measure1 = measures[0]
            measure2 = measures[1] if len(measures) > 1 else measures[0]
        combo = ("bar_multi", available_dim.get("fieldName"), measure1.get("fieldName"), measure2.get("fieldName"))
        if combo not in used_field_combinations and "bar_multi_measure" not in used_templates:
            recommendations.append({
                "template": "bar_multi_measure",
                "fields": {"category": available_dim.get("fieldName"), "measure_1": measure1.get("fieldName"), "measure_2": measure2.get("fieldName")},
                "reasoning": "Multi-measure comparison"
            })
            used_field_combinations.add(combo)
            used_templates.add("bar_multi_measure")
            used_dim_names.add(available_dim.get("fieldName"))
            used_measure_names.add(measure1.get("fieldName"))
            used_measure_names.add(measure2.get("fieldName"))
    
    # Priority 5: Scatter plot (2 measures) - Great for correlation
    # CRITICAL: Always include Detail encoding (category field) for scatter plots
    if len(measures) >= 2 and len(recommendations) < num_charts:
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 2) if len(available_measures) >= 2 else []
        if len(best_measures) >= 2:
            measure1 = best_measures[0]
            measure2 = best_measures[1]
        else:
            measure1 = measures[0]
            measure2 = measures[1] if len(measures) > 1 else measures[0]
        # Find a dimension field for Detail encoding (required for useful scatter plots)
        detail_dim = None
        available_dims = [d for d in text_dims if d.get("fieldName") not in used_dim_names]
        if available_dims:
            best_detail_dims = _select_best_dimensions(available_dims, 1)
            detail_dim = best_detail_dims[0] if best_detail_dims else available_dims[0]
        # Prefer stage/status fields for Detail encoding (but NOT ID fields - they're too granular)
        for dim in available_dims:
            dim_name = dim.get("fieldName", "").lower()
            # Prefer stage/status fields, but skip ID fields
            if ("stage" in dim_name or "status" in dim_name) and not _is_id_field(dim.get("fieldName", "")):
                detail_dim = dim
                break
        
        combo = ("scatter", measure1.get("fieldName"), measure2.get("fieldName"), detail_dim.get("fieldName") if detail_dim else None)
        if combo not in used_field_combinations and "scatter_correlation" not in used_templates:
            scatter_fields = {"x_measure": measure1.get("fieldName"), "y_measure": measure2.get("fieldName")}
            if detail_dim:
                scatter_fields["category"] = detail_dim.get("fieldName")
            recommendations.append({
                "template": "scatter_correlation",
                "fields": scatter_fields,
                "reasoning": "Correlation analysis" + (" (with Detail encoding)" if detail_dim else " (WARNING: missing Detail encoding)")
            })
            used_field_combinations.add(combo)
            used_templates.add("scatter_correlation")
            used_measure_names.add(measure1.get("fieldName"))
            used_measure_names.add(measure2.get("fieldName"))
            if detail_dim:
                used_dim_names.add(detail_dim.get("fieldName"))
    
    # Priority 6: Donut chart (category with < 5 values) - Prefer over funnel
    if text_dims and measures and len(recommendations) < num_charts:
        for dim in text_dims:
            dim_name = dim.get("fieldName", "")
            unique_count = unique_value_counts.get(dim_name, 999)
            # Prefer donut for small categories (< 5 values)
            if unique_count < 5:
                available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
                best_measures = _select_best_measures(available_measures, 1) if available_measures else []
                measure_field = best_measures[0] if best_measures else measures[0]
                combo = ("donut", dim_name, measure_field.get("fieldName"))
                if combo not in used_field_combinations and "market_share_donut" not in used_templates:
                    recommendations.append({
                        "template": "market_share_donut",
                        "fields": {"category": dim_name, "amount": measure_field.get("fieldName")},
                        "reasoning": "Distribution analysis"
                    })
                    used_field_combinations.add(combo)
                    used_templates.add("market_share_donut")
                    used_measure_names.add(measure_field.get("fieldName"))
                    break
    
    # Priority 5: Dot Matrix (2 dimensions + 2 measures) - Great for multi-dimensional analysis
    if len(text_dims) >= 2 and len(measures) >= 2 and len(recommendations) < num_charts:
        best_dims = _select_best_dimensions(text_dims, 2)
        dim1 = best_dims[0] if len(best_dims) > 0 else text_dims[0]
        dim2 = best_dims[1] if len(best_dims) > 1 else (best_dims[0] if len(best_dims) > 0 else text_dims[1] if len(text_dims) > 1 else text_dims[0]) if len(text_dims) > 1 else text_dims[0]
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 2) if len(available_measures) >= 2 else []
        if len(best_measures) >= 2:
            measure1 = best_measures[0]
            measure2 = best_measures[1]
        else:
            measure1 = measures[0]
            measure2 = measures[1] if len(measures) > 1 else measures[0]
        combo = ("dot_matrix", dim1.get("fieldName"), dim2.get("fieldName"), measure1.get("fieldName"), measure2.get("fieldName"))
        if combo not in used_field_combinations and "dot_matrix" not in used_templates:
            recommendations.append({
                "template": "dot_matrix",
                "fields": {"row_dim": dim1.get("fieldName"), "col_dim": dim2.get("fieldName"), 
                          "size_measure": measure1.get("fieldName"), "color_measure": measure2.get("fieldName")},
                "reasoning": "Multi-dimensional analysis"
            })
            used_field_combinations.add(combo)
            used_templates.add("dot_matrix")
            used_measure_names.add(measure1.get("fieldName"))
            used_measure_names.add(measure2.get("fieldName"))
    
    # Priority 6: Bar charts for remaining categories (diverse fields) - Preferred over funnels
    # Add color_dim automatically when second dimension available (test harness pattern)
    remaining_dims = [d for d in text_dims if d.get("fieldName") not in 
                      [r["fields"].get("category") or r["fields"].get("row_dim") or r["fields"].get("col_dim") 
                       for r in recommendations for k in r["fields"].keys()]]
    bar_count = sum(1 for r in recommendations if r["template"] == "revenue_by_category")
    
    for dim in remaining_dims[:num_charts - len(recommendations)]:
        if len(recommendations) >= num_charts:
            break
        available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
        best_measures = _select_best_measures(available_measures, 1) if available_measures else []
        measure_field = best_measures[0] if best_measures else measures[0]
        
        # Add color_dim if another dimension is available (test harness pattern: Bar + Color + Sort)
        color_dim_field = None
        available_for_color = [d for d in remaining_dims if d.get("fieldName") != dim.get("fieldName")]
        if available_for_color:
            color_dim_field = available_for_color[0].get("fieldName")
        
        combo = ("bar", dim.get("fieldName"), measure_field.get("fieldName"), color_dim_field)
        if combo not in used_field_combinations:
            # Business logic: If showing revenue by stage, warn about filtering to Closed Won
            reasoning = "Comparison analysis"
            dim_name = dim.get("fieldName", "").lower()
            measure_name = measure_field.get("fieldName", "").lower()
            if ("stage" in dim_name or "status" in dim_name) and ("revenue" in measure_name or "amount" in measure_name):
                reasoning += " (NOTE: Consider filtering to Closed Won for meaningful revenue analysis)"
            
            bar_fields = {"category": dim.get("fieldName"), "amount": measure_field.get("fieldName")}
            if color_dim_field:
                bar_fields["color_dim"] = color_dim_field
                reasoning += " (with color encoding)"
            
            recommendations.append({
                "template": "revenue_by_category",
                "fields": bar_fields,
                "reasoning": reasoning
            })
            used_field_combinations.add(combo)
            bar_count += 1
            used_measure_names.add(measure_field.get("fieldName"))
            if color_dim_field:
                used_dim_names.add(color_dim_field)
    
    # Priority 7: Funnel chart (ONLY if stage field with 5-15 values) - Last resort, rarely used
    stage_dims = [d for d in text_dims if any(kw in d.get("fieldName", "").lower() for kw in ["stage", "status", "phase"])]
    if stage_dims and measures and len(recommendations) < num_charts:
        stage_field = stage_dims[0]
        stage_name = stage_field.get("fieldName", "")
        unique_count = unique_value_counts.get(stage_name, 999)
        # Only use funnel if it's clearly a stage field AND has reasonable count (5-15 values)
        # AND we haven't already filled the dashboard with better chart types
        if 5 <= unique_count <= 15:
            available_measures = [m for m in measures if m.get("fieldName") not in used_measure_names]
            best_measures = _select_best_measures(available_measures, 1) if available_measures else []
            measure_field = best_measures[0] if best_measures else measures[0]
            combo = ("funnel", stage_name, measure_field.get("fieldName"))
            if combo not in used_field_combinations and "conversion_funnel" not in used_templates:
                recommendations.append({
                    "template": "conversion_funnel",
                    "fields": {"stage": stage_name, "count": measure_field.get("fieldName")},
                    "reasoning": "Pipeline/stage analysis"
                })
                used_field_combinations.add(combo)
                used_templates.add("conversion_funnel")
                used_measure_names.add(measure_field.get("fieldName"))
    
    return recommendations


def analyze_fields_for_chart_selection(
    sdm_fields: Dict[str, Dict[str, Any]],
    selected_field_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Analyze SDM fields and recommend chart type + field mappings.
    
    Args:
        sdm_fields: Dict mapping field names to field definitions
        selected_field_names: Optional list of field names user wants to use
        
    Returns:
        Dict with:
            - recommended_template: Template name
            - field_mappings: Dict mapping template field names to SDM field names
            - reasoning: Explanation of why this chart type was chosen
    """
    # Filter to selected fields if provided
    if selected_field_names:
        fields = {name: sdm_fields[name] for name in selected_field_names if name in sdm_fields}
    else:
        fields = sdm_fields
    
    # Separate dimensions and measures
    dimensions = [f for f in fields.values() if f.get("role") == "Dimension"]
    measures = [f for f in fields.values() if f.get("role") == "Measure"]
    
    # Recommend chart type
    recommended_template = recommend_chart_type(dimensions, measures)
    
    if not recommended_template:
        return {
            "recommended_template": None,
            "field_mappings": {},
            "reasoning": "No suitable chart type found for provided fields"
        }
    
    # Get template to understand required fields
    template = get_template(recommended_template)
    if not template:
        return {
            "recommended_template": None,
            "field_mappings": {},
            "reasoning": f"Template '{recommended_template}' not found"
        }
    
    # Map fields to template requirements
    field_mappings = find_matching_fields(fields, template["required_fields"])
    
    # Build reasoning
    reasoning_parts = []
    if len([d for d in dimensions if d.get("dataType") in ["DateTime", "Date"]]) == 1:
        reasoning_parts.append("1 Date Dimension detected")
    if len([d for d in dimensions if d.get("dataType") in ["Text", "Picklist"]]) == 1:
        reasoning_parts.append("1 Text Dimension detected")
    reasoning_parts.append(f"{len(measures)} Measure(s) detected")
    
    reasoning = f"Chart Type: {recommended_template}. " + ", ".join(reasoning_parts)
    
    return {
        "recommended_template": recommended_template,
        "field_mappings": {k: v.get("fieldName") for k, v in field_mappings.items()},
        "reasoning": reasoning
    }
