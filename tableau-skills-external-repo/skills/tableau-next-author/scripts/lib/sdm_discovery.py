"""Semantic Data Model (SDM) discovery and field extraction.

Provides functions for discovering SDMs, listing available models,
and extracting field definitions from SDM responses.
"""

import sys
from typing import Any, Dict, List, Optional

from .sf_api import get_credentials, sdm_detail_endpoint, sdm_list_endpoint, sf_get


def _normalize_aggregation_type(value: Optional[str]) -> Optional[str]:
    """Normalize SDM aggregation values for visualization authoring.

    Some live SDMs return the literal string "None" for raw measures. Tableau
    visualization POST bodies reject that as a function, so treat it as unset and
    let the template layer infer a valid aggregation.
    """
    if value in (None, "", "None"):
        return None
    return value


def discover_sdm_fields(sdm_name: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """Discover all fields from an SDM.
    
    Retrieves SDM details from Salesforce API and builds a flattened
    dictionary mapping field names to field definitions.
    
    Args:
        sdm_name: SDM API name (e.g., "Sales_Cloud12_backward")
        
    Returns:
        Dict mapping field names to field definitions with keys:
        - fieldName: Field API name
        - objectName: Object API name (None for calculated fields)
        - role: "Dimension" or "Measure"
        - displayCategory: "Discrete" or "Continuous"
        - dataType: Field data type (e.g., "Text", "Number", "Date")
        - function: Aggregation function for measures (e.g., "Sum", "Avg")
        - label: Field display label
        - description: Field description
        Or None if SDM not found or API error
        
    Example:
        >>> fields = discover_sdm_fields("Sales_Model")
        >>> print(fields["Account_Industry"]["label"])
        "Account Industry"
    """
    token, instance = get_credentials()
    data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    
    if data is None:
        print(f"✗ Error: SDM '{sdm_name}' not found", file=sys.stderr)
        return None
    
    # Build flattened field dict
    fields: Dict[str, Dict[str, Any]] = {}
    
    # Add fields from semantic data objects
    for obj in data.get("semanticDataObjects", []):
        obj_name = obj.get("apiName", "")
        
        for d in obj.get("semanticDimensions", []):
            field_name = d.get("apiName", "")
            fields[field_name] = {
                "fieldName": field_name,
                "objectName": obj_name,
                "role": "Dimension",
                "displayCategory": "Discrete",
                "dataType": d.get("dataType", ""),
                "function": None,
                "label": d.get("label", ""),
                "description": d.get("description", ""),
            }
        
        for m in obj.get("semanticMeasurements", []):
            field_name = m.get("apiName", "")
            aggregation_type = _normalize_aggregation_type(m.get("aggregationType"))
            fields[field_name] = {
                "fieldName": field_name,
                "objectName": obj_name,
                "role": "Measure",
                "displayCategory": "Continuous",
                "aggregationType": aggregation_type,
                "function": aggregation_type,
                "label": m.get("label", ""),
                "description": m.get("description", ""),
            }
    
    # Add calculated dimensions
    for d in data.get("semanticCalculatedDimensions", []):
        field_name = d.get("apiName", "")
        fields[field_name] = {
            "fieldName": field_name,
            "objectName": None,
            "role": "Dimension",
            "displayCategory": "Discrete",
            "dataType": d.get("dataType", ""),
            "function": None,
            "label": d.get("label", ""),
            "description": d.get("description", ""),
        }
    
    # Add calculated measures
    for m in data.get("semanticCalculatedMeasurements", []):
        field_name = m.get("apiName", "")
        aggregation_type = _normalize_aggregation_type(m.get("aggregationType"))
        fields[field_name] = {
            "fieldName": field_name,
            "objectName": None,
            "role": "Measure",
            "displayCategory": "Continuous",
            "aggregationType": aggregation_type,
            "function": aggregation_type,
            "label": m.get("label", ""),
            "description": m.get("description", ""),
        }
    
    return fields


def list_sdms() -> List[Dict[str, Any]]:
    """List all available Semantic Data Models.
    
    Returns:
        List of SDM dicts with keys: apiName, label, dataspace
    """
    token, instance = get_credentials()
    data = sf_get(token, instance, sdm_list_endpoint())
    
    if data is None:
        return []
    
    models = data.get("semantic_models") or data.get("items") or []
    return models


def get_sdm_details(sdm_name: str) -> Optional[Dict[str, Any]]:
    """Get full SDM details including all fields and metadata.
    
    Args:
        sdm_name: SDM API name
        
    Returns:
        Full SDM response dict from API, or None if not found
    """
    token, instance = get_credentials()
    return sf_get(token, instance, sdm_detail_endpoint(sdm_name))
