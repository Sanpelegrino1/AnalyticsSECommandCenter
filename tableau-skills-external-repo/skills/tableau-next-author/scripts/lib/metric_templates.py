"""Template library and payload builders for semantic metrics.

Provides common formula templates and functions to build semantic metric
payloads for Salesforce Tableau Next API.

Semantic metrics are simpler than calculated measurements - they only require
apiName, label, and expression (no aggregationType, dataType, decimalPlace, etc.).
"""

from typing import Dict, List, Optional, Tuple


# -- Template Functions ---------------------------------------------------------

def sum_metric(field: str) -> str:
    """Generate sum aggregation formula.

    Args:
        field: Field name to sum

    Returns:
        Tableau formula string
    """
    return f"SUM([{field}])"


def avg_metric(field: str) -> str:
    """Generate average aggregation formula.

    Args:
        field: Field name to average

    Returns:
        Tableau formula string
    """
    return f"AVG([{field}])"


def count_metric(field: str) -> str:
    """Generate count aggregation formula.

    Args:
        field: Field name to count

    Returns:
        Tableau formula string
    """
    return f"COUNT([{field}])"


def win_rate_metric(won_field: str, total_field: str) -> str:
    """Generate win rate formula.

    Args:
        won_field: Field name for won count
        total_field: Field name for total count

    Returns:
        Tableau formula string
    """
    return f"SUM([{won_field}]) / SUM([{total_field}])"


def conversion_rate_metric(converted_field: str, total_field: str) -> str:
    """Generate conversion rate formula.

    Args:
        converted_field: Field name for converted count
        total_field: Field name for total count

    Returns:
        Tableau formula string
    """
    return f"SUM([{converted_field}]) / SUM([{total_field}])"


def weighted_pipeline_metric(amount_field: str, probability_field: str) -> str:
    """Generate weighted pipeline value formula.

    Args:
        amount_field: Field name for amount
        probability_field: Field name for probability (0-1)

    Returns:
        Tableau formula string
    """
    return f"SUM([{amount_field}] * [{probability_field}])"


def sales_cycle_metric(start_field: str, end_field: str) -> str:
    """Generate sales cycle (days between) formula.

    Args:
        start_field: Start date field name
        end_field: End date field name

    Returns:
        Tableau formula string
    """
    return f"AVG(DATEDIFF('day', [{start_field}], [{end_field}]))"


# -- Payload Builder -----------------------------------------------------------

def build_default_insights_settings(
    additional_dimensions: Optional[List[Dict]] = None,
    sentiment: str = "SentimentTypeUpIsGood"
) -> Dict[str, any]:
    """Build default insightsSettings structure based on collection patterns.
    
    Args:
        additional_dimensions: List of dimension references (optional)
        sentiment: Sentiment value (default: "SentimentTypeUpIsGood")
    
    Returns:
        Complete insightsSettings dict
    """
    insights_dimensions_refs = []
    if additional_dimensions:
        # Match insightsDimensionsReferences to additionalDimensions
        for dim in additional_dimensions:
            if "tableFieldReference" in dim:
                insights_dimensions_refs.append({
                    "tableFieldReference": dim["tableFieldReference"]
                })
    
    return {
        "insightTypes": [
            {"enabled": False, "type": "TopContributors"},
            {"enabled": False, "type": "ComparisonToExpectedRangeAlert"},
            {"enabled": True, "type": "TrendChangeAlert"},
            {"enabled": True, "type": "BottomContributors"},
            {"enabled": True, "type": "ConcentratedContributionAlert"},
            {"enabled": True, "type": "TopDrivers"},
            {"enabled": True, "type": "TopDetractors"},
            {"enabled": True, "type": "CurrentTrend"},
            {"enabled": False, "type": "OutlierDetection"},
            {"enabled": False, "type": "RecordLevelTable"}
        ],
        "insightsDimensionsReferences": insights_dimensions_refs,
        "pluralNoun": "",
        "sentiment": sentiment,
        "singularNoun": ""
    }


def build_semantic_metric(
    api_name: str,
    label: str,
    calculated_field_api_name: str,
    time_dimension_field_name: str,
    time_dimension_table_name: str,
    description: str = "",
    aggregation_type: str = "UserAgg",
    filters: Optional[List[Dict]] = None,
    is_cumulative: bool = False,
    is_goal_editing_blocked: bool = False,
    time_grains: Optional[List[str]] = None,
    additional_dimensions: Optional[List[Dict]] = None,
    insights_settings: Optional[Dict[str, any]] = None,
    sentiment: str = "SentimentTypeUpIsGood",
) -> Dict[str, any]:
    """Build semantic metric payload.

    Semantic metrics reference calculated fields via measurementReference.
    Based on production examples (HR_Workforce1_package, Sales_Cloud12_package), metrics use:
    - measurementReference.calculatedFieldApiName (not expression)
    - aggregationType: "UserAgg"
    - timeDimensionReference (required)
    - timeGrains (required)
    - additionalDimensions (optional, for breakdown analysis)
    - insightsSettings (optional, auto-generated from additionalDimensions if not provided)
    - filters, isCumulative, isGoalEditingBlocked

    Args:
        api_name: API name (must end with _mtc)
        label: Display label
        calculated_field_api_name: API name of calculated field to reference
        time_dimension_field_name: Time dimension field API name (e.g., "Close_Date")
        time_dimension_table_name: Time dimension table API name (e.g., "Opportunity_TAB_Sales_Cloud")
        description: Optional field description
        aggregation_type: Aggregation type (default: "UserAgg")
        filters: Optional list of filter dictionaries
        is_cumulative: Whether metric is cumulative (default: False)
        is_goal_editing_blocked: Whether goal editing is blocked (default: False)
        time_grains: List of time grains (default: ["Day", "Week", "Month", "Quarter", "Year"])
        additional_dimensions: Optional list of dimension references for breakdown analysis
        insights_settings: Optional insightsSettings dict (auto-generated if not provided)
        sentiment: Sentiment value (default: "SentimentTypeUpIsGood")

    Returns:
        Complete semantic metric payload dict
    """
    if time_grains is None:
        time_grains = ["Day", "Week", "Month", "Quarter", "Year"]
    
    payload: Dict[str, any] = {
        "apiName": api_name,
        "label": label,
        "aggregationType": aggregation_type,
        "measurementReference": {
            "calculatedFieldApiName": calculated_field_api_name
        },
        "timeDimensionReference": {
            "tableFieldReference": {
                "fieldApiName": time_dimension_field_name,
                "tableApiName": time_dimension_table_name
            }
        },
        "timeGrains": time_grains,
        "filters": filters or [],
        "isCumulative": is_cumulative,
        "isGoalEditingBlocked": is_goal_editing_blocked,
    }
    
    # Add additionalDimensions if provided
    if additional_dimensions:
        payload["additionalDimensions"] = additional_dimensions
    
    # Add insightsSettings (auto-generate if not provided and additionalDimensions exist, or if sentiment is explicitly set)
    if insights_settings:
        payload["insightsSettings"] = insights_settings
    elif additional_dimensions or sentiment != "SentimentTypeUpIsGood":
        # Auto-generate insightsSettings from additionalDimensions (or empty if none)
        # Also generate if sentiment is explicitly set to non-default value
        payload["insightsSettings"] = build_default_insights_settings(
            additional_dimensions=additional_dimensions,
            sentiment=sentiment
        )
    
    # Only include description if provided
    if description:
        payload["description"] = description
    return payload


# -- Validation ----------------------------------------------------------------

def validate_metric(
    api_name: str,
    expression: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """Validate semantic metric structure and optionally expression syntax.

    Args:
        api_name: API name to validate
        expression: Optional expression to validate function names

    Returns:
        (is_valid, list_of_errors)
    """
    errors: List[str] = []

    # Check API name format
    if not api_name.endswith("_mtc"):
        errors.append("API name must end with '_mtc'")

    # Check for double underscores (Salesforce API restriction)
    if "__" in api_name:
        errors.append("API name cannot contain double underscores (__)")

    # Validate expression functions if provided
    if expression:
        try:
            from .tableau_functions import validate_functions
            is_valid_funcs, invalid_funcs, suggestions = validate_functions(expression)
            if not is_valid_funcs:
                for invalid in invalid_funcs:
                    error_msg = f"Invalid function '{invalid}' in expression"
                    # Add suggestions if available
                    suggestion = next((s for s in suggestions if invalid in s), None)
                    if suggestion:
                        error_msg += f". Did you mean: {suggestion.split(' -> ')[1]}"
                    errors.append(error_msg)
        except ImportError:
            # tableau_functions module not available, skip function validation
            pass

    return len(errors) == 0, errors


# -- Template Registry ---------------------------------------------------------

METRIC_TEMPLATE_REGISTRY = {
    "sum": sum_metric,
    "avg": avg_metric,
    "count": count_metric,
    "win_rate": win_rate_metric,
    "conversion_rate": conversion_rate_metric,
    "weighted_pipeline": weighted_pipeline_metric,
    "sales_cycle": sales_cycle_metric,
}
