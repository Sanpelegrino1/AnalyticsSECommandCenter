#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from itertools import cycle
from pathlib import Path
from types import SimpleNamespace

import requests


ROOT = Path(__file__).resolve().parents[2]
TOOLKIT_ROOT = ROOT / "tableau-skills-external-repo" / "skills" / "tableau-next-author" / "scripts"
if str(TOOLKIT_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLKIT_ROOT))

from generate_viz import build_viz  # noqa: E402
from lib.calc_field_templates import build_calculated_measurement  # noqa: E402
from lib.dashboard_template_loader import load_dashboard_template  # noqa: E402
from lib.metric_templates import build_semantic_metric  # noqa: E402
from lib.sf_api import (  # noqa: E402
    calculated_field_endpoint,
    dashboard_endpoint,
    get_credentials,
    sf_delete,
    sf_post,
    visualization_endpoint,
)
from lib.templates import validate_full_visualization  # noqa: E402


TARGET_ORG = "STORM_TABLEAU_NEXT"
WORKSPACE_NAME = "Hubbell"
WORKSPACE_ID = "1DyKZ000000kAhw0AE"
MODEL_ID = "2SMKZ000000kAhv4AE"
MODEL_API_NAME = "New_Semantic_Model_0ce1"
MODEL_LABEL = "Hubbell Historical Opportunity Performance"
OBJECT_NAME = "Final_Hist_Sales"

DATE_FIELD = "Close_Date3"
STAGE_FIELD = "Stage_Name"
PRODUCT_FIELD = "Product_Family1"
INDUSTRY_FIELD = "Industry6"
BILLING_STATE_FIELD = "Billing_State"
OPPORTUNITY_TYPE_FIELD = "Opportunity_Type2"
IS_CLOSED_FIELD = "Is_Closed1"
IS_WON_FIELD = "Is_Won1"
AMOUNT_FIELD = "Amount"
EXPECTED_REVENUE_FIELD = "Expected_Revenue1"
CLOSED_WON_AMOUNT_FIELD = "Closed_Won_Amount"
ANNUAL_REVENUE_FIELD = "Annual_Revenue"


def resolve_credentials(target_org: str) -> tuple[str, str]:
    if os.environ.get("SF_TOKEN") and os.environ.get("SF_INSTANCE"):
        return get_credentials()

    sf_executable = shutil.which("sf") or shutil.which("sf.cmd") or shutil.which("sf.exe")
    command = [sf_executable, "org", "display", "--target-org", target_org, "--json"] if sf_executable else [
        "powershell",
        "-NoProfile",
        "-Command",
        f"sf org display --target-org '{target_org}' --json",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "sf org display failed")

    payload = json.loads(result.stdout)
    org = payload.get("result") or {}
    token = org.get("accessToken")
    instance = org.get("instanceUrl")
    if not token or not instance:
        raise RuntimeError("sf org display did not return accessToken and instanceUrl")

    os.environ["SF_TOKEN"] = token
    os.environ["SF_INSTANCE"] = instance
    return token, instance.rstrip("/")


def api_get_optional(access_token: str, instance_url: str, path: str) -> dict | None:
    response = requests.get(
        f"{instance_url}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=120,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    if not response.text:
        return None
    return response.json()


def ensure_semantic_resource(access_token: str, instance_url: str, resource_type: str, api_name: str, payload: dict) -> tuple[dict, bool]:
    existing = api_get_optional(
        access_token,
        instance_url,
        calculated_field_endpoint(MODEL_API_NAME, resource_type, api_name),
    )
    if existing:
        return existing, False

    created, error = sf_post(
        access_token,
        instance_url,
        calculated_field_endpoint(MODEL_API_NAME, resource_type),
        payload,
    )
    if error:
        raise RuntimeError(error)
    return created or {"apiName": api_name}, True


def ensure_visualization(access_token: str, instance_url: str, payload: dict) -> tuple[dict, bool]:
    name = payload["name"]
    existing = api_get_optional(access_token, instance_url, visualization_endpoint(name))
    if existing:
        return existing, False

    created, error = sf_post(access_token, instance_url, visualization_endpoint(), payload)
    if error:
        raise RuntimeError(error)
    return created or {"name": name}, True


def ensure_dashboard(access_token: str, instance_url: str, payload: dict, replace: bool) -> tuple[dict, bool]:
    name = payload["name"]
    existing = api_get_optional(access_token, instance_url, dashboard_endpoint(name))
    if existing and not replace:
        return existing, False
    if existing and replace:
        deleted, error = sf_delete(access_token, instance_url, dashboard_endpoint(name))
        if not deleted:
            raise RuntimeError(error or f"Failed to delete existing dashboard {name}")

    created, error = sf_post(access_token, instance_url, dashboard_endpoint(), payload)
    if error:
        raise RuntimeError(error)
    return created or {"name": name}, True


def make_viz_payload(*, chart_type: str, name: str, label: str, columns: list[str], rows: list[str], fields: list[list[str]]) -> dict:
    payload = build_viz(
        SimpleNamespace(
            chart_type=chart_type,
            name=name,
            label=label,
            sdm_name=MODEL_API_NAME,
            sdm_label=MODEL_LABEL,
            workspace_name=WORKSPACE_NAME,
            workspace_label=WORKSPACE_NAME,
            columns=columns,
            rows=rows,
            field=fields,
            encoding=None,
            legend=None,
            sort=None,
            style=None,
            measure_values=None,
        )
    )
    is_valid, errors = validate_full_visualization(payload)
    if not is_valid:
        raise RuntimeError(f"Visualization payload {name} is invalid: {'; '.join(errors)}")
    return payload


def strip_readonly_fields(dashboard: dict) -> dict:
    readonly_fields = {
        "id",
        "url",
        "createdBy",
        "createdDate",
        "lastModifiedBy",
        "lastModifiedDate",
        "permissions",
        "customViews",
        "templateSource",
    }
    dashboard = json.loads(json.dumps(dashboard))
    for field in readonly_fields:
        dashboard.pop(field, None)

    for widget in dashboard.get("widgets", {}).values():
        if not isinstance(widget, dict):
            continue
        widget.pop("id", None)
        widget.pop("status", None)

    for layout in dashboard.get("layouts", []):
        layout.pop("id", None)
        for page in layout.get("pages", []):
            page.pop("id", None)
            if not page.get("name"):
                page["name"] = str(uuid.uuid4())
            for page_widget in page.get("widgets", []):
                if isinstance(page_widget, dict):
                    page_widget.pop("id", None)

    return dashboard


def assign_widget_sources(dashboard: dict, metric_names: list[str], visualization_names: list[str], filter_defs: list[dict]) -> dict:
    dashboard = strip_readonly_fields(dashboard)
    dashboard["workspaceIdOrApiName"] = WORKSPACE_NAME

    metric_iter = cycle(metric_names)
    viz_iter = cycle(visualization_names)
    filter_iter = cycle(filter_defs)

    widgets = dashboard.get("widgets", {})
    for widget_name in sorted(widgets.keys()):
        widget = widgets[widget_name]
        if not isinstance(widget, dict):
            continue
        widget_type = widget.get("type")
        if widget_type == "metric":
            metric_name = next(metric_iter)
            widget.setdefault("parameters", {}).setdefault("metricOption", {})["sdmApiName"] = MODEL_API_NAME
            widget["parameters"]["metricOption"]["sdmId"] = MODEL_ID
            widget["source"] = {"name": metric_name}
        elif widget_type == "visualization":
            widget["source"] = {"name": next(viz_iter)}
        elif widget_type == "filter":
            filter_def = next(filter_iter)
            widget.setdefault("parameters", {}).setdefault("filterOption", {})["fieldName"] = filter_def["fieldName"]
            widget["parameters"]["filterOption"]["objectName"] = filter_def["objectName"]
            widget["parameters"]["filterOption"]["dataType"] = filter_def["dataType"]
            widget["parameters"]["filterOption"]["selectionType"] = filter_def.get("selectionType", "multiple")
            widget["label"] = filter_def.get("label", widget.get("label", "Filter"))
            widget["source"] = {"name": MODEL_API_NAME}

    return dashboard


def build_calc_fields() -> dict[str, dict]:
    return {
        "Hist_Amount_clc": build_calculated_measurement(
            api_name="Hist_Amount_clc",
            label="Historical Amount",
            expression=f"[{OBJECT_NAME}].[{AMOUNT_FIELD}]",
            aggregation_type="Sum",
            data_type="Number",
        ),
        "Hist_Expected_Revenue_clc": build_calculated_measurement(
            api_name="Hist_Expected_Revenue_clc",
            label="Expected Revenue",
            expression=f"[{OBJECT_NAME}].[{EXPECTED_REVENUE_FIELD}]",
            aggregation_type="Sum",
            data_type="Number",
        ),
        "Hist_Closed_Won_Amount_clc": build_calculated_measurement(
            api_name="Hist_Closed_Won_Amount_clc",
            label="Closed Won Amount",
            expression=f"[{OBJECT_NAME}].[{CLOSED_WON_AMOUNT_FIELD}]",
            aggregation_type="Sum",
            data_type="Number",
        ),
        "Hist_Open_Pipeline_clc": build_calculated_measurement(
            api_name="Hist_Open_Pipeline_clc",
            label="Open Pipeline",
            expression=f"IF NOT [{OBJECT_NAME}].[{IS_CLOSED_FIELD}] THEN [{OBJECT_NAME}].[{AMOUNT_FIELD}] ELSE 0 END",
            aggregation_type="Sum",
            data_type="Number",
        ),
        "Hist_Revenue_Gap_clc": build_calculated_measurement(
            api_name="Hist_Revenue_Gap_clc",
            label="Revenue Gap",
            expression=f"[{OBJECT_NAME}].[{EXPECTED_REVENUE_FIELD}] - [{OBJECT_NAME}].[{CLOSED_WON_AMOUNT_FIELD}]",
            aggregation_type="Sum",
            data_type="Number",
        ),
        "Hist_Closed_Won_Count_clc": build_calculated_measurement(
            api_name="Hist_Closed_Won_Count_clc",
            label="Closed Won Count",
            expression=f"IF [{OBJECT_NAME}].[{IS_WON_FIELD}] THEN 1 ELSE 0 END",
            aggregation_type="Sum",
            data_type="Number",
        ),
        "Hist_Open_Opportunity_Count_clc": build_calculated_measurement(
            api_name="Hist_Open_Opportunity_Count_clc",
            label="Open Opportunity Count",
            expression=f"IF NOT [{OBJECT_NAME}].[{IS_CLOSED_FIELD}] THEN 1 ELSE 0 END",
            aggregation_type="Sum",
            data_type="Number",
        ),
        "Hist_Annual_Revenue_clc": build_calculated_measurement(
            api_name="Hist_Annual_Revenue_clc",
            label="Annual Revenue",
            expression=f"[{OBJECT_NAME}].[{ANNUAL_REVENUE_FIELD}]",
            aggregation_type="Sum",
            data_type="Number",
        ),
    }


def build_metric_payloads() -> dict[str, dict]:
    additional_dimensions = [
        {"tableFieldReference": {"fieldApiName": STAGE_FIELD, "tableApiName": OBJECT_NAME}},
        {"tableFieldReference": {"fieldApiName": PRODUCT_FIELD, "tableApiName": OBJECT_NAME}},
        {"tableFieldReference": {"fieldApiName": INDUSTRY_FIELD, "tableApiName": OBJECT_NAME}},
    ]

    metric_map = {
        "Hist_Amount_mtc": "Hist_Amount_clc",
        "Hist_Expected_Revenue_mtc": "Hist_Expected_Revenue_clc",
        "Hist_Closed_Won_Amount_mtc": "Hist_Closed_Won_Amount_clc",
        "Hist_Open_Pipeline_mtc": "Hist_Open_Pipeline_clc",
        "Hist_Revenue_Gap_mtc": "Hist_Revenue_Gap_clc",
        "Hist_Closed_Won_Count_mtc": "Hist_Closed_Won_Count_clc",
        "Hist_Open_Opportunity_Count_mtc": "Hist_Open_Opportunity_Count_clc",
        "Hist_Annual_Revenue_mtc": "Hist_Annual_Revenue_clc",
    }
    payloads: dict[str, dict] = {}
    for metric_name, calc_name in metric_map.items():
        payloads[metric_name] = build_semantic_metric(
            api_name=metric_name,
            label=metric_name.replace("Hist_", "").replace("_mtc", "").replace("_", " "),
            calculated_field_api_name=calc_name,
            time_dimension_field_name=DATE_FIELD,
            time_dimension_table_name=OBJECT_NAME,
            additional_dimensions=additional_dimensions,
        )
    return payloads


def build_visualization_payloads() -> dict[str, dict]:
    return {
        "Hist_Expected_Revenue_Trend": make_viz_payload(
            chart_type="line",
            name="Hist_Expected_Revenue_Trend",
            label="Expected Revenue Trend",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={DATE_FIELD}", f"objectName={OBJECT_NAME}", "function=DatePartMonth"],
                ["F2", "role=Measure", "fieldName=Hist_Expected_Revenue_clc", "objectName=None", "function=Sum"],
            ],
        ),
        "Hist_Closed_Won_Trend": make_viz_payload(
            chart_type="line",
            name="Hist_Closed_Won_Trend",
            label="Closed Won Amount Trend",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={DATE_FIELD}", f"objectName={OBJECT_NAME}", "function=DatePartMonth"],
                ["F2", "role=Measure", "fieldName=Hist_Closed_Won_Amount_clc", "objectName=None", "function=Sum"],
            ],
        ),
        "Hist_Open_Pipeline_By_Stage": make_viz_payload(
            chart_type="bar",
            name="Hist_Open_Pipeline_By_Stage",
            label="Open Pipeline by Stage",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={STAGE_FIELD}", f"objectName={OBJECT_NAME}"],
                ["F2", "role=Measure", "fieldName=Hist_Open_Pipeline_clc", "objectName=None", "function=Sum"],
            ],
        ),
        "Hist_Closed_Won_By_Product_Family": make_viz_payload(
            chart_type="bar",
            name="Hist_Closed_Won_By_Product_Family",
            label="Closed Won Amount by Product Family",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={PRODUCT_FIELD}", f"objectName={OBJECT_NAME}"],
                ["F2", "role=Measure", "fieldName=Hist_Closed_Won_Amount_clc", "objectName=None", "function=Sum"],
            ],
        ),
        "Hist_Amount_By_Industry": make_viz_payload(
            chart_type="bar",
            name="Hist_Amount_By_Industry",
            label="Amount by Industry",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={INDUSTRY_FIELD}", f"objectName={OBJECT_NAME}"],
                ["F2", "role=Measure", "fieldName=Hist_Amount_clc", "objectName=None", "function=Sum"],
            ],
        ),
        "Hist_Expected_Revenue_By_State": make_viz_payload(
            chart_type="bar",
            name="Hist_Expected_Revenue_By_State",
            label="Expected Revenue by Billing State",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={BILLING_STATE_FIELD}", f"objectName={OBJECT_NAME}"],
                ["F2", "role=Measure", "fieldName=Hist_Expected_Revenue_clc", "objectName=None", "function=Sum"],
            ],
        ),
        "Hist_Open_Opportunity_Count_By_Type": make_viz_payload(
            chart_type="bar",
            name="Hist_Open_Opportunity_Count_By_Type",
            label="Open Opportunity Count by Type",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={OPPORTUNITY_TYPE_FIELD}", f"objectName={OBJECT_NAME}"],
                ["F2", "role=Measure", "fieldName=Hist_Open_Opportunity_Count_clc", "objectName=None", "function=Sum"],
            ],
        ),
    }


def build_filter_defs() -> list[dict]:
    return [
        {"fieldName": DATE_FIELD, "objectName": OBJECT_NAME, "dataType": "Date", "label": "Close Date"},
        {"fieldName": STAGE_FIELD, "objectName": OBJECT_NAME, "dataType": "Text", "label": "Stage"},
        {"fieldName": PRODUCT_FIELD, "objectName": OBJECT_NAME, "dataType": "Text", "label": "Product Family"},
        {"fieldName": INDUSTRY_FIELD, "objectName": OBJECT_NAME, "dataType": "Text", "label": "Industry"},
        {"fieldName": OPPORTUNITY_TYPE_FIELD, "objectName": OBJECT_NAME, "dataType": "Text", "label": "Opportunity Type"},
        {"fieldName": IS_WON_FIELD, "objectName": OBJECT_NAME, "dataType": "Boolean", "label": "Won"},
    ]


def create_dashboards(access_token: str, instance_url: str, template_names: list[str], replace: bool) -> dict:
    calc_fields = build_calc_fields()
    metrics = build_metric_payloads()
    visualizations = build_visualization_payloads()
    filter_defs = build_filter_defs()

    calc_results = {name: ensure_semantic_resource(access_token, instance_url, "measurements", name, payload) for name, payload in calc_fields.items()}
    metric_results = {name: ensure_semantic_resource(access_token, instance_url, "metrics", name, payload) for name, payload in metrics.items()}
    viz_results = {name: ensure_visualization(access_token, instance_url, payload) for name, payload in visualizations.items()}

    metric_names = list(metrics.keys())
    visualization_names = list(visualizations.keys())

    dashboard_results = {}
    for template_name in template_names:
        template = load_dashboard_template(template_name)
        if not template:
            dashboard_results[template_name] = {"created": False, "error": "Template not found"}
            continue

        dashboard_name = f"Hubbell_Historical_{template_name}_dashboard"
        dashboard_label = f"Hubbell Historical Opportunity Performance - {template_name}"
        dashboard = assign_widget_sources(template, metric_names, visualization_names, filter_defs)
        dashboard["name"] = dashboard_name
        dashboard["label"] = dashboard_label
        dashboard["description"] = f"Template-driven dashboard for {MODEL_LABEL} using {template_name}."
        result, created = ensure_dashboard(access_token, instance_url, dashboard, replace)
        dashboard_results[template_name] = {
            "created": created,
            "id": result.get("id"),
            "apiName": result.get("apiName") or result.get("name") or dashboard_name,
        }

    return {
        "calcFields": {name: {"created": created, "id": result.get("id"), "apiName": result.get("apiName", name)} for name, (result, created) in calc_results.items()},
        "metrics": {name: {"created": created, "id": result.get("id"), "apiName": result.get("apiName", name)} for name, (result, created) in metric_results.items()},
        "visualizations": {name: {"created": created, "id": result.get("id"), "apiName": result.get("apiName") or result.get("name", name)} for name, (result, created) in viz_results.items()},
        "dashboards": dashboard_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create template-driven dashboards for Hubbell Historical Opportunity Performance.")
    parser.add_argument("--target-org", default=TARGET_ORG)
    parser.add_argument("--replace-dashboards", action="store_true")
    parser.add_argument(
        "--templates",
        nargs="*",
        default=["z_layout", "f_layout", "performance_overview", "c360_full", "c360_half", "c360_vertical"],
        help="Template names to try from tableau-next-author/templates/dashboards.",
    )
    parser.add_argument("--output", default=str(ROOT / "tmp" / "hubbell-historical-template-dashboards.result.json"))
    args = parser.parse_args()

    access_token, instance_url = resolve_credentials(args.target_org)
    summary = create_dashboards(access_token, instance_url, args.templates, args.replace_dashboards)
    summary.update(
        {
            "targetOrg": args.target_org,
            "workspaceName": WORKSPACE_NAME,
            "workspaceId": WORKSPACE_ID,
            "modelApiName": MODEL_API_NAME,
            "modelId": MODEL_ID,
            "modelLabel": MODEL_LABEL,
            "templatesRequested": args.templates,
        }
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())