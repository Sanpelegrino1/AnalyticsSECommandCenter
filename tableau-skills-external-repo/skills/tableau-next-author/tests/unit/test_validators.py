"""Unit tests for validators.py - all 17 validation rules."""

import pytest
from scripts.lib.validators import (
    ValidationResult,
    validate,
    is_valid,
    _check_encoding_field_refs,
    _check_root_fields,
    _check_view,
    _check_visual_spec_fields,
    _check_marks_structure,
    _check_style,
    _check_encoding_fields,
    _check_palette_schema,
    _check_size_encoding_support,
)


class TestCheckRootFields:
    """Test Rule 1: Required root fields."""

    def test_valid_payload(self, sample_viz_payload):
        """Valid payload has all required root fields."""
        results = _check_root_fields(sample_viz_payload)
        assert len(results) == 1
        assert results[0].ok is True
        assert "root_fields" in results[0].rule

    def test_missing_single_field(self):
        """Missing a single required field fails."""
        payload = {
            "name": "Test",
            "label": "Test",
            "dataSource": {},
            "workspace": {},
            "fields": {},
            "visualSpecification": {},
            "interactions": []
            # Missing "view"
        }
        results = _check_root_fields(payload)
        assert len(results) == 1
        assert results[0].ok is False
        assert "view" in results[0].message

    def test_missing_multiple_fields(self):
        """Missing multiple required fields fails."""
        payload = {
            "name": "Test"
            # Missing all other required fields
        }
        results = _check_root_fields(payload)
        assert len(results) == 1
        assert results[0].ok is False
        assert "Missing required root field" in results[0].message


class TestCheckView:
    """Test Rule 2: View structure."""

    def test_valid_view(self, sample_viz_payload):
        """Valid view structure passes."""
        results = _check_view(sample_viz_payload)
        assert len(results) == 1
        assert results[0].ok is True

    def test_missing_view(self):
        """Missing view fails."""
        payload = {"name": "Test"}
        results = _check_view(payload)
        assert len(results) == 1
        assert results[0].ok is False
        assert "view" in results[0].message.lower()

    def test_invalid_view_type(self):
        """View must be a dict."""
        payload = {"view": "not a dict"}
        results = _check_view(payload)
        assert len(results) == 1
        assert results[0].ok is False

    def test_missing_view_fields(self):
        """View must have label, name, viewSpecification."""
        payload = {
            "view": {
                "label": "default"
                # Missing name and viewSpecification
            }
        }
        results = _check_view(payload)
        assert len(results) == 1
        assert results[0].ok is False
        assert "name" in results[0].message or "viewSpecification" in results[0].message

    def test_flow_rejects_top_level_view_specification_filters(self):
        """Flow must omit legacy viewSpecification.filters (v66.12)."""
        payload = {
            "visualSpecification": {"layout": "Flow"},
            "view": {
                "label": "d",
                "name": "d",
                "viewSpecification": {
                    "filters": [],
                    "sortOrders": {"columns": [], "fields": {}, "rows": []},
                },
            },
        }
        results = _check_view(payload)
        assert len(results) == 1
        assert results[0].ok is False
        assert "filters" in results[0].message.lower()


class TestCheckVisualSpecFields:
    """Test Rule 3: Visual specification required keys."""

    def test_valid_vizql_layout(self, sample_viz_payload):
        """Valid Vizql layout passes."""
        results = _check_visual_spec_fields(sample_viz_payload)
        assert len(results) == 1
        # Check that layout is present (defaults to Vizql if not specified)
        vs = sample_viz_payload.get("visualSpecification", {})
        assert "layout" in vs or vs.get("layout", "Vizql") == "Vizql"
        assert results[0].ok is True

    def test_valid_table_layout(self):
        """Valid Table layout passes."""
        payload = {
            "visualSpecification": {
                "layout": "Table",
                "marks": {},
                "style": {},
                "rows": []
            }
        }
        results = _check_visual_spec_fields(payload)
        assert len(results) == 1
        assert results[0].ok is True

    def test_missing_required_fields(self):
        """Missing required fields fails."""
        payload = {
            "visualSpecification": {
                "marks": {}
                # Missing style, measureValues, etc.
            }
        }
        results = _check_visual_spec_fields(payload)
        assert len(results) == 1
        assert results[0].ok is False


class TestCheckMarksStructure:
    """Test Rules 4-7: Marks structure checks."""

    def test_valid_marks(self, sample_viz_payload):
        """Valid marks structure passes all checks."""
        results = _check_marks_structure(sample_viz_payload)
        assert all(r.ok for r in results)
        assert len(results) == 5  # ALL, panes+headers, mark type, panes.stack, headers.stack

    def test_no_legacy_all_key(self):
        """Rule 4: marks.ALL is not allowed (v65.11 format)."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "ALL": {}  # Old format
                }
            }
        }
        results = _check_marks_structure(payload)
        all_check = [r for r in results if r.rule == "marks_no_ALL"][0]
        assert all_check.ok is False
        assert "ALL" in all_check.message

    def test_marks_panes_and_headers_required(self):
        """Rule 5: panes and headers must be present."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "panes": {}
                    # Missing headers
                }
            }
        }
        results = _check_marks_structure(payload)
        panes_headers_check = [r for r in results if r.rule == "marks_panes_headers"][0]
        assert panes_headers_check.ok is False

    def test_valid_mark_type(self):
        """Rule 6: Valid mark type passes."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "panes": {
                        "type": "Bar",
                        "stack": {"isAutomatic": True, "isStacked": True},
                    },
                    "headers": {
                        "encodings": [],
                        "isAutomatic": True,
                        "stack": {"isAutomatic": True, "isStacked": False},
                        "type": "Text",
                    },
                }
            }
        }
        results = _check_marks_structure(payload)
        mark_type_check = [r for r in results if r.rule == "mark_type"][0]
        assert mark_type_check.ok is True

    def test_invalid_mark_type(self):
        """Rule 6: Invalid mark type fails."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "panes": {
                        "type": "InvalidType",
                        "stack": {"isAutomatic": True, "isStacked": True},
                    },
                    "headers": {
                        "encodings": [],
                        "isAutomatic": True,
                        "stack": {"isAutomatic": True, "isStacked": False},
                        "type": "Text",
                    },
                }
            }
        }
        results = _check_marks_structure(payload)
        mark_type_check = [r for r in results if r.rule == "mark_type"][0]
        assert mark_type_check.ok is False

    def test_stack_required(self):
        """Rule 7: stack must be present in panes."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "panes": {
                        "type": "Bar",
                    },
                    "headers": {
                        "encodings": [],
                        "isAutomatic": True,
                        "stack": {"isAutomatic": True, "isStacked": False},
                        "type": "Text",
                    },
                }
            }
        }
        results = _check_marks_structure(payload)
        stack_check = [r for r in results if r.rule == "marks_stack"][0]
        assert stack_check.ok is False


class TestCheckStyle:
    """Test Rules 8-11: Style checks."""

    def test_valid_style(self, sample_viz_payload):
        """Valid style passes all checks."""
        results = _check_style(sample_viz_payload)
        assert all(r.ok for r in results)
        assert len(results) == 6  # panes.range, headers.range, headers.size, axis, fonts, lines

    def test_range_required(self):
        """Rule 8: style.marks.panes.range is required."""
        payload = {
            "visualSpecification": {
                "layout": "Vizql",
                "style": {
                    "marks": {
                        "panes": {}
                        # Missing range
                    }
                }
            }
        }
        results = _check_style(payload)
        range_check = [r for r in results if r.rule == "style_range"][0]
        assert range_check.ok is False

    def test_axis_required_for_vizql(self):
        """Rule 9: axis required for Vizql layout."""
        payload = {
            "visualSpecification": {
                "layout": "Vizql",
                "style": {
                    "marks": {
                        "headers": {
                            "range": {"reverse": True},
                            "size": {"isAutomatic": True, "type": "Pixel", "value": 13},
                        },
                        "panes": {
                            "range": {}
                        },
                    }
                    # Missing axis
                }
            }
        }
        results = _check_style(payload)
        axis_check = [r for r in results if r.rule == "style_axis"][0]
        assert axis_check.ok is False

    def test_table_forbidden_keys(self):
        """Rule 9: Table layout cannot have axis, referenceLines, showDataPlaceholder."""
        payload = {
            "visualSpecification": {
                "layout": "Table",
                "style": {
                    "axis": {},  # Forbidden for Table
                    "marks": {
                        "headers": {
                            "range": {"reverse": True},
                            "size": {"isAutomatic": True, "type": "Pixel", "value": 13},
                        },
                        "panes": {
                            "range": {}
                        },
                    }
                }
            }
        }
        results = _check_style(payload)
        table_check = [r for r in results if r.rule == "style_table_forbidden"][0]
        assert table_check.ok is False

    def test_fonts_required(self):
        """Rule 10: All 7 font keys required."""
        payload = {
            "visualSpecification": {
                "style": {
                    "fonts": {
                        "actionableHeaders": {},
                        "axisTickLabels": {}
                        # Missing 5 other font keys
                    },
                    "marks": {
                        "headers": {
                            "range": {"reverse": True},
                            "size": {"isAutomatic": True, "type": "Pixel", "value": 13},
                        },
                        "panes": {
                            "range": {}
                        },
                    }
                }
            }
        }
        results = _check_style(payload)
        fonts_check = [r for r in results if r.rule == "style_fonts"][0]
        assert fonts_check.ok is False

    def test_lines_required(self):
        """Rule 11: All 4 line keys required."""
        payload = {
            "visualSpecification": {
                "style": {
                    "lines": {
                        "axisLine": {}
                        # Missing 3 other line keys
                    },
                    "marks": {
                        "headers": {
                            "range": {"reverse": True},
                            "size": {"isAutomatic": True, "type": "Pixel", "value": 13},
                        },
                        "panes": {
                            "range": {}
                        },
                    }
                }
            }
        }
        results = _check_style(payload)
        lines_check = [r for r in results if r.rule == "style_lines"][0]
        assert lines_check.ok is False


class TestCheckEncodingFields:
    """Test Rules 12-16: Encoding/header field checks."""

    def test_valid_encoding_fields(self, sample_viz_payload):
        """Valid encoding fields pass all checks."""
        results = _check_encoding_fields(sample_viz_payload)
        assert all(r.ok for r in results)

    def test_measure_in_encoding_needs_style(self):
        """Rule 12: Measure in encodings must have style.encodings.fields entry."""
        payload = {
            "fields": {
                "F2": {
                    "role": "Measure"
                }
            },
            "visualSpecification": {
                "marks": {
                    "panes": {
                        "encodings": [
                            {
                                "type": "Label",
                                "fieldKey": "F2"
                            }
                        ]
                    }
                },
                "style": {
                    "encodings": {
                        "fields": {}
                        # Missing F2 entry
                    }
                }
            }
        }
        results = _check_encoding_fields(payload)
        enc_measure_check = [r for r in results if r.rule == "enc_measure_style"][0]
        assert enc_measure_check.ok is False

    def test_dimension_in_encodings_fields_invalid(self):
        """Rule 13: Dimension in style.encodings.fields is invalid (unless has color config)."""
        payload = {
            "fields": {
                "F1": {
                    "role": "Dimension",
                    "type": "Field"
                }
            },
            "visualSpecification": {
                "style": {
                    "encodings": {
                        "fields": {
                            "F1": {
                                "defaults": {}
                                # No color configuration
                            }
                        }
                    }
                }
            }
        }
        results = _check_encoding_fields(payload)
        enc_dims_check = [r for r in results if r.rule == "enc_no_dims"][0]
        assert enc_dims_check.ok is False

    def test_dimension_with_color_allowed(self):
        """Rule 13: Dimension with color configuration is allowed."""
        payload = {
            "fields": {
                "F1": {
                    "role": "Dimension",
                    "type": "Field"
                }
            },
            "visualSpecification": {
                "style": {
                    "encodings": {
                        "fields": {
                            "F1": {
                                "colors": {
                                    "palette": {}
                                }
                            }
                        }
                    }
                }
            }
        }
        results = _check_encoding_fields(payload)
        enc_dims_check = [r for r in results if r.rule == "enc_no_dims"][0]
        assert enc_dims_check.ok is True

    def test_headers_fields_only_shelf_dims(self):
        """Rule 14: style.headers.fields only for dims on rows/columns."""
        payload = {
            "visualSpecification": {
                "columns": ["F1"],
                "style": {
                    "headers": {
                        "fields": {
                            "F1": {},
                            "F2": {}  # F2 not on columns/rows
                        }
                    }
                }
            }
        }
        results = _check_encoding_fields(payload)
        hdr_check = [r for r in results if r.rule == "hdr_only_shelf_dims"][0]
        assert hdr_check.ok is False

    def test_shelf_and_encoding_conflict(self):
        """Rule 15: Fields cannot be both on shelves AND in encodings."""
        payload = {
            "fields": {
                "F1": {}
            },
            "visualSpecification": {
                "columns": ["F1"],  # On shelf
                "marks": {
                    "panes": {
                        "encodings": [
                            {
                                "type": "Label",
                                "fieldKey": "F1"  # Also in encoding
                            }
                        ]
                    }
                }
            }
        }
        results = _check_encoding_fields(payload)
        conflict_check = [r for r in results if r.rule == "shelf_and_encoding"][0]
        assert conflict_check.ok is False

    def test_donut_requires_color_dimension(self, sample_donut_payload):
        """Rule 16: Donut charts require Color(dimension) encoding."""
        # Remove Color encoding
        payload = sample_donut_payload.copy()
        payload["visualSpecification"]["marks"]["panes"]["encodings"] = [
            {
                "type": "Angle",
                "fieldKey": "F2"
            }
            # Missing Color encoding with dimension
        ]
        results = _check_encoding_fields(payload)
        donut_color_check = [r for r in results if r.rule == "donut_color_required"][0]
        assert donut_color_check.ok is False

    def test_donut_requires_angle_measure(self, sample_donut_payload):
        """Rule 16: Donut charts require Angle(measure) encoding."""
        # Remove Angle encoding
        payload = sample_donut_payload.copy()
        payload["visualSpecification"]["marks"]["panes"]["encodings"] = [
            {
                "type": "Color",
                "fieldKey": "F1"
            }
            # Missing Angle encoding with measure
        ]
        results = _check_encoding_fields(payload)
        donut_angle_check = [r for r in results if r.rule == "donut_angle_required"][0]
        assert donut_angle_check.ok is False


class TestCheckSizeEncodingSupport:
    """Test Rule 17: Size encoding support."""

    def test_size_encoding_not_supported_line(self):
        """Size encoding not supported for Line charts."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "panes": {
                        "type": "Line",
                        "encodings": [
                            {
                                "type": "Size",
                                "fieldKey": "F2"
                            }
                        ]
                    }
                }
            }
        }
        results = _check_size_encoding_support(payload)
        assert len(results) == 1
        assert results[0].ok is False
        assert "Line" in results[0].message

    def test_size_encoding_not_supported_donut(self):
        """Size encoding not supported for Donut charts."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "panes": {
                        "type": "Donut",
                        "encodings": [
                            {
                                "type": "Size",
                                "fieldKey": "F2"
                            }
                        ]
                    }
                }
            }
        }
        results = _check_size_encoding_support(payload)
        assert len(results) == 1
        assert results[0].ok is False
        assert "Donut" in results[0].message

    def test_size_encoding_supported_bar(self):
        """Size encoding supported for Bar charts."""
        payload = {
            "visualSpecification": {
                "marks": {
                    "panes": {
                        "type": "Bar",
                        "encodings": [
                            {
                                "type": "Size",
                                "fieldKey": "F2"
                            }
                        ]
                    }
                }
            }
        }
        results = _check_size_encoding_support(payload)
        assert len(results) == 1
        assert results[0].ok is True


class TestCheckPaletteSchema:
    """Test Rules 15-16: Palette schema validation."""

    def test_sequential_palette_valid(self):
        """Sequential palette (2-color) uses startToEndSteps."""
        payload = {
            "visualSpecification": {
                "style": {
                    "encodings": {
                        "fields": {
                            "F1": {
                                "colors": {
                                    "palette": {
                                        "startToEndSteps": 5
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        results = _check_palette_schema(payload)
        assert all(r.ok for r in results)

    def test_sequential_palette_invalid(self):
        """Sequential palette cannot have middle-related keys."""
        payload = {
            "visualSpecification": {
                "style": {
                    "encodings": {
                        "fields": {
                            "F1": {
                                "colors": {
                                    "palette": {
                                        "startToEndSteps": 5,
                                        "startToMiddleSteps": 3  # Invalid for sequential
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        results = _check_palette_schema(payload)
        sequential_check = [r for r in results if r.rule == "palette_sequential"][0]
        assert sequential_check.ok is False

    def test_diverging_palette_valid(self):
        """Diverging palette (3-color) uses startToMiddleSteps + middleToEndSteps."""
        payload = {
            "visualSpecification": {
                "style": {
                    "encodings": {
                        "fields": {
                            "F1": {
                                "colors": {
                                    "palette": {
                                        "middle": "#FFFFFF",
                                        "startToMiddleSteps": 3,
                                        "middleToEndSteps": 3
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        results = _check_palette_schema(payload)
        assert all(r.ok for r in results)

    def test_diverging_palette_empty_start_to_end_steps_ok(self):
        """Diverging palette may include empty startToEndSteps (map exports)."""
        payload = {
            "visualSpecification": {
                "style": {
                    "encodings": {
                        "fields": {
                            "F3": {
                                "colors": {
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
                            }
                        }
                    }
                }
            }
        }
        results = _check_palette_schema(payload)
        diverging_check = [r for r in results if r.rule == "palette_diverging"][0]
        assert diverging_check.ok is True

    def test_diverging_palette_invalid(self):
        """Diverging palette rejects non-empty or non-list startToEndSteps."""
        payload = {
            "visualSpecification": {
                "style": {
                    "encodings": {
                        "fields": {
                            "F1": {
                                "colors": {
                                    "palette": {
                                        "middle": "#FFFFFF",
                                        "startToEndSteps": 5  # Invalid for diverging
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        results = _check_palette_schema(payload)
        diverging_check = [r for r in results if r.rule == "palette_diverging"][0]
        assert diverging_check.ok is False


class TestMapFlowLayouts:
    """Map and Flow (Sankey) layout validation."""

    def test_visual_spec_map_required_keys(self):
        vs = {
            "layout": "Map",
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
                "background": {"type": "Map", "style": {"type": "Name", "value": "light"}},
                "encodings": {"fields": {}},
                "fieldLabels": {
                    "columns": {"showDividerLine": False, "showLabels": True},
                    "rows": {"showDividerLine": False, "showLabels": True},
                },
                "fonts": {k: {"color": "#2E2E2E", "size": 13} for k in (
                    "actionableHeaders", "axisTickLabels", "fieldLabels", "headers",
                    "legendLabels", "markLabels", "marks",
                )},
                "lines": {
                    "axisLine": {"color": "#C9C9C9"},
                    "fieldLabelDividerLine": {"color": "#C9C9C9"},
                    "separatorLine": {"color": "#C9C9C9"},
                    "zeroLine": {"color": "#C9C9C9"},
                },
                "marks": {
                    "fields": {},
                    "panes": {
                        "color": {"color": ""},
                        "isAutomaticSize": True,
                        "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": True},
                        "range": {"reverse": True},
                        "size": {"isAutomatic": True, "type": "Pixel", "value": 10},
                    },
                },
                "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
                "title": {"isVisible": True},
            },
        }
        payload = {
            "name": "M",
            "label": "M",
            "dataSource": {},
            "workspace": {},
            "fields": {},
            "interactions": [],
            "view": {"label": "d", "name": "d", "viewSpecification": {"filter": {"filters": []}, "sortOrders": {}}},
            "visualSpecification": vs,
        }
        payload["view"]["viewSpecification"]["sortOrders"] = {"columns": [], "fields": {}, "rows": []}
        res = _check_visual_spec_fields(payload)
        assert res[0].ok is True

    def test_map_marks_rejects_headers(self):
        """Map layout must not include visualSpecification.marks.headers (v66.12)."""
        vs = {
            "layout": "Map",
            "locations": ["F1"],
            "marks": {
                "fields": {},
                "headers": {
                    "encodings": [],
                    "isAutomatic": True,
                    "stack": {"isAutomatic": True, "isStacked": False},
                    "type": "Text",
                },
                "panes": {
                    "encodings": [],
                    "isAutomatic": True,
                    "stack": {"isAutomatic": True, "isStacked": False},
                    "type": "Circle",
                },
            },
            "style": {
                "background": {"type": "Map", "style": {"type": "Name", "value": "light"}},
                "encodings": {"fields": {}},
                "fieldLabels": {
                    "columns": {"showDividerLine": False, "showLabels": True},
                    "rows": {"showDividerLine": False, "showLabels": True},
                },
                "fonts": {k: {"color": "#2E2E2E", "size": 13} for k in (
                    "actionableHeaders", "axisTickLabels", "fieldLabels", "headers",
                    "legendLabels", "markLabels", "marks",
                )},
                "lines": {
                    "axisLine": {"color": "#C9C9C9"},
                    "fieldLabelDividerLine": {"color": "#C9C9C9"},
                    "separatorLine": {"color": "#C9C9C9"},
                    "zeroLine": {"color": "#C9C9C9"},
                },
                "marks": {
                    "fields": {},
                    "panes": {
                        "color": {"color": ""},
                        "isAutomaticSize": True,
                        "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": True},
                        "range": {"reverse": True},
                        "size": {"isAutomatic": True, "type": "Pixel", "value": 10},
                    },
                },
                "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
                "title": {"isVisible": True},
            },
        }
        payload = {
            "name": "M",
            "label": "M",
            "dataSource": {},
            "workspace": {},
            "fields": {},
            "interactions": [],
            "view": {"label": "d", "name": "d", "viewSpecification": {"filter": {"filters": []}, "sortOrders": {}}},
            "visualSpecification": vs,
        }
        payload["view"]["viewSpecification"]["sortOrders"] = {"columns": [], "fields": {}, "rows": []}
        results = _check_marks_structure(payload)
        bad = [r for r in results if r.rule == "map_marks_no_headers"][0]
        assert bad.ok is False

    def test_visual_spec_flow_required_keys(self):
        vs = {
            "layout": "Flow",
            "levels": ["F1", "F2"],
            "link": "F3",
            "legends": {},
            "marks": {
                "fields": {
                    "F1": {"encodings": [], "isAutomatic": True, "stack": {"isAutomatic": True, "isStacked": False}, "type": "Bar"},
                },
                "links": {
                    "encodings": [],
                    "isAutomatic": True,
                    "stack": {"isAutomatic": True, "isStacked": False},
                    "type": "Line",
                },
                "nodes": {
                    "encodings": [],
                    "isAutomatic": True,
                    "stack": {"isAutomatic": True, "isStacked": False},
                    "type": "Bar",
                },
            },
            "style": {
                "encodings": {"fields": {}},
                "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
                "fonts": {k: {"color": "#2E2E2E", "size": 13} for k in (
                    "actionableHeaders", "axisTickLabels", "fieldLabels", "headers",
                    "legendLabels", "markLabels", "marks",
                )},
                "lines": {
                    "axisLine": {"color": "#C9C9C9"},
                    "fieldLabelDividerLine": {"color": "#C9C9C9"},
                    "separatorLine": {"color": "#C9C9C9"},
                    "zeroLine": {"color": "#C9C9C9"},
                },
                "marks": {
                    "fields": {"F1": {"range": {"reverse": True}}},
                    "links": {"range": {"reverse": True}},
                    "nodes": {"range": {"reverse": True}},
                },
                "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
                "title": {"isVisible": True},
            },
        }
        payload = {
            "name": "F",
            "label": "F",
            "dataSource": {},
            "workspace": {},
            "fields": {},
            "interactions": [],
            "view": {
                "label": "d",
                "name": "d",
                "viewSpecification": {"sortOrders": {"columns": [], "fields": {}, "rows": []}},
            },
            "visualSpecification": vs,
        }
        res = _check_visual_spec_fields(payload)
        assert res[0].ok is True


class TestValidateIntegration:
    """Test full validate() function integration."""

    def test_validate_valid_payload(self, sample_viz_payload):
        """Valid payload passes all validation rules."""
        results = validate(sample_viz_payload)
        assert all(r.ok for r in results)

    def test_validate_invalid_payload(self, invalid_viz_payload_missing_fields):
        """Invalid payload fails multiple rules."""
        results = validate(invalid_viz_payload_missing_fields)
        assert any(not r.ok for r in results)

    def test_is_valid_convenience(self, sample_viz_payload):
        """is_valid() returns (bool, list) tuple."""
        ok, results = is_valid(sample_viz_payload)
        assert ok is True
        assert isinstance(results, list)
        assert all(r.ok for r in results)

    def test_is_valid_fails(self, invalid_viz_payload_missing_fields):
        """is_valid() returns False for invalid payload."""
        ok, results = is_valid(invalid_viz_payload_missing_fields)
        assert ok is False
        assert any(not r.ok for r in results)

    def test_strict_encoding_field_refs_fails_on_orphan_key(self):
        """strict_encoding_field_refs catches encoding fieldKey missing from fields."""
        payload = {
            "name": "X",
            "label": "X",
            "dataSource": {},
            "workspace": {},
            "fields": {"F1": {}, "F2": {}},
            "interactions": [],
            "view": {
                "label": "d",
                "name": "d",
                "viewSpecification": {"sortOrders": {"columns": [], "fields": {}, "rows": []}},
            },
            "visualSpecification": {
                "layout": "Flow",
                "levels": ["F1", "F2"],
                "link": "F3",
                "legends": {},
                "marks": {
                    "fields": {
                        "F1": {"encodings": [], "isAutomatic": True, "stack": {"isAutomatic": True, "isStacked": False}, "type": "Bar"},
                        "F2": {"encodings": [], "isAutomatic": True, "stack": {"isAutomatic": True, "isStacked": False}, "type": "Bar"},
                    },
                    "links": {
                        "encodings": [{"fieldKey": "F99", "type": "Color"}],
                        "isAutomatic": True,
                        "stack": {"isAutomatic": True, "isStacked": False},
                        "type": "Line",
                    },
                    "nodes": {"encodings": [], "isAutomatic": True, "stack": {"isAutomatic": True, "isStacked": False}, "type": "Bar"},
                },
                "style": {
                    "encodings": {"fields": {}},
                    "fieldLabels": {"levels": {"showDividerLine": False, "showLabels": True}},
                    "fonts": {k: {"color": "#2E2E2E", "size": 13} for k in (
                        "actionableHeaders", "axisTickLabels", "fieldLabels", "headers",
                        "legendLabels", "markLabels", "marks",
                    )},
                    "lines": {
                        "axisLine": {"color": "#C9C9C9"},
                        "fieldLabelDividerLine": {"color": "#C9C9C9"},
                        "separatorLine": {"color": "#C9C9C9"},
                        "zeroLine": {"color": "#C9C9C9"},
                    },
                    "marks": {
                        "fields": {
                            "F1": {"color": {"color": ""}, "isAutomaticSize": True, "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": True}, "range": {"reverse": True}, "size": {"isAutomatic": True, "type": "Percentage", "value": 75}},
                            "F2": {"color": {"color": ""}, "isAutomaticSize": True, "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": True}, "range": {"reverse": True}, "size": {"isAutomatic": True, "type": "Percentage", "value": 75}},
                        },
                        "links": {"color": {"color": ""}, "isAutomaticSize": True, "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": True}, "range": {"reverse": True}, "size": {"isAutomatic": True, "type": "Pixel", "value": 3}},
                        "nodes": {"color": {"color": ""}, "isAutomaticSize": True, "label": {"canOverlapLabels": False, "marksToLabel": {"type": "All"}, "showMarkLabels": True}, "range": {"reverse": True}, "size": {"isAutomatic": True, "type": "Percentage", "value": 75}},
                    },
                    "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
                    "title": {"isVisible": True},
                },
            },
        }
        ref = _check_encoding_field_refs(payload)
        assert ref[0].ok is False
        assert "F99" in ref[0].message
