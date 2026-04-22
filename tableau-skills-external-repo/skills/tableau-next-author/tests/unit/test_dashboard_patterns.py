"""Unit tests for dashboard_patterns.py - pattern builders and deduplication."""

import pytest
import sys
from scripts.lib.dashboard_patterns import (
    deduplicate_filter_defs,
    get_pattern_requirements,
    validate_pattern_requirements,
    auto_select_pattern,
    apply_metric_style,
    apply_container_style,
    apply_viz_style,
    apply_filter_style,
    apply_button_style,
    apply_text_header_style,
    build_f_layout_pattern,
    build_z_layout_pattern,
    build_performance_overview_pattern,
    validate_pattern_output,
    PATTERN_REQUIREMENTS,
)
from scripts.lib.templates import FilterDef


class TestDeduplicateFilterDefs:
    """Test filter deduplication function."""

    def test_deduplicate_dict_filters(self, sample_duplicate_filters):
        """Deduplicate filters removes duplicates (dict-based)."""
        result = deduplicate_filter_defs(sample_duplicate_filters)
        assert len(result) == 2
        # First occurrence kept
        assert result[0]["fieldName"] == "StageName"
        assert result[1]["fieldName"] == "Amount"

    def test_deduplicate_filterdef_objects(self):
        """Deduplicate filters works with FilterDef objects."""
        filters = [
            FilterDef(field_name="StageName", object_name="Opportunity", label="Stage Name"),
            FilterDef(field_name="StageName", object_name="Opportunity", label="Stage Name"),  # Duplicate
            FilterDef(field_name="Amount", object_name="Opportunity", label="Amount"),
        ]
        result = deduplicate_filter_defs(filters)
        assert len(result) == 2
        assert result[0].field_name == "StageName"
        assert result[1].field_name == "Amount"

    def test_deduplicate_mixed_types(self):
        """Deduplicate filters works with mixed dict and FilterDef objects."""
        filters = [
            {"fieldName": "StageName", "objectName": "Opportunity"},
            FilterDef(field_name="StageName", object_name="Opportunity", label="Stage Name"),  # Duplicate
            {"fieldName": "Amount", "objectName": "Opportunity"},
        ]
        result = deduplicate_filter_defs(filters)
        assert len(result) == 2

    def test_no_duplicates(self, sample_filter_defs):
        """No duplicates returns original list."""
        result = deduplicate_filter_defs(sample_filter_defs)
        assert len(result) == len(sample_filter_defs)

    def test_empty_list(self):
        """Empty list returns empty list."""
        result = deduplicate_filter_defs([])
        assert result == []

    def test_warns_on_duplicate(self, capsys):
        """Deduplication warns on stderr for duplicates."""
        filters = [
            {"fieldName": "StageName", "objectName": "Opportunity"},
            {"fieldName": "StageName", "objectName": "Opportunity"},  # Duplicate
        ]
        deduplicate_filter_defs(filters)
        captured = capsys.readouterr()
        assert "Duplicate filter removed" in captured.err


class TestGetPatternRequirements:
    """Test pattern requirements lookup."""

    def test_get_f_layout_requirements(self):
        """Get F-layout requirements."""
        req = get_pattern_requirements("f_layout")
        assert req is not None
        assert req["filters"]["slots"] == 6
        assert req["metrics"]["slots"] == 3
        assert req["visualizations"]["slots"] == 5

    def test_get_z_layout_requirements(self):
        """Get Z-layout requirements."""
        req = get_pattern_requirements("z_layout")
        assert req is not None
        assert req["filters"]["slots"] == 6
        assert req["metrics"]["slots"] == 6

    def test_get_performance_overview_requirements(self):
        """Get performance overview requirements."""
        req = get_pattern_requirements("performance_overview")
        assert req is not None
        assert req["primary_metric"]["required"] is True

    def test_unknown_pattern_returns_none(self):
        """Unknown pattern returns None."""
        req = get_pattern_requirements("unknown_pattern")
        assert req is None


class TestValidatePatternRequirements:
    """Test pattern requirement validation."""

    def test_valid_f_layout(self):
        """Valid F-layout passes validation."""
        filters = [{"fieldName": f"F{i}"} for i in range(6)]
        metrics = [f"M{i}" for i in range(3)]
        visualizations = [f"V{i}" for i in range(5)]
        
        is_valid, warnings = validate_pattern_requirements(
            "f_layout",
            filters,
            metrics,
            visualizations
        )
        assert is_valid is True
        assert len(warnings) == 0

    def test_f_layout_too_few_filters(self):
        """F-layout with too few filters fails."""
        filters = [{"fieldName": "F1"}]  # Need 6
        metrics = [f"M{i}" for i in range(3)]
        visualizations = [f"V{i}" for i in range(5)]
        
        is_valid, warnings = validate_pattern_requirements(
            "f_layout",
            filters,
            metrics,
            visualizations
        )
        assert is_valid is False
        assert len(warnings) > 0
        assert "filters" in warnings[0].lower()

    def test_f_layout_too_many_filters(self):
        """F-layout with too many filters fails."""
        filters = [{"fieldName": f"F{i}"} for i in range(10)]  # Need exactly 6
        metrics = [f"M{i}" for i in range(3)]
        visualizations = [f"V{i}" for i in range(5)]
        
        is_valid, warnings = validate_pattern_requirements(
            "f_layout",
            filters,
            metrics,
            visualizations
        )
        assert is_valid is False
        assert any("filters" in w.lower() for w in warnings)

    def test_performance_overview_requires_primary_metric(self):
        """Performance overview requires primary_metric argument."""
        filters = [{"fieldName": f"F{i}"} for i in range(3)]
        metrics = [f"M{i}" for i in range(5)]
        visualizations = [f"V{i}" for i in range(5)]
        
        is_valid, warnings = validate_pattern_requirements(
            "performance_overview",
            filters,
            metrics,
            visualizations,
            primary_metric="M0"
        )
        assert is_valid is True

    def test_unknown_pattern_fails(self):
        """Unknown pattern fails validation."""
        is_valid, warnings = validate_pattern_requirements(
            "unknown_pattern",
            [],
            [],
            []
        )
        assert is_valid is False
        assert "Unknown pattern" in warnings[0]


class TestAutoSelectPattern:
    """Test pattern auto-selection logic."""

    def test_auto_select_f_layout(self):
        """Auto-select F-layout for 6 filters, 3 metrics, 5 visualizations."""
        filters = [{"fieldName": f"F{i}"} for i in range(6)]
        metrics = [f"M{i}" for i in range(3)]
        visualizations = [f"V{i}" for i in range(5)]
        
        pattern, args = auto_select_pattern(metrics, visualizations, filters)
        assert pattern == "f_layout"

    def test_auto_select_z_layout(self):
        """Auto-select Z-layout for 6 filters, 6 metrics, 5 visualizations."""
        filters = [{"fieldName": f"F{i}"} for i in range(6)]
        metrics = [f"M{i}" for i in range(6)]
        visualizations = [f"V{i}" for i in range(5)]
        
        pattern, args = auto_select_pattern(metrics, visualizations, filters)
        assert pattern == "z_layout"

    def test_auto_select_metrics_only_uses_f_layout(self):
        """Metrics without charts falls back to f_layout (create_dashboard still requires vizzes)."""
        filters = [{"fieldName": f"F{i}"} for i in range(3)]
        metrics = [f"M{i}" for i in range(8)]
        visualizations = []
        pattern, args = auto_select_pattern(metrics, visualizations, filters)
        assert pattern == "f_layout"

    def test_auto_select_partial_counts_f_layout(self):
        """Non-exact metric+viz counts default to f_layout."""
        filters = [{"fieldName": f"F{i}"} for i in range(3)]
        metrics = [f"M{i}" for i in range(4)]
        visualizations = [f"V{i}" for i in range(2)]
        pattern, args = auto_select_pattern(metrics, visualizations, filters)
        assert pattern == "f_layout"

    def test_auto_select_performance_overview(self):
        """Auto-select performance overview for 3 filters, 5 metrics, 5 visualizations."""
        filters = [{"fieldName": f"F{i}"} for i in range(3)]
        metrics = [f"M{i}" for i in range(5)]
        visualizations = [f"V{i}" for i in range(5)]
        
        pattern, args = auto_select_pattern(metrics, visualizations, filters)
        assert pattern == "performance_overview"
        assert "primary_metric" in args

    def test_auto_select_defaults_to_f_layout(self):
        """Auto-select defaults to F-layout for unmatched counts."""
        filters = [{"fieldName": "F1"}]
        metrics = []
        visualizations = []
        
        pattern, args = auto_select_pattern(metrics, visualizations, filters)
        # Should default to f_layout
        assert pattern == "f_layout"


class TestApplyMetricStyle:
    """Test apply_metric_style function."""

    def test_apply_metric_style_basic(self):
        """Apply metric style to widget."""
        widget = {
            "name": "metric1",
            "type": "metric"
        }
        
        styled = apply_metric_style(widget)
        
        assert "parameters" in styled
        assert "widgetStyle" in styled["parameters"]
        assert styled["parameters"]["widgetStyle"]["borderColor"] == "#C9C9C9"
        assert styled["parameters"]["widgetStyle"]["borderEdges"] == ["all"]
        assert styled["parameters"]["widgetStyle"]["borderRadius"] == 20

    def test_apply_metric_style_existing_parameters(self):
        """Apply metric style preserves existing parameters."""
        widget = {
            "name": "metric1",
            "type": "metric",
            "parameters": {
                "metricOption": {}
            }
        }
        
        styled = apply_metric_style(widget)
        
        assert "metricOption" in styled["parameters"]
        assert "widgetStyle" in styled["parameters"]


class TestApplyContainerStyle:
    """Test apply_container_style function."""

    def test_apply_container_style_default(self):
        """Apply container style with default border radius."""
        widget = {
            "name": "container1",
            "type": "container"
        }
        
        styled = apply_container_style(widget)
        
        assert styled["parameters"]["widgetStyle"]["borderRadius"] == 16
        assert styled["parameters"]["widgetStyle"]["borderColor"] == "#c9c9c9"
        assert styled["parameters"]["widgetStyle"]["borderEdges"] == ["all"]

    def test_apply_container_style_custom_radius(self):
        """Apply container style with custom border radius."""
        widget = {
            "name": "container1",
            "type": "container"
        }
        
        styled = apply_container_style(widget, border_radius=20)
        
        assert styled["parameters"]["widgetStyle"]["borderRadius"] == 20


class TestApplyVizStyle:
    """Test apply_viz_style function."""

    def test_apply_viz_style_default(self):
        """Apply viz style with default border radius."""
        widget = {
            "name": "viz1",
            "type": "visualization"
        }
        
        styled = apply_viz_style(widget)
        
        assert styled["parameters"]["widgetStyle"]["borderRadius"] == 16
        assert styled["parameters"]["widgetStyle"]["borderColor"] == "#C9C9C9"
        assert styled["parameters"]["widgetStyle"]["borderEdges"] == []

    def test_apply_viz_style_custom_radius(self):
        """Apply viz style with custom border radius."""
        widget = {
            "name": "viz1",
            "type": "visualization"
        }
        
        styled = apply_viz_style(widget, border_radius=12)
        
        assert styled["parameters"]["widgetStyle"]["borderRadius"] == 12


class TestApplyFilterStyle:
    """Test apply_filter_style function."""

    def test_apply_filter_style(self):
        """Apply filter style to widget."""
        widget = {
            "name": "filter1",
            "type": "filter"
        }
        
        styled = apply_filter_style(widget)
        
        assert styled["parameters"]["widgetStyle"]["backgroundColor"] == "#f3f3f3"
        assert styled["parameters"]["widgetStyle"]["borderEdges"] == []


class TestApplyButtonStyle:
    """Test apply_button_style function."""

    def test_apply_button_style_active(self):
        """Apply button style for active state."""
        widget = {
            "name": "button1",
            "type": "button"
        }
        
        styled = apply_button_style(widget, is_active=True)
        
        assert styled["parameters"]["widgetStyle"]["backgroundColor"] == "#066AFE"
        assert styled["parameters"]["widgetStyle"]["fontColor"] == "#ffffff"
        assert styled["parameters"]["widgetStyle"]["borderEdges"] == ["all"]

    def test_apply_button_style_inactive(self):
        """Apply button style for inactive state."""
        widget = {
            "name": "button1",
            "type": "button"
        }
        
        styled = apply_button_style(widget, is_active=False)
        
        assert styled["parameters"]["widgetStyle"]["fontColor"] == "#0250D9"
        assert styled["parameters"]["widgetStyle"]["borderEdges"] == ["all"]
        # Inactive buttons don't have backgroundColor set


class TestApplyTextHeaderStyle:
    """Test apply_text_header_style function."""

    def test_apply_text_header_style_default(self):
        """Apply text header style with defaults."""
        widget = {
            "name": "header1",
            "type": "text",
            "parameters": {
                "content": [
                    {
                        "attributes": {},
                        "insert": "Header Text"
                    }
                ]
            }
        }
        
        styled = apply_text_header_style(widget)
        
        assert styled["parameters"]["widgetStyle"]["borderEdges"] == []
        # Content attributes should be updated if present
        if styled["parameters"]["content"]:
            assert "size" in styled["parameters"]["content"][0]["attributes"]
            assert "color" in styled["parameters"]["content"][0]["attributes"]

    def test_apply_text_header_style_custom(self):
        """Apply text header style with custom size/color."""
        widget = {
            "name": "header1",
            "type": "text",
            "parameters": {
                "content": [
                    {
                        "attributes": {},
                        "insert": "Header Text"
                    }
                ]
            }
        }
        
        styled = apply_text_header_style(widget, size="24px", color="#000000")
        
        if styled["parameters"]["content"]:
            assert styled["parameters"]["content"][0]["attributes"]["size"] == "24px"
            assert styled["parameters"]["content"][0]["attributes"]["color"] == "#000000"


class TestBuildFLayoutPattern:
    """Test build_f_layout_pattern function."""

    def test_build_f_layout_pattern_basic(self):
        """Build F-layout pattern with recommended counts."""
        metrics = ["Metric1", "Metric2", "Metric3"]
        visualizations = ["Viz1", "Viz2", "Viz3", "Viz4", "Viz5"]
        filters = [
            FilterDef(field_name="StageName", object_name="Opportunity")
        ] * 6
        
        widgets, layout = build_f_layout_pattern(
            column_count=72,
            metrics=metrics,
            visualizations=visualizations,
            filters=filters,
            title_text="Test Dashboard",
            sdm_name="Test_SDM",
            validate=False
        )
        
        assert isinstance(widgets, dict)
        assert isinstance(layout, list)
        assert len(layout) > 0  # Should have layout widgets
        # Layout is a list of widget layout dicts (not pages)
        # Should have title, filters, metrics, visualizations
        widget_names = [w["name"] for w in layout]
        assert "title" in widget_names
        assert any("filter_" in name for name in widget_names)
        assert any("metric_" in name for name in widget_names)
        # Visualizations are named "visualization_1", "visualization_2", etc.
        viz_widget_keys = [k for k in widgets.keys() if "visualization" in k.lower()]
        assert len(viz_widget_keys) == 5

    def test_build_f_layout_pattern_fewer_widgets(self):
        """Build F-layout with fewer widgets than recommended."""
        metrics = ["Metric1"]
        visualizations = ["Viz1", "Viz2"]
        filters = [FilterDef(field_name="StageName", object_name="Opportunity")]
        
        widgets, layout = build_f_layout_pattern(
            column_count=72,
            metrics=metrics,
            visualizations=visualizations,
            filters=filters,
            title_text="Test Dashboard",
            sdm_name="Test_SDM",
            validate=False
        )
        
        # Should still build successfully with fewer widgets
        assert len(layout) >= 1


class TestBuildZLayoutPattern:
    """Test build_z_layout_pattern function."""

    def test_build_z_layout_pattern_basic(self):
        """Build Z-layout pattern."""
        metrics = ["Metric1", "Metric2", "Metric3"]
        visualizations = ["Viz1", "Viz2"]
        filters = [FilterDef(field_name="StageName", object_name="Opportunity")]
        
        widgets, layout = build_z_layout_pattern(
            column_count=72,
            metrics=metrics,
            visualizations=visualizations,
            filters=filters,
            title_text="Test Dashboard",
            sdm_name="Test_SDM"
        )
        
        assert isinstance(widgets, dict)
        assert isinstance(layout, list)
        # Z-layout should have metrics in top row
        # Layout is a list of widget layout dicts
        widget_names = [w["name"] for w in layout]
        assert any("metric_" in name for name in widget_names)


class TestBuildPerformanceOverviewPattern:
    """Test build_performance_overview_pattern function."""

    def test_build_performance_overview_pattern(self):
        """Build performance overview pattern."""
        primary_metric = "PrimaryMetric"
        secondary_metrics = ["Metric1", "Metric2", "Metric3"]
        filters = [
            FilterDef(field_name="CloseDate", object_name="Opportunity", data_type="Date")
        ]
        
        from scripts.lib.templates import PageDef
        pages = [PageDef(label="Page 1", name="page1")]
        
        widgets, layout = build_performance_overview_pattern(
            column_count=72,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics,
            visualizations=[],
            filters=filters,
            pages=pages,
            sdm_name="Test_SDM"
        )
        
        assert isinstance(widgets, dict)
        assert isinstance(layout, list)
        # Should have primary metric and secondary metrics
        # Layout is a list of page dicts with "widgets" key
        all_widgets = []
        for page in layout:
            if isinstance(page, dict) and "widgets" in page:
                all_widgets.extend(page["widgets"])
            elif isinstance(page, dict) and "name" in page:
                all_widgets.append(page)
        widget_names = [w["name"] for w in all_widgets]
        assert any("metric_" in name for name in widget_names)


class TestValidatePatternOutput:
    """Test validate_pattern_output function."""

    def test_validate_pattern_output_valid(self):
        """Validate valid pattern output."""
        widgets = {
            "widget1": {
                "name": "widget1",
                "type": "visualization",
                "source": {"name": "Viz1"}
            }
        }
        pages = [
            {
                "widgets": [
                    {"name": "widget1", "column": 0, "row": 0, "colspan": 24, "rowspan": 10}
                ]
            }
        ]
        
        is_valid, errors = validate_pattern_output(widgets, pages, column_count=72)
        
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_pattern_output_invalid_source(self):
        """Validate pattern output with invalid source (has id/label/type)."""
        widgets = {
            "widget1": {
                "name": "widget1",
                "type": "visualization",
                "source": {
                    "name": "Viz1",
                    "id": "12345"  # Should not have id
                }
            }
        }
        pages = [
            {
                "widgets": [
                    {"name": "widget1", "column": 0, "row": 0, "colspan": 24, "rowspan": 10}
                ]
            }
        ]
        
        is_valid, errors = validate_pattern_output(widgets, pages, column_count=72)
        
        assert is_valid is False
        assert any("id" in err.lower() or "source" in err.lower() for err in errors)

    def test_validate_pattern_output_column_overflow(self):
        """Validate pattern output with column overflow."""
        widgets = {
            "widget1": {
                "name": "widget1",
                "type": "visualization",
                "source": {"name": "Viz1"}
            }
        }
        pages = [
            {
                "widgets": [
                    {"name": "widget1", "column": 50, "row": 0, "colspan": 30, "rowspan": 10}
                    # column (50) + colspan (30) = 80 > 72
                ]
            }
        ]
        
        is_valid, errors = validate_pattern_output(widgets, pages, column_count=72)
        
        assert is_valid is False
        assert any("column" in err.lower() or "overflow" in err.lower() for err in errors)

    def test_validate_pattern_output_missing_widget(self):
        """Validate pattern output with missing widget in layout."""
        widgets = {
            "widget1": {
                "name": "widget1",
                "type": "visualization",
                "source": {"name": "Viz1"}
            }
        }
        pages = [
            {
                "widgets": [
                    {"name": "widget2", "column": 0, "row": 0, "colspan": 24, "rowspan": 10}
                    # widget2 not in widgets dict
                ]
            }
        ]
        
        is_valid, errors = validate_pattern_output(widgets, pages, column_count=72)
        
        assert is_valid is False
        assert any("widget2" in err or "not found" in err.lower() for err in errors)

    def test_validate_pattern_output_name_mismatch(self):
        """Validate pattern output with widget name mismatch."""
        widgets = {
            "widget1": {
                "name": "widget2",  # Name doesn't match key
                "type": "visualization",
                "source": {"name": "Viz1"}
            }
        }
        pages = [
            {
                "widgets": [
                    {"name": "widget1", "column": 0, "row": 0, "colspan": 24, "rowspan": 10}
                ]
            }
        ]
        
        is_valid, errors = validate_pattern_output(widgets, pages, column_count=72)
        
        assert is_valid is False
        assert any("name" in err.lower() and "match" in err.lower() for err in errors)
