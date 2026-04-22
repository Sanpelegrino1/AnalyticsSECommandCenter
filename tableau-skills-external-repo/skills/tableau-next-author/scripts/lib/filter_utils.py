"""Filter definition utilities for dashboard filters.

Provides functions for parsing filter arguments, enriching filters with labels,
and generating filter definitions from field names.
"""

import sys
from typing import Any, Dict, List, Optional

from .templates import FilterDef


def parse_filter_arg(tokens: List[str]) -> FilterDef:
    """Parse filter argument tokens into a FilterDef.
    
    Parses CLI-style filter arguments like:
    ``fieldName=X objectName=Y dataType=Z label=Label``
    
    Handles objectName=null or objectName=None for calculated fields.
    
    Args:
        tokens: List of key=value tokens (e.g., ["fieldName=Account_Industry", "objectName=Opportunity"])
        
    Returns:
        FilterDef dataclass instance
        
    Raises:
        SystemExit: If required fields (fieldName, objectName) are missing
    """
    props: Dict[str, str] = {}
    for tok in tokens:
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        props[k] = v

    if "fieldName" not in props:
        print("Error: --filter requires at least fieldName=...", file=sys.stderr)
        sys.exit(1)
    
    if "objectName" not in props:
        print("Error: --filter requires objectName=... (use objectName=null for calculated fields)", file=sys.stderr)
        sys.exit(1)

    # Handle null/None for calculated fields
    object_name_val = props["objectName"]
    if object_name_val.lower() in ("null", "none", ""):
        object_name_val = None
    else:
        object_name_val = object_name_val

    return FilterDef(
        field_name=props["fieldName"],
        object_name=object_name_val,
        data_type=props.get("dataType", "Text"),
        label=props.get("label", ""),
        selection_type=props.get("selectionType", "multiple"),
    )


def enrich_filters(
    filters: List[Dict[str, Any]],
    sdm_fields: Dict[str, Dict[str, Any]]
) -> None:
    """Enrich filters with objectName, dataType, and label from SDM field definitions.
    
    Updates filter definitions in-place, populating objectName, dataType, and label
    from SDM field definitions when available. For calculated fields (_clc), objectName
    will be None.
    
    Args:
        filters: List of filter definition dicts (modified in-place)
        sdm_fields: Dict of SDM field definitions (from discover_sdm_fields)
        
    Example:
        >>> filters = [{"fieldName": "Account_Industry"}]
        >>> sdm_fields = {"Account_Industry": {"label": "Account Industry", "objectName": "Opportunity", "dataType": "Text"}}
        >>> enrich_filters(filters, sdm_fields)
        >>> print(filters[0])
        {"fieldName": "Account_Industry", "objectName": "Opportunity", "dataType": "Text", "label": "Account Industry"}
    """
    for filter_def in filters:
        field_name = filter_def.get("fieldName")
        if not field_name:
            continue
        
        # Get field definition from SDM
        if field_name in sdm_fields:
            field_def = sdm_fields[field_name]
            
            # Populate objectName (can be None for calculated fields)
            if "objectName" not in filter_def:
                filter_def["objectName"] = field_def.get("objectName")
            
            # Populate dataType
            if "dataType" not in filter_def:
                filter_def["dataType"] = field_def.get("dataType", "Text")
            
            # Populate label if missing
            if "label" not in filter_def:
                field_label = field_def.get("label", "")
                
                if field_label:
                    filter_def["label"] = field_label
                else:
                    # Fallback: clean field name (strip technical suffixes, convert to title case)
                    cleaned_name = field_name
                    technical_suffixes = ["_Clc", "_clc", "_Mtc", "_mtc", "_MTC", "_CLC"]
                    for suffix in technical_suffixes:
                        if cleaned_name.endswith(suffix):
                            cleaned_name = cleaned_name[:-len(suffix)]
                            break
                    filter_def["label"] = cleaned_name.replace("_", " ").title()
        else:
            # Field not found in SDM - only set label as fallback
            # Leave objectName unset so validation can catch it
            if "label" not in filter_def:
                cleaned_name = field_name.replace("_", " ").title()
                filter_def["label"] = cleaned_name


def enrich_filter_labels(
    filters: List[Dict[str, Any]],
    sdm_fields: Dict[str, Dict[str, Any]]
) -> None:
    """Legacy alias for enrich_filters - kept for backward compatibility."""
    enrich_filters(filters, sdm_fields)


def validate_filters(
    filters: List[Dict[str, Any]],
    sdm_fields: Dict[str, Dict[str, Any]],
    sdm_name: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Validate that all filters have required fields populated.
    
    Checks that every filter has objectName defined (either a string or explicit None).
    Returns error message if validation fails, listing unresolved filters and suggestions.
    
    Args:
        filters: List of filter definition dicts
        sdm_fields: Dict of SDM field definitions (for suggestions)
        sdm_name: Optional SDM API name for concrete error message commands

    Returns:
        (is_valid, error_message) tuple where error_message is None if valid
        
    Example:
        >>> filters = [{"fieldName": "Unknown_Field"}]
        >>> sdm_fields = {"Account_Industry": {...}}
        >>> is_valid, error = validate_filters(filters, sdm_fields)
        >>> print(error)
        "✗ Error: 1 filter(s) have unresolved field names: ..."
    """
    unresolved = []
    for filter_def in filters:
        field_name = filter_def.get("fieldName")
        if not field_name:
            continue
        
        # Check if objectName is missing (not set at all)
        if "objectName" not in filter_def:
            unresolved.append(field_name)
    
    if not unresolved:
        return True, None
    
    # Build error message with suggestions
    discover_cmd = (
        f"python scripts/discover_sdm.py --sdm {sdm_name}"
        if sdm_name
        else "python scripts/discover_sdm.py --sdm <SDM_NAME>"
    )
    error_lines = [
        f"✗ Error: {len(unresolved)} filter(s) have unresolved field names:",
        "",
        "  Why this matters: Filters must use exact field names from the SDM.",
        "  Incorrect names cause dashboard creation to fail.",
        "",
    ]
    for field_name in unresolved:
        error_lines.append(f"  - {field_name}")
    error_lines.extend([
        "",
        "  Discover correct field names:",
        f"     {discover_cmd}",
        "",
        "  Available dimension fields (first 15):",
    ])
    
    # Get dimension fields as suggestions
    dimension_fields = [
        (name, defn.get("objectName"), defn.get("label", name))
        for name, defn in sdm_fields.items()
        if defn.get("role") == "Dimension"
    ][:15]
    
    if dimension_fields:
        error_lines.append("  fieldName | objectName | label")
        error_lines.append("  " + "-" * 60)
        for name, obj_name, label in dimension_fields:
            obj_display = obj_name if obj_name else "null"
            error_lines.append(f"  {name:<30} | {obj_display:<25} | {label}")
    else:
        error_lines.append("  (No dimension fields found)")
    
    return False, "\n".join(error_lines)


def generate_filters_from_fields(
    field_names: List[str],
    sdm_fields: Dict[str, Dict[str, Any]],
    num_filters: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Generate filter definitions from field names using SDM field metadata.
    
    Ensures correct objectName is looked up from sdm_fields instead of guessing.
    Populates label from SDM field label for business-friendly display.
    Only creates filters for dimension fields (not measures).
    
    Args:
        field_names: List of field names to create filters for
        sdm_fields: Dict of SDM field definitions (from discover_sdm_fields)
        num_filters: Optional number of filters to generate (defaults to len(field_names))
        
    Returns:
        List of filter definition dicts with fieldName, objectName, dataType, label
        
    Example:
        >>> field_names = ["Account_Industry", "Opportunity_Stage"]
        >>> sdm_fields = discover_sdm_fields("Sales_Model")
        >>> filters = generate_filters_from_fields(field_names, sdm_fields)
        >>> print(filters[0]["label"])
        "Account Industry"
    """
    filters = []
    for field_name in field_names[:num_filters] if num_filters else field_names:
        if field_name not in sdm_fields:
            print(f"⚠ Warning: Field '{field_name}' not found in SDM, skipping filter", file=sys.stderr)
            continue
        
        field_def = sdm_fields[field_name]
        # Calculated fields have objectName=None
        object_name = field_def.get("objectName")
        data_type = field_def.get("dataType", "Text")
        
        # Only create filters for dimensions (not measures)
        if field_def.get("role") != "Dimension":
            print(f"⚠ Warning: Field '{field_name}' is a measure, skipping filter (filters should be dimensions)", file=sys.stderr)
            continue
        
        # Get label from SDM field definition, fallback to cleaned field name
        field_label = field_def.get("label", "")
        if not field_label:
            # Fallback: clean field name (strip technical suffixes, convert to title case)
            cleaned_name = field_name
            technical_suffixes = ["_Clc", "_clc", "_Mtc", "_mtc", "_MTC", "_CLC"]
            for suffix in technical_suffixes:
                if cleaned_name.endswith(suffix):
                    cleaned_name = cleaned_name[:-len(suffix)]
                    break
            field_label = cleaned_name.replace("_", " ").title()
        
        filters.append({
            "fieldName": field_name,
            "objectName": object_name,  # Correct object name from SDM
            "dataType": data_type,
            "label": field_label,  # Business-friendly label from SDM
        })
    
    return filters
