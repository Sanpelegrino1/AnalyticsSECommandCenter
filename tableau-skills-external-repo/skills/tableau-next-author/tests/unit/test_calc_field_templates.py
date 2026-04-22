"""Unit tests for calc_field_templates.py - calculated field builders."""

import pytest
from scripts.lib.calc_field_templates import (
    win_rate,
    days_between,
    bucket_amount,
    is_equal,
    count_distinct,
    percentage_of_total,
    build_calculated_measurement,
    build_calculated_dimension,
    validate_calc_field,
)


class TestFormulaTemplates:
    """Test formula template functions."""

    def test_win_rate(self):
        """Win rate formula generates correctly."""
        formula = win_rate("Won_Count", "Total_Count")
        assert "Won_Count" in formula
        assert "Total_Count" in formula
        assert "SUM" in formula
        assert "/" in formula

    def test_days_between(self):
        """Days between formula generates correctly."""
        formula = days_between("StartDate", "EndDate")
        assert "StartDate" in formula
        assert "EndDate" in formula
        assert "DATEDIFF" in formula

    def test_bucket_amount(self):
        """Bucket amount formula generates correctly."""
        formula = bucket_amount("Amount", 10000, 50000)
        assert "Amount" in formula
        assert "Small" in formula
        assert "Medium" in formula
        assert "Large" in formula

    def test_is_equal(self):
        """Is equal formula generates correctly."""
        formula = is_equal("Stage", "Won")
        assert "Stage" in formula
        assert "Won" in formula
        assert "=" in formula

    def test_count_distinct(self):
        """Count distinct formula generates correctly."""
        formula = count_distinct("AccountId")
        assert "AccountId" in formula
        assert "COUNTD" in formula

    def test_percentage_of_total(self):
        """Percentage of total formula generates correctly."""
        formula = percentage_of_total("Amount")
        assert "Amount" in formula
        assert "TOTAL" in formula
        assert "/" in formula


class TestBuildCalculatedMeasurement:
    """Test calculated measurement builder."""

    def test_build_measurement_basic(self):
        """Build basic calculated measurement."""
        payload = build_calculated_measurement(
            api_name="Test_Measure_clc",
            label="Test Measure",
            expression="SUM([Amount])",
            aggregation_type="Sum",
            data_type="Number"
        )
        
        assert payload["apiName"] == "Test_Measure_clc"
        assert payload["label"] == "Test Measure"
        assert payload["expression"] == "SUM([Amount])"
        # Expression contains SUM, so aggregationType becomes UserAgg
        assert payload["aggregationType"] == "UserAgg"
        assert payload["dataType"] == "Number"

    def test_build_measurement_useragg(self):
        """Build measurement with UserAgg preserves it."""
        payload = build_calculated_measurement(
            api_name="Test_Measure_clc",
            label="Test Measure",
            expression="AVG([Amount])",
            aggregation_type="UserAgg",
            data_type="Number"
        )
        
        assert payload["aggregationType"] == "UserAgg"

    def test_build_measurement_currency(self):
        """Build measurement with Currency data type."""
        payload = build_calculated_measurement(
            api_name="Revenue_clc",
            label="Revenue",
            expression="SUM([Amount])",
            aggregation_type="Sum",
            data_type="Currency"
        )
        
        assert payload["dataType"] == "Currency"


class TestBuildCalculatedDimension:
    """Test calculated dimension builder."""

    def test_build_dimension_basic(self):
        """Build basic calculated dimension."""
        payload = build_calculated_dimension(
            api_name="Test_Dim_clc",
            label="Test Dimension",
            expression="[Stage] = 'Won'",
            data_type="Boolean"
        )
        
        assert payload["apiName"] == "Test_Dim_clc"
        assert payload["label"] == "Test Dimension"
        assert payload["expression"] == "[Stage] = 'Won'"
        assert payload["dataType"] == "Boolean"

    def test_build_dimension_text(self):
        """Build dimension with Text data type."""
        payload = build_calculated_dimension(
            api_name="Bucket_clc",
            label="Bucket",
            expression="IF [Amount] < 10000 THEN 'Small' ELSE 'Large' END",
            data_type="Text"
        )
        
        assert payload["dataType"] == "Text"

    def test_build_dimension_number(self):
        """Build dimension with Number data type."""
        payload = build_calculated_dimension(
            api_name="Days_To_Close_clc",
            label="Days to Close",
            expression="DATEDIFF('day', [CreatedDate], [CloseDate])",
            data_type="Number"
        )
        
        assert payload["dataType"] == "Number"


class TestValidateCalcField:
    """Test calculated field validation."""

    def test_valid_measurement(self):
        """Valid measurement passes validation."""
        payload = build_calculated_measurement(
            api_name="Test_clc",
            label="Test",
            expression="SUM([Amount])",
            aggregation_type="Sum",
            data_type="Number"
        )
        
        is_valid, errors = validate_calc_field(
            payload["apiName"],
            "measurements",
            aggregation_type=payload.get("aggregationType"),
            data_type=payload.get("dataType"),
            expression=payload.get("expression")
        )
        assert is_valid is True
        assert len(errors) == 0

    def test_valid_dimension(self):
        """Valid dimension passes validation."""
        payload = build_calculated_dimension(
            api_name="Test_clc",
            label="Test",
            expression="[Stage] = 'Won'",
            data_type="Boolean"
        )
        
        is_valid, errors = validate_calc_field(
            payload["apiName"],
            "dimensions",
            data_type=payload.get("dataType"),
            expression=payload.get("expression")
        )
        assert is_valid is True
        assert len(errors) == 0

    def test_missing_api_name(self):
        """Missing apiName fails validation."""
        is_valid, errors = validate_calc_field(
            "",
            "measurements",
            expression="SUM([Amount])"
        )
        assert is_valid is False
        assert any("apiName" in err.lower() or "api name" in err.lower() for err in errors)

    def test_missing_expression(self):
        """Missing expression passes validation (expression is optional)."""
        is_valid, errors = validate_calc_field(
            "Test_clc",
            "measurements",
            expression=None
        )
        # Expression is optional - validation only checks API name format
        assert is_valid is True
        assert len(errors) == 0
