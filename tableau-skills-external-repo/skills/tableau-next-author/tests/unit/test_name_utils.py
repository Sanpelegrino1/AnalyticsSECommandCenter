"""Unit tests for lib.name_utils module."""

import pytest

from scripts.lib.name_utils import (
    clean_field_name_for_display,
    generate_business_friendly_name,
    validate_business_friendly_name,
)


class TestValidateBusinessFriendlyName:
    """Test validate_business_friendly_name function."""
    
    def test_valid_name(self):
        """Test valid business-friendly name."""
        is_valid, error = validate_business_friendly_name(
            "Sales_Trend_Over_Time",
            "Sales Performance Over Time"
        )
        
        assert is_valid is True
        assert error is None
    
    def test_technical_suffix_in_name(self):
        """Test rejection of technical suffix in name."""
        is_valid, error = validate_business_friendly_name(
            "Sales_Trend_Clc",
            "Sales Trend"
        )
        
        assert is_valid is False
        assert "technical suffix" in error.lower()
    
    def test_short_label(self):
        """Test rejection of short label."""
        is_valid, error = validate_business_friendly_name(
            "Sales",
            "Sale"  # 4 characters, should fail
        )
        
        assert is_valid is False
        assert "too short" in error.lower()
    
    def test_technical_suffix_in_label(self):
        """Test rejection of technical suffix in label."""
        is_valid, error = validate_business_friendly_name(
            "Sales_Trend",
            "Sales Trend _Clc"  # Use underscore prefix to match logic
        )
        
        assert is_valid is False
        assert "technical suffix" in error.lower()


class TestCleanFieldNameForDisplay:
    """Test clean_field_name_for_display function."""
    
    def test_use_sdm_label(self):
        """Test using SDM label when available."""
        sdm_fields = {
            "Account_Industry": {
                "label": "Account Industry"
            }
        }
        
        cleaned = clean_field_name_for_display("Account_Industry", sdm_fields)
        
        assert cleaned == "Account Industry"
    
    def test_strip_technical_suffix(self):
        """Test stripping technical suffixes."""
        sdm_fields = {}
        
        cleaned = clean_field_name_for_display("Pipeline_Generation_Clc", sdm_fields)
        
        assert cleaned == "Pipeline Generation"
    
    def test_convert_to_title_case(self):
        """Test converting to title case."""
        sdm_fields = {}
        
        cleaned = clean_field_name_for_display("account_industry", sdm_fields)
        
        assert cleaned == "Account Industry"
    
    def test_empty_sdm_fields(self):
        """Test handling when field not in SDM."""
        sdm_fields = {}
        
        cleaned = clean_field_name_for_display("Unknown_Field", sdm_fields)
        
        assert cleaned == "Unknown Field"


class TestGenerateBusinessFriendlyName:
    """Test generate_business_friendly_name function."""
    
    def test_category_template(self):
        """Test name generation for category-based templates."""
        template = "revenue_by_category"
        fields = {"category": "Account_Industry", "amount": "Total_Amount"}
        sdm_fields = {
            "Account_Industry": {"label": "Account Industry"},
            "Total_Amount": {"label": "Total Amount"}
        }
        
        name, label = generate_business_friendly_name(template, fields, sdm_fields)
        
        assert "Account Industry" in label
        assert "Analysis" in label
        assert name == label.replace(" ", "_")
    
    def test_date_template(self):
        """Test name generation for date-based templates."""
        template = "trend_over_time"
        fields = {"date": "Close_Date", "measure": "Total_Amount"}
        sdm_fields = {
            "Close_Date": {"label": "Close Date"},
            "Total_Amount": {"label": "Total Amount"}
        }
        
        name, label = generate_business_friendly_name(template, fields, sdm_fields)
        
        assert "Total Amount" in label
        assert "Trend" in label
    
    def test_multi_series_line(self):
        """Test name generation for multi-series line chart."""
        template = "multi_series_line"
        fields = {
            "date": "Close_Date",
            "measure": "Total_Amount",
            "color_dim": "Opportunity_Type"
        }
        sdm_fields = {
            "Close_Date": {"label": "Close Date"},
            "Total_Amount": {"label": "Total Amount"},
            "Opportunity_Type": {"label": "Opportunity Type"}
        }
        
        name, label = generate_business_friendly_name(template, fields, sdm_fields)
        
        assert "Total Amount" in label
        assert "Trend" in label
        assert "Opportunity Type" in label
    
    def test_heatmap_template(self):
        """Test name generation for heatmap template."""
        template = "heatmap_grid"
        fields = {
            "row_dim": "Account_Industry",
            "col_dim": "Opportunity_Stage",
            "measure": "Total_Amount"
        }
        sdm_fields = {
            "Account_Industry": {"label": "Account Industry"},
            "Opportunity_Stage": {"label": "Opportunity Stage"},
            "Total_Amount": {"label": "Total Amount"}
        }
        
        name, label = generate_business_friendly_name(template, fields, sdm_fields)
        
        assert "Total Amount" in label
        assert "Account Industry" in label
        assert "Opportunity Stage" in label
    
    def test_scatter_template(self):
        """Test name generation for scatter plot template."""
        template = "scatter_correlation"
        # When category is present, it takes precedence over x_measure/y_measure
        # So we test without category to get x_measure vs y_measure format
        fields = {
            "x_measure": "Total_Amount",
            "y_measure": "Probability"
        }
        sdm_fields = {
            "Total_Amount": {"label": "Total Amount"},
            "Probability": {"label": "Probability"}
        }
        
        name, label = generate_business_friendly_name(template, fields, sdm_fields)
        
        # Scatter plots use x_measure vs y_measure format
        assert "Total Amount" in label
        assert "Probability" in label
        assert "vs" in label
    
    def test_fallback_template(self):
        """Test fallback name generation."""
        template = "unknown_template"
        fields = {"measure": "Total_Amount"}
        sdm_fields = {
            "Total_Amount": {"label": "Total Amount"}
        }
        
        name, label = generate_business_friendly_name(template, fields, sdm_fields)
        
        assert "Total Amount" in label
        assert name == label.replace(" ", "_")
