"""Reusable dashboard creation workflow functions.

Provides functions for:
- SDM field discovery
- Workspace management
- Metric discovery
- Visualization creation from specs
- Dashboard pattern selection
- Dashboard creation
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .sf_api import (
    get_credentials,
    sf_get,
    sf_post,
    sdm_detail_endpoint,
    dashboard_endpoint,
    workspace_endpoint,
)
from .sdm_discovery import discover_sdm_fields
from .viz_templates import get_template, _normalize_fields_for_template


def ensure_workspace(workspace_name: str, workspace_label: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Ensure workspace exists, create if needed.
    
    Args:
        workspace_name: Workspace API name
        workspace_label: Optional workspace display label
        
    Returns:
        Tuple of (success, actual_workspace_name)
    """
    token, instance = get_credentials()
    existing = sf_get(token, instance, workspace_endpoint(workspace_name))
    
    if existing and isinstance(existing, dict) and existing.get("name") == workspace_name:
        print(f"✓ Workspace '{workspace_name}' already exists")
        return True, workspace_name
    
    payload = {"name": workspace_name, "label": workspace_label or workspace_name}
    resp, err = sf_post(token, instance, workspace_endpoint(), payload)
    
    if err:
        if "DUPLICATE" in err.upper() or "already" in err.lower():
            print(f"✓ Workspace '{workspace_name}' already exists")
            return True, workspace_name
        print(f"✗ Error creating workspace: {err}", file=sys.stderr)
        return False, None
    
    actual_name = resp.get("name", workspace_name)
    print(f"✓ Created workspace '{workspace_name}'")
    if actual_name != workspace_name:
        print(f"  → Actual API name: {actual_name}")
    return True, actual_name


def discover_metrics(sdm_name: str) -> List[str]:
    """Discover all metrics from an SDM.
    
    Args:
        sdm_name: SDM API name
        
    Returns:
        List of metric API names
    """
    token, instance = get_credentials()
    data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    
    if data is None:
        return []
    
    metrics = []
    for m in data.get("semanticMetrics", []):
        metric_name = m.get("apiName")
        if metric_name:
            metrics.append(metric_name)
    
    return metrics


def create_visualization_from_spec(
    viz_spec: Dict[str, Any],
    sdm_name: str,
    workspace_name: str,
) -> Optional[str]:
    """Create a visualization from a specification.
    
    Args:
        viz_spec: Visualization specification dict with:
            - template: Template name
            - name: Visualization API name
            - label: Visualization display label
            - fields: Dict mapping template field names to SDM field names
        sdm_name: SDM API name
        workspace_name: Workspace API name
        
    Returns:
        Actual visualization API name if created successfully, None otherwise
    """
    _normalize_fields_for_template(viz_spec)
    script_path = Path(__file__).parent.parent / "apply_viz_template.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        "--template", viz_spec["template"],
        "--sdm", sdm_name,
        "--workspace", workspace_name,
        "--name", viz_spec["name"],
        "--label", viz_spec["label"],
        "--post",
    ]
    
    # Add field overrides from spec
    fields = viz_spec.get("fields", {})
    color_dim = viz_spec.get("color_dim")  # Handle color_dim separately
    
    # Auto-detect color_dim if template supports it and not already specified
    if not color_dim:
        template = get_template(viz_spec["template"])
        if template and template.get("optional_fields", {}).get("color_dim"):
            # Template supports color_dim, check if we have 2+ dimensions available
            sdm_fields = discover_sdm_fields(sdm_name)
            if sdm_fields:
                # Find dimensions already used in the spec
                used_dimensions = set()
                for param, field_name in fields.items():
                    if field_name in sdm_fields:
                        field_def = sdm_fields[field_name]
                        if field_def.get("role") == "Dimension":
                            used_dimensions.add(field_name)
                
                # Find available dimensions (Text/Picklist) that aren't already used
                available_dimensions = [
                    field_name for field_name, field_def in sdm_fields.items()
                    if field_def.get("role") == "Dimension"
                    and field_def.get("dataType") in ["Text", "Picklist"]
                    and field_name not in used_dimensions
                ]
                
                # Auto-add first available dimension as color_dim
                if available_dimensions:
                    color_dim = available_dimensions[0]
                    print(f"  → Auto-added color_dim: {color_dim}", file=sys.stderr)
    
    for param, field_name in fields.items():
        if param == "category":
            cmd.extend(["--category", field_name])
        elif param == "amount":
            cmd.extend(["--amount", field_name])
        elif param == "date":
            cmd.extend(["--date", field_name])
        elif param == "measure":
            cmd.extend(["--measure", field_name])
        elif param == "measure_1":
            cmd.extend(["--measure", field_name])  # Use --measure for first measure
        elif param == "measure_2":
            # For bar_multi_measure, pass as second --measure argument
            # The script will need to handle multiple --measure args
            cmd.extend(["--measure", field_name])  # Pass second measure
        elif param == "stage":
            cmd.extend(["--stage", field_name])
        elif param == "count":
            cmd.extend(["--count", field_name])
        elif param == "x_measure":
            cmd.extend(["--x-measure", field_name])
        elif param == "y_measure":
            cmd.extend(["--y-measure", field_name])
        elif param == "size_measure":
            cmd.extend(["--size-measure", field_name])
        elif param == "label_measure":
            cmd.extend(["--label-measure", field_name])
        elif param == "row_dim":
            cmd.extend(["--row-dim", field_name])
        elif param == "col_dim":
            cmd.extend(["--col-dim", field_name])
        elif param == "x_dimension":
            cmd.extend(["--col-dim", field_name])
        elif param == "y_dimension":
            cmd.extend(["--row-dim", field_name])
        elif param == "id_field":
            cmd.extend(["--id-field", field_name])
        elif param == "label_field":
            cmd.extend(["--label-field", field_name])
        elif param == "color_dim":
            cmd.extend(["--color-dim", field_name])
        elif param == "stack_dim":
            cmd.extend(["--stack-dim", field_name])
        elif param == "latitude":
            cmd.extend(["--latitude", field_name])
        elif param == "longitude":
            cmd.extend(["--longitude", field_name])
        elif param == "label_dim":
            cmd.extend(["--label-dim", field_name])
        elif param == "level1":
            cmd.extend(["--level1", field_name])
        elif param == "level2":
            cmd.extend(["--level2", field_name])
        elif param == "link_measure":
            cmd.extend(["--link-measure", field_name])
        elif param == "link_color_measure":
            cmd.extend(["--link-color-measure", field_name])
        elif param == "level2_color_dim":
            cmd.extend(["--level2-color-dim", field_name])
        elif param == "level3":
            cmd.extend(["--level3", field_name])
        elif param == "detail_dim":
            cmd.extend(["--color-dim", field_name])  # Detail encoding often uses color-dim parameter
        elif param == "category2":
            # For table template with multiple categories
            pass  # Tables handle multiple categories differently
    
    # Add color_dim if specified at top level
    if color_dim:
        cmd.extend(["--color-dim", color_dim])

    # Pass style / palette / arbitrary overrides to apply_viz_template
    override_payload: Dict[str, Any] = {}
    if viz_spec.get("palette"):
        override_payload["palette"] = viz_spec["palette"]
    if viz_spec.get("style"):
        override_payload.update(viz_spec["style"])
    if viz_spec.get("overrides"):
        override_payload.update(viz_spec["overrides"])

    tmp_path = None
    if override_payload:
        fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="tableau_overrides_")
        try:
            os.write(fd, json.dumps(override_payload).encode())
        finally:
            os.close(fd)
        cmd.extend(["--overrides", tmp_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if result.returncode != 0:
        print(f"✗ Failed to create visualization '{viz_spec['name']}':", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return None

    # Parse actual API name from subprocess output
    actual_name = viz_spec["name"]  # Default to requested name
    for line in result.stderr.split("\n"):
        if line.startswith("ACTUAL_NAME:"):
            actual_name = line.split(":", 1)[1].strip()
            break

    # Check for success indicators
    if "✓ Created visualization" in result.stderr or "Created visualization" in result.stdout:
        print(f"✓ Created visualization '{viz_spec['name']}'")
        if actual_name != viz_spec["name"]:
            print(f"  → Actual API name: {actual_name}")
        return actual_name

    # Check for errors
    if "Error" in result.stderr or "error" in result.stderr.lower():
        print(f"✗ Error creating visualization '{viz_spec['name']}':", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return None

    print(f"✓ Created visualization '{viz_spec['name']}'")
    if actual_name != viz_spec["name"]:
        print(f"  → Actual API name: {actual_name}")
    return actual_name


def create_dashboard_from_pattern(
    pattern: str,
    name: str,
    label: str,
    workspace_name: str,
    sdm_name: str,
    viz_names: List[str],
    metric_names: List[str],
    filters: Optional[List[Dict[str, Any]]] = None,
    pattern_args: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Create dashboard using pattern.
    
    Args:
        pattern: Dashboard pattern name
        name: Dashboard API name
        label: Dashboard display label
        workspace_name: Workspace API name
        sdm_name: SDM API name
        viz_names: List of visualization API names
        metric_names: List of metric API names
        filters: Optional list of filter definitions
        pattern_args: Optional pattern-specific arguments
        
    Returns:
        Tuple of (success, dashboard_id, actual_dashboard_name)
    """
    script_path = Path(__file__).parent.parent / "generate_dashboard_pattern.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        "--pattern", pattern,
        "--name", name,
        "--label", label,
        "--workspace-name", workspace_name,
        "--sdm-name", sdm_name,
    ]
    
    # Add pattern-specific arguments
    if pattern_args:
        if "title_text" in pattern_args:
            cmd.extend(["--title-text", pattern_args["title_text"]])
        if "primary_metric" in pattern_args:
            cmd.extend(["--primary-metric", pattern_args["primary_metric"]])
        if "secondary_metrics" in pattern_args:
            for m in pattern_args["secondary_metrics"]:
                cmd.extend(["--secondary-metrics", m])
        if "pages" in pattern_args:
            for p in pattern_args["pages"]:
                cmd.extend(["--page", p])
    
    for viz_name in viz_names:
        cmd.extend(["--viz", viz_name])
    
    for metric_name in metric_names:
        cmd.extend(["--metrics", metric_name])
    
    if filters:
        for f in filters:
            field_name = f.get("fieldName")
            if not field_name:
                continue
            
            # Validate objectName exists (should be caught earlier, but double-check)
            object_name = f.get("objectName")
            if object_name is None:
                # None means calculated field - pass as string "null" for CLI parser
                object_name_str = "null"
            elif object_name == "":
                # Empty string also means calculated field
                object_name_str = "null"
            elif "objectName" not in f:
                # Missing entirely - this should have been caught by validation
                print(f"✗ Error: Filter '{field_name}' missing objectName", file=sys.stderr)
                return False, None, None
            else:
                object_name_str = str(object_name)
            
            filter_parts = [
                f"fieldName={field_name}",
                f"objectName={object_name_str}",
                f"dataType={f.get('dataType', 'Text')}"
            ]
            if f.get("label"):
                filter_parts.append(f"label={f['label']}")
            cmd.extend(["--filter"] + filter_parts)
    
    # Generate JSON first
    output_file = Path(tempfile.gettempdir()) / f"{name}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd.extend(["-o", str(output_file)])
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    
    if result.returncode != 0:
        error_msg = f"Failed to generate dashboard JSON: {result.stderr}"
        print(f"✗ {error_msg}", file=sys.stderr)
        return False, None, None
    
    if not output_file.exists():
        error_msg = "Dashboard JSON file not created"
        print(f"✗ {error_msg}", file=sys.stderr)
        return False, None, None
    
    # POST dashboard
    token, instance = get_credentials()
    with open(output_file) as f:
        dashboard_json = json.load(f)
    
    response, error = sf_post(token, instance, dashboard_endpoint(), dashboard_json)
    
    if error:
        print(f"✗ Error posting dashboard: {error}", file=sys.stderr)
        return False, None, None
    
    dashboard_id = response.get("id", "")
    dashboard_url = response.get("url", "")
    actual_name = response.get("name", name)
    
    print(f"✓ Created dashboard '{name}' ({dashboard_id})")
    if actual_name != name:
        print(f"  → Actual API name: {actual_name}")
    if dashboard_url:
        print(f"✓ Dashboard URL: {dashboard_url}")
    
    return True, dashboard_id, actual_name
