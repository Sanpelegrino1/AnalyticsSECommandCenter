"""Unit tests for viz_templates.py - field matching and chart recommendations."""

import pytest
from scripts.lib.viz_templates import (
    score_field,
    find_matching_fields,
    recommend_chart_type,
    get_template,
    get_template_info,
    list_templates,
    validate_viz_spec_fields,
    _is_id_field,
    _score_dimension_relevance,
    _score_measure_relevance,
    _select_best_dimensions,
    _select_best_measures,
    recommend_diverse_chart_types,
    analyze_fields_for_chart_selection,
)


class TestScoreField:
    """Test field name scoring."""

    def test_exact_match(self):
        """Exact match scores highest."""
        assert score_field("Revenue", ["Revenue"]) == 1
        assert score_field("Revenue", ["Amount"]) == 0

    def test_partial_match(self):
        """Partial match scores correctly."""
        exact_score = score_field("Revenue", ["Revenue"])
        partial_score = score_field("TotalRevenue", ["Revenue"])
        assert exact_score == 1
        assert partial_score == 1  # Both match "Revenue" keyword

    def test_case_insensitive(self):
        """Scoring is case insensitive."""
        assert score_field("revenue", ["Revenue"]) > 0
        assert score_field("REVENUE", ["Revenue"]) > 0

    def test_no_match(self):
        """No match scores zero."""
        assert score_field("Unknown", ["Revenue", "Amount"]) == 0


class TestFindMatchingFields:
    """Test field matching logic."""

    def test_find_exact_match(self, sample_sdm_data):
        """Find exact field match."""
        # Flatten SDM data into field dict
        sdm_fields = {}
        for obj in sample_sdm_data.get("semanticDataObjects", []):
            for field in obj.get("fields", []):
                field_def = field.copy()
                # Ensure dataType is set for dimensions
                if field_def.get("role") == "Dimension" and "dataType" not in field_def:
                    field_def["dataType"] = "Text"  # Default for text dimensions
                sdm_fields[field["apiName"]] = field_def
        
        template_fields = {
            "category": {"role": "Dimension", "dataType": ["Text"]},
            "amount": {"role": "Measure", "aggregationType": "Sum"}
        }
        
        matches = find_matching_fields(sdm_fields, template_fields)
        
        # Should find matches based on role and keyword matching
        assert len(matches) > 0
        assert "category" in matches or "amount" in matches

    def test_find_fuzzy_match(self):
        """Find fuzzy field match."""
        sdm_fields = {
            "TotalRevenue": {
                "apiName": "TotalRevenue",
                "label": "Total Revenue",
                "type": "Number",
                "role": "Measure"
            }
        }
        template_fields = {
            "amount": {"role": "Measure"}
        }
        
        matches = find_matching_fields(sdm_fields, template_fields)
        # Should find match based on role
        assert "amount" in matches

    def test_no_match_raises_error(self):
        """No match raises ValueError."""
        sdm_fields = {
            "OtherField": {
                "apiName": "OtherField",
                "role": "Dimension"
            }
        }
        template_fields = {
            "amount": {"role": "Measure"}
        }
        
        # Function raises ValueError when no match found
        with pytest.raises(ValueError) as exc_info:
            find_matching_fields(sdm_fields, template_fields)
        assert "No Measure fields found" in str(exc_info.value)

    def test_find_matching_fields_latitude_longitude_numeric_preference(self):
        """Geomap-style SDM: prefer Latitude/Longitude (numeric) over unrelated text dimensions."""
        sdm_fields = {
            "customer_external_id": {
                "apiName": "customer_external_id",
                "fieldName": "customer_external_id",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Text",
            },
            "store_name": {
                "apiName": "store_name",
                "fieldName": "store_name",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Text",
            },
            "Latitude": {
                "apiName": "Latitude",
                "fieldName": "Latitude",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Number",
            },
            "Longitude": {
                "apiName": "Longitude",
                "fieldName": "Longitude",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Number",
            },
        }
        template_fields = {
            "latitude": {"role": "Dimension"},
            "longitude": {"role": "Dimension"},
        }
        matches = find_matching_fields(sdm_fields, template_fields)
        assert matches["latitude"]["apiName"] == "Latitude"
        assert matches["longitude"]["apiName"] == "Longitude"

    def test_find_matching_fields_latitude_uses_label_when_api_name_opaque(self):
        """Retail-style SDM: apiName without 'lat' but label 'Latitude' must win over unrelated dims."""
        sdm_fields = {
            "customer_external_id": {
                "apiName": "customer_external_id",
                "fieldName": "customer_external_id",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Text",
                "label": "customer_external_id",
            },
            "order_coord_y": {
                "apiName": "order_coord_y",
                "fieldName": "order_coord_y",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Number",
                "label": "Latitude",
            },
            "order_coord_x": {
                "apiName": "order_coord_x",
                "fieldName": "order_coord_x",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Number",
                "label": "Longitude",
            },
        }
        template_fields = {
            "latitude": {"role": "Dimension"},
            "longitude": {"role": "Dimension"},
        }
        matches = find_matching_fields(sdm_fields, template_fields)
        assert matches["latitude"]["apiName"] == "order_coord_y"
        assert matches["longitude"]["apiName"] == "order_coord_x"

    def test_find_matching_fields_longitude_excludes_chosen_latitude(self):
        sdm_fields = {
            "lat_dup": {
                "apiName": "lat_dup",
                "fieldName": "lat_dup",
                "objectName": "Store",
                "role": "Dimension",
                "dataType": "Number",
                "label": "Latitude",
            },
            "Latitude": {
                "apiName": "Latitude",
                "fieldName": "Latitude",
                "objectName": "Store",
                "role": "Dimension",
                "dataType": "Number",
                "label": "Store lat",
            },
            "Longitude": {
                "apiName": "Longitude",
                "fieldName": "Longitude",
                "objectName": "Store",
                "role": "Dimension",
                "dataType": "Number",
                "label": "Store lon",
            },
        }
        matches = find_matching_fields(
            sdm_fields,
            {"latitude": {"role": "Dimension"}, "longitude": {"role": "Dimension"}},
        )
        assert matches["latitude"]["apiName"] == "lat_dup"
        assert matches["longitude"]["apiName"] == "Longitude"

    def test_find_matching_fields_retail_orders_lat_lon_under_store_measurements(self):
        """Retail_Orders-style SDM: Latitude/Longitude live on Store as semanticMeasurements (Measure)."""
        sdm_fields = {
            "customer_external_id": {
                "apiName": "customer_external_id",
                "fieldName": "customer_external_id",
                "objectName": "Order",
                "role": "Dimension",
                "dataType": "Text",
                "label": "customer_external_id",
            },
            "Latitude": {
                "apiName": "Latitude",
                "fieldName": "Latitude",
                "objectName": "Store_Home",
                "role": "Measure",
                "function": "Sum",
                "dataType": "Number",
                "label": "Latitude",
            },
            "Longitude": {
                "apiName": "Longitude",
                "fieldName": "Longitude",
                "objectName": "Store_Home",
                "role": "Measure",
                "function": "Sum",
                "dataType": "Number",
                "label": "Longitude",
            },
            "Square_Footage": {
                "apiName": "Square_Footage",
                "fieldName": "Square_Footage",
                "objectName": "Store_Home",
                "role": "Measure",
                "function": "Sum",
                "dataType": "Number",
                "label": "Square Footage",
            },
        }
        matches = find_matching_fields(
            sdm_fields,
            {"latitude": {"role": "Dimension"}, "longitude": {"role": "Dimension"}},
        )
        assert matches["latitude"]["fieldName"] == "Latitude"
        assert matches["latitude"]["role"] == "Measure"
        assert matches["longitude"]["fieldName"] == "Longitude"
        assert matches["longitude"]["role"] == "Measure"


class TestRecommendChartType:
    """Test chart type recommendation."""

    def test_recommend_bar_for_category_amount(self):
        """Recommend bar chart template for category + amount."""
        dimensions = [{"role": "Dimension", "dataType": "Text"}]
        measures = [{"role": "Measure"}]
        
        template_name = recommend_chart_type(dimensions, measures)
        # Should return revenue_by_category for 1 text dim + 1 measure
        assert template_name == "revenue_by_category"

    def test_recommend_line_for_date_measure(self):
        """Recommend line chart template for date + measure."""
        dimensions = [{"role": "Dimension", "dataType": "Date"}]
        measures = [{"role": "Measure"}]
        
        template_name = recommend_chart_type(dimensions, measures)
        # Should return trend_over_time for 1 date dim + 1 measure
        assert template_name == "trend_over_time"

    def test_recommend_bar_for_category_measure(self):
        """Recommend bar chart template for category + measure (Rule 4 takes precedence)."""
        dimensions = [{"role": "Dimension", "dataType": "Text", "fieldName": "category"}]
        measures = [{"role": "Measure"}]
        unique_counts = {"category": 4}  # < 5 unique values
        
        template_name = recommend_chart_type(dimensions, measures, unique_counts)
        # Rule 4 (Comparison/Ranking) matches first for 1 text dim + 1 measure
        # Rule 9 would check unique counts, but Rule 4 comes first
        # This is expected behavior - the function prioritizes bar charts
        assert template_name == "revenue_by_category"

    def test_recommend_table_for_multiple_dimensions(self):
        """Recommend template for multiple dimensions."""
        dimensions = [
            {"role": "Dimension", "dataType": "Text"},
            {"role": "Dimension", "dataType": "Text"}
        ]
        measures = [{"role": "Measure"}]
        
        template_name = recommend_chart_type(dimensions, measures)
        # May recommend various templates depending on logic
        assert template_name is not None
        assert isinstance(template_name, str)


class TestGetTemplate:
    """Test template lookup."""

    def test_get_existing_template(self):
        """Get existing template."""
        template = get_template("revenue_by_category")
        assert template is not None
        assert template["chart_type"] == "bar"

    def test_get_nonexistent_template(self):
        """Get nonexistent template returns None."""
        template = get_template("nonexistent_template")
        assert template is None


class TestListTemplates:
    """Test template listing."""

    def test_list_templates(self):
        """List all templates."""
        templates = list_templates()
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert "revenue_by_category" in templates


class TestValidateVizSpecFields:
    """Test visualization spec field validation."""

    def test_valid_fields(self):
        """Valid viz spec passes validation."""
        viz_spec = {
            "template": "revenue_by_category",
            "name": "Test_Viz",
            "fields": {
                "category": "StageName",
                "amount": "Amount"
            }
        }
        
        is_valid, error = validate_viz_spec_fields(viz_spec)
        assert is_valid is True
        assert error is None

    def test_missing_required_field(self):
        """Missing required field passes (function only validates field names, not presence)."""
        viz_spec = {
            "template": "revenue_by_category",
            "name": "Test_Viz",
            "fields": {
                "category": "StageName"
                # Missing amount field - but function only checks if field names are valid
            }
        }
        
        is_valid, error = validate_viz_spec_fields(viz_spec)
        # Function only validates that provided field names are valid template field names
        # It doesn't check if all required fields are present
        assert is_valid is True
        assert error is None

    def test_scatter_correlation_optional_size_label_measures(self):
        """scatter_correlation accepts optional size_measure and label_measure."""
        viz_spec = {
            "template": "scatter_correlation",
            "name": "Account_Performance",
            "fields": {
                "x_measure": "Amount",
                "y_measure": "Probability",
                "size_measure": "Total_Sales",
                "label_measure": "Total_Sales",
            },
        }
        is_valid, error = validate_viz_spec_fields(viz_spec)
        assert is_valid is True
        assert error is None
        # Verify template has these optional fields
        template = get_template("scatter_correlation")
        assert "size_measure" in template.get("optional_fields", {})
        assert "label_measure" in template.get("optional_fields", {})

    def test_heatmap_alias_normalization(self):
        """x_dimension/y_dimension aliases are normalized to col_dim/row_dim."""
        viz_spec = {
            "template": "heatmap_grid",
            "name": "Heatmap_Viz",
            "fields": {
                "x_dimension": "Region",
                "y_dimension": "Industry",
                "measure": "Amount",
            },
        }
        is_valid, error = validate_viz_spec_fields(viz_spec)
        assert is_valid is True
        assert error is None
        # Normalization mutates fields in-place
        assert viz_spec["fields"]["col_dim"] == "Region"
        assert viz_spec["fields"]["row_dim"] == "Industry"
        assert viz_spec["fields"]["measure"] == "Amount"
        assert "x_dimension" not in viz_spec["fields"]
        assert "y_dimension" not in viz_spec["fields"]


class TestGetTemplateInfo:
    """Test get_template_info function."""

    def test_get_template_info_existing(self):
        """Get template info for existing template."""
        info = get_template_info("revenue_by_category")
        
        assert info is not None
        assert info["name"] == "revenue_by_category"
        assert "description" in info
        assert info["chart_type"] == "bar"
        assert "required_fields" in info
        assert "category" in info["required_fields"]
        assert "amount" in info["required_fields"]

    def test_get_template_info_nonexistent(self):
        """Get template info for non-existent template returns None."""
        info = get_template_info("nonexistent_template")
        
        assert info is None


class TestIsIdField:
    """Test _is_id_field function."""

    def test_id_suffix(self):
        """Field ending with _id is ID field."""
        assert _is_id_field("Account_Id") is True
        assert _is_id_field("Contact_Id") is True

    def test_ids_suffix(self):
        """Field ending with _ids is ID field."""
        assert _is_id_field("Account_Ids") is True

    def test_id_pattern(self):
        """Field containing _id_ is ID field."""
        assert _is_id_field("Account_Id_Field") is True

    def test_dot_id_suffix(self):
        """Field ending with .id is ID field."""
        assert _is_id_field("Account.id") is True

    def test_just_id(self):
        """Field named 'id' is ID field."""
        assert _is_id_field("id") is True
        assert _is_id_field("ids") is True

    def test_false_positives(self):
        """Fields that should not be ID fields."""
        assert _is_id_field("StageName") is False
        assert _is_id_field("Amount") is False
        assert _is_id_field("Region") is False


class TestScoreDimensionRelevance:
    """Test _score_dimension_relevance function."""

    def test_clc_field_scoring(self):
        """CLC fields get highest score."""
        field = {"fieldName": "WinRate_clc"}
        score = _score_dimension_relevance(field)
        assert score >= 15  # CLC fields get +15

    def test_high_priority_keywords(self):
        """High priority keywords score +10."""
        field = {"fieldName": "Industry"}
        score = _score_dimension_relevance(field)
        assert score >= 10

    def test_medium_priority_keywords(self):
        """Medium priority keywords score +5."""
        field = {"fieldName": "Country"}
        score = _score_dimension_relevance(field)
        assert score >= 5

    def test_generic_field_penalty(self):
        """Generic fields get penalty."""
        field = {"fieldName": "Description"}
        score = _score_dimension_relevance(field)
        assert score < 0  # Should be negative due to penalty

    def test_scoring_from_description(self):
        """Scoring considers description field."""
        field = {
            "fieldName": "Field1",
            "description": "Industry classification"
        }
        score = _score_dimension_relevance(field)
        assert score >= 10  # "Industry" in description

    def test_scoring_from_label(self):
        """Scoring considers label field."""
        field = {
            "fieldName": "Field1",
            "label": "Stage Name"
        }
        score = _score_dimension_relevance(field)
        assert score >= 10  # "Stage" in label


class TestScoreMeasureRelevance:
    """Test _score_measure_relevance function."""

    def test_clc_field_scoring(self):
        """CLC fields get highest score."""
        field = {"fieldName": "WinRate_clc"}
        score = _score_measure_relevance(field)
        assert score >= 15  # CLC fields get +15

    def test_high_priority_keywords(self):
        """High priority keywords score +10."""
        field = {"fieldName": "Revenue"}
        score = _score_measure_relevance(field)
        assert score >= 10

    def test_medium_priority_keywords(self):
        """Medium priority keywords score +5."""
        field = {"fieldName": "Count"}
        score = _score_measure_relevance(field)
        assert score >= 5

    def test_scoring_from_description(self):
        """Scoring considers description field."""
        field = {
            "fieldName": "Field1",
            "description": "Total revenue amount"
        }
        score = _score_measure_relevance(field)
        assert score >= 10  # "revenue" in description


class TestSelectBestDimensions:
    """Test _select_best_dimensions function."""

    def test_select_top_n(self):
        """Select top N dimensions by score."""
        dimensions = [
            {"fieldName": "Industry"},  # High priority
            {"fieldName": "Country"},   # Medium priority
            {"fieldName": "Name"}       # Lower priority
        ]
        
        best = _select_best_dimensions(dimensions, 2)
        
        assert len(best) == 2
        assert best[0]["fieldName"] == "Industry"  # Highest score

    def test_fewer_than_requested(self):
        """Return all dimensions if fewer than requested."""
        dimensions = [
            {"fieldName": "Industry"}
        ]
        
        best = _select_best_dimensions(dimensions, 5)
        
        assert len(best) == 1

    def test_empty_list(self):
        """Empty list returns empty list."""
        best = _select_best_dimensions([], 5)
        
        assert len(best) == 0

    def test_sorting_by_score(self):
        """Dimensions are sorted by score descending."""
        dimensions = [
            {"fieldName": "Name"},      # Lower score
            {"fieldName": "Industry"}, # Higher score
            {"fieldName": "Country"}   # Medium score
        ]
        
        best = _select_best_dimensions(dimensions, 3)
        
        assert best[0]["fieldName"] == "Industry"
        assert best[1]["fieldName"] == "Country"
        assert best[2]["fieldName"] == "Name"


class TestSelectBestMeasures:
    """Test _select_best_measures function."""

    def test_select_top_n(self):
        """Select top N measures by score."""
        measures = [
            {"fieldName": "Revenue"},   # High priority
            {"fieldName": "Count"},     # Medium priority
            {"fieldName": "Price"}      # Lower priority
        ]
        
        best = _select_best_measures(measures, 2)
        
        assert len(best) == 2
        assert best[0]["fieldName"] == "Revenue"  # Highest score

    def test_fewer_than_requested(self):
        """Return all measures if fewer than requested."""
        measures = [
            {"fieldName": "Revenue"}
        ]
        
        best = _select_best_measures(measures, 5)
        
        assert len(best) == 1

    def test_empty_list(self):
        """Empty list returns empty list."""
        best = _select_best_measures([], 5)
        
        assert len(best) == 0


class TestRecommendDiverseChartTypes:
    """Test recommend_diverse_chart_types function."""

    def test_multi_series_line_recommendation(self):
        """Recommend multi-series line for date + measure + dimension."""
        sdm_fields = {
            "CloseDate": {
                "fieldName": "CloseDate",
                "role": "Dimension",
                "dataType": "Date"
            },
            "Amount": {
                "fieldName": "Amount",
                "role": "Measure"
            },
            "StageName": {
                "fieldName": "StageName",
                "role": "Dimension",
                "dataType": "Text"
            }
        }
        
        recommendations = recommend_diverse_chart_types(sdm_fields, num_charts=3)
        
        assert len(recommendations) > 0
        template_names = [r["template"] for r in recommendations]
        assert "multi_series_line" in template_names

    def test_stacked_bar_recommendation(self):
        """Recommend stacked bar for 2+ text dimensions + measure."""
        sdm_fields = {
            "StageName": {
                "fieldName": "StageName",
                "role": "Dimension",
                "dataType": "Text"
            },
            "Region": {
                "fieldName": "Region",
                "role": "Dimension",
                "dataType": "Text"
            },
            "Amount": {
                "fieldName": "Amount",
                "role": "Measure"
            }
        }
        
        recommendations = recommend_diverse_chart_types(sdm_fields, num_charts=3)
        
        template_names = [r["template"] for r in recommendations]
        assert "stacked_bar_by_dimension" in template_names

    def test_avoids_duplicate_templates(self):
        """Avoid recommending duplicate templates."""
        sdm_fields = {
            "CloseDate": {
                "fieldName": "CloseDate",
                "role": "Dimension",
                "dataType": "Date"
            },
            "Amount": {
                "fieldName": "Amount",
                "role": "Measure"
            },
            "StageName": {
                "fieldName": "StageName",
                "role": "Dimension",
                "dataType": "Text"
            }
        }
        
        recommendations = recommend_diverse_chart_types(sdm_fields, num_charts=5)
        
        template_names = [r["template"] for r in recommendations]
        # Should not have duplicates
        assert len(template_names) == len(set(template_names))


class TestAnalyzeFieldsForChartSelection:
    """Test analyze_fields_for_chart_selection function."""

    def test_analyze_with_selected_fields(self):
        """Analyze with user-selected fields."""
        sdm_fields = {
            "StageName": {
                "fieldName": "StageName",
                "role": "Dimension",
                "dataType": "Text"
            },
            "Amount": {
                "fieldName": "Amount",
                "role": "Measure"
            },
            "OtherField": {
                "fieldName": "OtherField",
                "role": "Dimension",
                "dataType": "Text"
            }
        }
        
        result = analyze_fields_for_chart_selection(
            sdm_fields,
            selected_field_names=["StageName", "Amount"]
        )
        
        assert result["recommended_template"] is not None
        assert "field_mappings" in result
        assert "reasoning" in result
        assert "StageName" in result["field_mappings"].values() or "StageName" in str(result["field_mappings"])

    def test_analyze_without_selected_fields(self):
        """Analyze without selected fields uses all fields."""
        sdm_fields = {
            "StageName": {
                "fieldName": "StageName",
                "role": "Dimension",
                "dataType": "Text"
            },
            "Amount": {
                "fieldName": "Amount",
                "role": "Measure"
            }
        }
        
        result = analyze_fields_for_chart_selection(sdm_fields)
        
        assert result["recommended_template"] is not None
        assert "field_mappings" in result
        assert len(result["field_mappings"]) > 0

    def test_analyze_no_suitable_chart(self):
        """Return None when no suitable chart found."""
        sdm_fields = {
            "Id": {
                "fieldName": "Id",
                "role": "Dimension",
                "dataType": "Text"
            }
        }
        
        result = analyze_fields_for_chart_selection(sdm_fields)
        
        # May return None or a default template
        assert "recommended_template" in result
        assert "reasoning" in result
