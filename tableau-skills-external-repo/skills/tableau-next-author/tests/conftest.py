"""Pytest fixtures and shared test utilities."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest
import responses


# Test credentials
TEST_TOKEN = "test_access_token_12345"
TEST_INSTANCE = "https://test.salesforce.com"


@pytest.fixture
def mock_sf_credentials(monkeypatch):
    """Mock Salesforce credentials environment variables."""
    monkeypatch.setenv("SF_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("SF_INSTANCE", TEST_INSTANCE)
    return TEST_TOKEN, TEST_INSTANCE


@pytest.fixture
def mock_sf_api_responses():
    """Context manager for mocking Salesforce API responses."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def sample_viz_payload() -> Dict[str, Any]:
    """Valid bar chart visualization payload."""
    return {
        "name": "Test_Bar_Chart",
        "label": "Test Bar Chart",
        "dataSource": {
            "name": "Test_SDM",
            "label": "Test SDM",
            "type": "SemanticModel"
        },
        "workspace": {
            "name": "Test_Workspace",
            "label": "Test Workspace"
        },
        "interactions": [],
        "fields": {
            "F1": {
                "type": "Field",
                "displayCategory": "Discrete",
                "role": "Dimension",
                "objectName": "Opportunity",
                "fieldName": "StageName"
            },
            "F2": {
                "type": "Field",
                "displayCategory": "Continuous",
                "role": "Measure",
                "objectName": "Opportunity",
                "fieldName": "Amount",
                "function": "Sum"
            }
        },
        "visualSpecification": {
            "layout": "Vizql",
            "columns": ["F1"],
            "rows": [],
            "measureValues": [],
            "mode": "Visualization",
            "referenceLines": {},
            "forecasts": {},
            "marks": {
                "panes": {
                    "type": "Bar",
                    "stack": {
                        "isAutomatic": True,
                        "isStacked": True
                    },
                    "encodings": [
                        {
                            "type": "Label",
                            "fieldKey": "F2"
                        }
                    ],
                },
                "headers": {
                    "encodings": [],
                    "isAutomatic": True,
                    "stack": {"isAutomatic": True, "isStacked": False},
                    "type": "Text",
                }
            },
            "legends": {},
            "style": {
                "fit": "Entire",
                "fonts": {
                    "actionableHeaders": {"fontSize": 12},
                    "axisTickLabels": {"fontSize": 11},
                    "fieldLabels": {"fontSize": 11},
                    "headers": {"fontSize": 12},
                    "legendLabels": {"fontSize": 11},
                    "markLabels": {"fontSize": 11},
                    "marks": {"fontSize": 11}
                },
                "lines": {
                    "axisLine": {"width": 1},
                    "fieldLabelDividerLine": {"width": 1},
                    "separatorLine": {"width": 1},
                    "zeroLine": {"width": 1}
                },
                "axis": {
                    "fields": {
                        "F2": {
                            "defaults": {
                                "format": {
                                    "type": "Number",
                                    "precision": 0
                                }
                            }
                        }
                    }
                },
                "encodings": {
                    "fields": {
                        "F2": {
                            "defaults": {
                                "format": {
                                    "type": "Number",
                                    "precision": 0
                                }
                            }
                        }
                    }
                },
                "headers": {
                    "fields": {
                        "F1": {
                            "hiddenValues": [],
                            "isVisible": True,
                            "showMissingValues": False
                        }
                    },
                    "columns": {},
                    "rows": {}
                },
                "fieldLabels": {
                    "columns": {},
                    "rows": {}
                },
                "marks": {
                    "fields": {},
                    "headers": {
                        "color": {"color": ""},
                        "isAutomaticSize": True,
                        "label": {
                            "canOverlapLabels": False,
                            "marksToLabel": {"type": "All"},
                            "showMarkLabels": False,
                        },
                        "range": {"reverse": True},
                        "size": {"isAutomatic": True, "type": "Pixel", "value": 13},
                    },
                    "panes": {
                        "range": {
                            "reverse": True
                        }
                    }
                },
                "shading": {
                    "backgroundColor": "#FFFFFF",
                    "banding": True
                },
                "referenceLines": {},
                "showDataPlaceholder": False,
                "title": {
                    "isVisible": True
                }
            }
        },
        "view": {
            "label": "default",
            "name": "Test_Bar_Chart_default",
            "viewSpecification": {
                "filter": {"filters": []},
                "sortOrders": {
                    "columns": [],
                    "fields": {},
                    "rows": []
                }
            }
        }
    }


@pytest.fixture
def sample_donut_payload(sample_viz_payload) -> Dict[str, Any]:
    """Valid donut chart visualization payload."""
    payload = sample_viz_payload.copy()
    payload["name"] = "Test_Donut_Chart"
    payload["label"] = "Test Donut Chart"
    payload["visualSpecification"]["marks"]["panes"]["type"] = "Donut"
    payload["visualSpecification"]["marks"]["panes"]["encodings"] = [
        {
            "type": "Color",
            "fieldKey": "F1"
        },
        {
            "type": "Angle",
            "fieldKey": "F2"
        }
    ]
    payload["visualSpecification"]["style"]["marks"]["panes"]["range"]["reverse"] = True
    return payload


@pytest.fixture
def sample_sdm_data() -> Dict[str, Any]:
    """Mock SDM detail response with fields."""
    return {
        "apiName": "Test_SDM",
        "label": "Test SDM",
        "semanticDataObjects": [
            {
                "apiName": "Opportunity",
                "label": "Opportunity",
                "fields": [
                    {
                        "apiName": "StageName",
                        "label": "Stage Name",
                        "type": "Text",
                        "dataType": "Text",
                        "role": "Dimension",
                        "displayCategory": "Discrete"
                    },
                    {
                        "apiName": "Amount",
                        "label": "Amount",
                        "type": "Number",
                        "dataType": "Number",
                        "role": "Measure",
                        "displayCategory": "Continuous"
                    },
                    {
                        "apiName": "CloseDate",
                        "label": "Close Date",
                        "type": "Date",
                        "dataType": "Date",
                        "role": "Dimension",
                        "displayCategory": "Discrete"
                    }
                ]
            }
        ],
        "calculatedMeasurements": [],
        "calculatedDimensions": [],
        "metrics": []
    }


@pytest.fixture
def sample_sdm_list() -> List[Dict[str, Any]]:
    """Mock SDM list response."""
    return [
        {
            "apiName": "Test_SDM",
            "label": "Test SDM"
        },
        {
            "apiName": "Sales_Model",
            "label": "Sales Model"
        }
    ]


@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file for testing."""
    def _create_file(data: Dict[str, Any], filename: str = "test.json") -> Path:
        file_path = tmp_path / filename
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return file_path
    return _create_file


@pytest.fixture
def invalid_viz_payload_missing_fields() -> Dict[str, Any]:
    """Invalid visualization payload missing required fields."""
    return {
        "name": "Invalid_Chart",
        "label": "Invalid Chart"
        # Missing dataSource, workspace, fields, visualSpecification, view
    }


@pytest.fixture
def invalid_viz_payload_wrong_structure() -> Dict[str, Any]:
    """Invalid visualization payload with wrong structure."""
    payload = sample_viz_payload()
    # Remove required marks.panes.stack
    del payload["visualSpecification"]["marks"]["panes"]["stack"]
    return payload


@pytest.fixture
def sample_filter_defs() -> List[Dict[str, Any]]:
    """Sample filter definitions for testing."""
    return [
        {
            "fieldName": "StageName",
            "objectName": "Opportunity",
            "label": "Stage Name"
        },
        {
            "fieldName": "Amount",
            "objectName": "Opportunity",
            "label": "Amount"
        }
    ]


@pytest.fixture
def sample_duplicate_filters() -> List[Dict[str, Any]]:
    """Sample filter definitions with duplicates."""
    return [
        {
            "fieldName": "StageName",
            "objectName": "Opportunity",
            "label": "Stage Name"
        },
        {
            "fieldName": "StageName",  # Duplicate
            "objectName": "Opportunity",
            "label": "Stage Name"
        },
        {
            "fieldName": "Amount",
            "objectName": "Opportunity",
            "label": "Amount"
        }
    ]
