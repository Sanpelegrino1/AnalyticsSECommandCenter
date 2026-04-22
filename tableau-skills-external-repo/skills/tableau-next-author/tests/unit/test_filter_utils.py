"""Unit tests for lib.filter_utils module."""

import sys
from unittest.mock import patch

import pytest

from scripts.lib.filter_utils import enrich_filter_labels, generate_filters_from_fields, parse_filter_arg


class TestParseFilterArg:
    """Test parse_filter_arg function."""
    
    def test_success_minimal(self):
        """Test parsing minimal filter arguments."""
        tokens = ["fieldName=Account_Industry", "objectName=Opportunity"]
        filter_def = parse_filter_arg(tokens)
        
        assert filter_def.field_name == "Account_Industry"
        assert filter_def.object_name == "Opportunity"
        assert filter_def.data_type == "Text"
        assert filter_def.selection_type == "multiple"
    
    def test_success_full(self):
        """Test parsing full filter arguments."""
        tokens = [
            "fieldName=Account_Industry",
            "objectName=Opportunity",
            "dataType=Picklist",
            "label=Account Industry",
            "selectionType=single"
        ]
        filter_def = parse_filter_arg(tokens)
        
        assert filter_def.field_name == "Account_Industry"
        assert filter_def.object_name == "Opportunity"
        assert filter_def.data_type == "Picklist"
        assert filter_def.label == "Account Industry"
        assert filter_def.selection_type == "single"
    
    def test_missing_required_fields(self):
        """Test error when required fields are missing."""
        tokens = ["fieldName=Account_Industry"]
        
        # parse_filter_arg calls sys.exit() which raises SystemExit
        with pytest.raises(SystemExit):
            parse_filter_arg(tokens)


class TestEnrichFilterLabels:
    """Test enrich_filter_labels function."""
    
    def test_enrich_with_sdm_label(self):
        """Test enriching filters with SDM field labels."""
        filters = [
            {"fieldName": "Account_Industry", "objectName": "Opportunity"}
        ]
        sdm_fields = {
            "Account_Industry": {
                "label": "Account Industry",
                "objectName": "Opportunity"
            }
        }
        
        enrich_filter_labels(filters, sdm_fields)
        
        assert filters[0]["label"] == "Account Industry"
    
    def test_skip_existing_label(self):
        """Test that existing labels are not overwritten."""
        filters = [
            {
                "fieldName": "Account_Industry",
                "objectName": "Opportunity",
                "label": "Custom Label"
            }
        ]
        sdm_fields = {
            "Account_Industry": {
                "label": "SDM Label",
                "objectName": "Opportunity"
            }
        }
        
        enrich_filter_labels(filters, sdm_fields)
        
        assert filters[0]["label"] == "Custom Label"
    
    def test_fallback_to_cleaned_name(self):
        """Test fallback to cleaned field name when SDM label missing."""
        filters = [
            {"fieldName": "Account_Industry_Clc", "objectName": "Opportunity"}
        ]
        sdm_fields = {
            "Account_Industry_Clc": {
                "label": "",
                "objectName": "Opportunity"
            }
        }
        
        enrich_filter_labels(filters, sdm_fields)
        
        assert filters[0]["label"] == "Account Industry"
    
    def test_field_not_in_sdm(self):
        """Test handling when field is not in SDM."""
        filters = [
            {"fieldName": "Unknown_Field", "objectName": "Opportunity"}
        ]
        sdm_fields = {}
        
        enrich_filter_labels(filters, sdm_fields)
        
        assert filters[0]["label"] == "Unknown Field"


class TestGenerateFiltersFromFields:
    """Test generate_filters_from_fields function."""
    
    def test_success(self):
        """Test successful filter generation."""
        field_names = ["Account_Industry", "Opportunity_Stage"]
        sdm_fields = {
            "Account_Industry": {
                "role": "Dimension",
                "objectName": "Opportunity",
                "dataType": "Text",
                "label": "Account Industry"
            },
            "Opportunity_Stage": {
                "role": "Dimension",
                "objectName": "Opportunity",
                "dataType": "Picklist",
                "label": "Opportunity Stage"
            }
        }
        
        filters = generate_filters_from_fields(field_names, sdm_fields)
        
        assert len(filters) == 2
        assert filters[0]["fieldName"] == "Account_Industry"
        assert filters[0]["label"] == "Account Industry"
        assert filters[1]["fieldName"] == "Opportunity_Stage"
    
    def test_skip_measures(self):
        """Test that measure fields are skipped."""
        field_names = ["Account_Industry", "Total_Amount"]
        sdm_fields = {
            "Account_Industry": {
                "role": "Dimension",
                "objectName": "Opportunity",
                "dataType": "Text",
                "label": "Account Industry"
            },
            "Total_Amount": {
                "role": "Measure",
                "objectName": "Opportunity",
                "dataType": "Number",
                "label": "Total Amount"
            }
        }
        
        filters = generate_filters_from_fields(field_names, sdm_fields)
        
        assert len(filters) == 1
        assert filters[0]["fieldName"] == "Account_Industry"
    
    def test_limit_num_filters(self):
        """Test limiting number of filters."""
        field_names = ["Field1", "Field2", "Field3"]
        sdm_fields = {
            "Field1": {"role": "Dimension", "objectName": "Obj", "dataType": "Text", "label": "Field 1"},
            "Field2": {"role": "Dimension", "objectName": "Obj", "dataType": "Text", "label": "Field 2"},
            "Field3": {"role": "Dimension", "objectName": "Obj", "dataType": "Text", "label": "Field 3"}
        }
        
        filters = generate_filters_from_fields(field_names, sdm_fields, num_filters=2)
        
        assert len(filters) == 2
    
    def test_field_not_found(self):
        """Test handling when field is not in SDM."""
        field_names = ["Unknown_Field"]
        sdm_fields = {}
        
        with patch("sys.stderr"):
            filters = generate_filters_from_fields(field_names, sdm_fields)
        
        assert len(filters) == 0
