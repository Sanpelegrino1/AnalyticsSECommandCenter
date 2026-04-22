"""Unit tests for lib.sdm_discovery module."""

from unittest.mock import MagicMock, patch

import pytest

from scripts.lib.sdm_discovery import discover_sdm_fields, get_sdm_details, list_sdms


class TestDiscoverSdmFields:
    """Test discover_sdm_fields function."""
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_success_with_all_field_types(self, mock_creds, mock_sf_get):
        """Test successful field discovery with all field types."""
        mock_creds.return_value = ("token", "instance")
        mock_sf_get.return_value = {
            "apiName": "Test_SDM",
            "label": "Test SDM",
            "semanticDataObjects": [
                {
                    "apiName": "Opportunity",
                    "semanticDimensions": [
                        {
                            "apiName": "StageName",
                            "dataType": "Text",
                            "label": "Stage Name",
                            "description": "Opportunity stage"
                        }
                    ],
                    "semanticMeasurements": [
                        {
                            "apiName": "Amount",
                            "aggregationType": "Sum",
                            "label": "Amount",
                            "description": "Opportunity amount"
                        }
                    ]
                }
            ],
            "semanticCalculatedDimensions": [
                {
                    "apiName": "Stage_Clc",
                    "dataType": "Text",
                    "label": "Calculated Stage",
                    "description": "Calculated stage"
                }
            ],
            "semanticCalculatedMeasurements": [
                {
                    "apiName": "Total_Amount_Clc",
                    "aggregationType": "Avg",
                    "label": "Average Amount",
                    "description": "Average amount"
                }
            ]
        }
        
        fields = discover_sdm_fields("Test_SDM")
        
        assert fields is not None
        assert "StageName" in fields
        assert fields["StageName"]["role"] == "Dimension"
        assert fields["StageName"]["objectName"] == "Opportunity"
        assert fields["StageName"]["label"] == "Stage Name"
        
        assert "Amount" in fields
        assert fields["Amount"]["role"] == "Measure"
        assert fields["Amount"]["function"] == "Sum"
        
        assert "Stage_Clc" in fields
        assert fields["Stage_Clc"]["objectName"] is None
        
        assert "Total_Amount_Clc" in fields
        assert fields["Total_Amount_Clc"]["aggregationType"] == "Avg"
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_sdm_not_found(self, mock_creds, mock_sf_get):
        """Test when SDM is not found."""
        mock_creds.return_value = ("token", "instance")
        mock_sf_get.return_value = None
        
        fields = discover_sdm_fields("NonExistent_SDM")
        
        assert fields is None
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_empty_sdm(self, mock_creds, mock_sf_get):
        """Test SDM with no fields."""
        mock_creds.return_value = ("token", "instance")
        mock_sf_get.return_value = {
            "apiName": "Empty_SDM",
            "label": "Empty SDM",
            "semanticDataObjects": [],
            "semanticCalculatedDimensions": [],
            "semanticCalculatedMeasurements": []
        }
        
        fields = discover_sdm_fields("Empty_SDM")
        
        assert fields is not None
        assert len(fields) == 0


class TestListSdms:
    """Test list_sdms function."""
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_success(self, mock_creds, mock_sf_get):
        """Test successful SDM listing."""
        mock_creds.return_value = ("token", "instance")
        mock_sf_get.return_value = {
            "semantic_models": [
                {"apiName": "SDM1", "label": "SDM 1", "dataspace": "ds1"},
                {"apiName": "SDM2", "label": "SDM 2", "dataspace": "ds2"}
            ]
        }
        
        sdms = list_sdms()
        
        assert len(sdms) == 2
        assert sdms[0]["apiName"] == "SDM1"
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_empty_list(self, mock_creds, mock_sf_get):
        """Test when no SDMs are found."""
        mock_creds.return_value = ("token", "instance")
        mock_sf_get.return_value = {"items": []}
        
        sdms = list_sdms()
        
        assert len(sdms) == 0
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_api_error(self, mock_creds, mock_sf_get):
        """Test when API returns None."""
        mock_creds.return_value = ("token", "instance")
        mock_sf_get.return_value = None
        
        sdms = list_sdms()
        
        assert len(sdms) == 0


class TestGetSdmDetails:
    """Test get_sdm_details function."""
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_success(self, mock_creds, mock_sf_get):
        """Test successful SDM detail retrieval."""
        mock_creds.return_value = ("token", "instance")
        expected_data = {"apiName": "Test_SDM", "label": "Test SDM"}
        mock_sf_get.return_value = expected_data
        
        details = get_sdm_details("Test_SDM")
        
        assert details == expected_data
    
    @patch("scripts.lib.sdm_discovery.sf_get")
    @patch("scripts.lib.sdm_discovery.get_credentials")
    def test_not_found(self, mock_creds, mock_sf_get):
        """Test when SDM is not found."""
        mock_creds.return_value = ("token", "instance")
        mock_sf_get.return_value = None
        
        details = get_sdm_details("NonExistent_SDM")
        
        assert details is None
