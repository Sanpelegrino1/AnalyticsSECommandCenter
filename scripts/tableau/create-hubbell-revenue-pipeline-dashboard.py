#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import requests


ROOT = Path(__file__).resolve().parents[2]
TOOLKIT_ROOT = ROOT / "tableau-skills-external-repo" / "skills" / "tableau-next-author" / "scripts"
if str(TOOLKIT_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLKIT_ROOT))

from generate_viz import build_viz  # noqa: E402
from lib.calc_field_templates import build_calculated_measurement  # noqa: E402
from lib.dashboard_template_loader import customize_dashboard_template, load_dashboard_template  # noqa: E402
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


MODEL_API_NAME = "Hubbell_Account_Semantic_Model"
MODEL_LABEL = "Hubbell Account Semantic Model"
WORKSPACE_NAME = "Hubbell"
WORKSPACE_LABEL = "Hubbell"

OPPORTUNITY_OBJECT = "Opportunity4"
DATE_FIELD = "CloseDate1"
STAGE_FIELD = "StageName1"
FORECAST_FIELD = "ForecastCategory1"
OPPORTUNITY_TYPE_FIELD = "OpportunityType1"
EXPECTED_AMOUNT_FIELD = "ExpectedAmount"
TOTAL_AMOUNT_FIELD = "TotalOpportunityAmount1"
IS_WON_FIELD = "IsWon1"
IS_CLOSED_FIELD = "IsClosed1"


def resolve_credentials(target_org: str | None) -> tuple[str, str]:
    if os.environ.get("SF_TOKEN") and os.environ.get("SF_INSTANCE"):
        return get_credentials()

    if not target_org:
        raise RuntimeError("Provide --target-org or set SF_TOKEN and SF_INSTANCE.")

    command = ["sf", "org", "display", "--target-org", target_org, "--json"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
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


def ensure_semantic_resource(
    access_token: str,
    instance_url: str,
    resource_type: str,
    api_name: str,
    payload: dict,
) -> tuple[dict, bool]:
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


def make_viz_payload(
    *,
    chart_type: str,
    name: str,
    label: str,
    columns: list[str],
    rows: list[str],
    fields: list[list[str]],
    encodings: list[list[str]] | None = None,
    measure_values: list[str] | None = None,
) -> dict:
    payload = build_viz(
        SimpleNamespace(
            chart_type=chart_type,
            name=name,
            label=label,
            sdm_name=MODEL_API_NAME,
            sdm_label=MODEL_LABEL,
            workspace_name=WORKSPACE_NAME,
            workspace_label=WORKSPACE_LABEL,
            columns=columns,
            rows=rows,
            field=fields,
            encoding=encodings,
            legend=None,
            sort=None,
            style=None,
            measure_values=measure_values,
        )
    )
    is_valid, errors = validate_full_visualization(payload)
    if not is_valid:
        raise RuntimeError(f"Visualization payload {name} is invalid: {'; '.join(errors)}")
    return payload


def build_dashboard_payload(template_name: str, dashboard_name: str, dashboard_label: str, sdm_id: str) -> dict:
    template = load_dashboard_template(template_name)
    if not template:
        raise RuntimeError(f"Dashboard template '{template_name}' was not found in the external repo.")

    visualization_names = [
        "Hubbell_Expected_Revenue_Trend",
        "Hubbell_Open_Pipeline_By_Forecast_Category",
        "Hubbell_Closed_Won_Revenue_By_Stage",
        "Hubbell_Expected_Revenue_By_Stage",
        "Hubbell_Open_Pipeline_Trend",
    ]
    metric_names = [
        "Expected_Revenue_mtc",
        "Closed_Won_Revenue_mtc",
        "Open_Pipeline_mtc",
        "Revenue_Gap_mtc",
        "Closed_Won_Count_mtc",
        "Open_Opportunity_Count_mtc",
    ]
    filter_defs = [
        {"fieldName": DATE_FIELD, "objectName": OPPORTUNITY_OBJECT, "dataType": "Date", "label": "Close Date"},
        {"fieldName": STAGE_FIELD, "objectName": OPPORTUNITY_OBJECT, "dataType": "Text", "label": "Stage"},
        {"fieldName": FORECAST_FIELD, "objectName": OPPORTUNITY_OBJECT, "dataType": "Text", "label": "Forecast Category"},
        {"fieldName": IS_CLOSED_FIELD, "objectName": OPPORTUNITY_OBJECT, "dataType": "Boolean", "label": "Closed"},
        {"fieldName": IS_WON_FIELD, "objectName": OPPORTUNITY_OBJECT, "dataType": "Boolean", "label": "Won"},
        {"fieldName": OPPORTUNITY_TYPE_FIELD, "objectName": OPPORTUNITY_OBJECT, "dataType": "Text", "label": "Opportunity Type"},
    ]

    dashboard = customize_dashboard_template(
        template=template,
        name=dashboard_name,
        label=dashboard_label,
        workspace_name=WORKSPACE_NAME,
        visualization_names=visualization_names,
        metric_names=metric_names,
        filter_defs=filter_defs,
        sdm_name=MODEL_API_NAME,
        sdm_id=sdm_id,
    )
    dashboard["description"] = f"Template-driven {template_name} dashboard for Hubbell revenue and pipeline."
    return dashboard


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Hubbell revenue and pipeline Tableau Next dashboard.")
    parser.add_argument("--target-org", default="STORM_TABLEAU_NEXT", help="Salesforce alias to use when SF_TOKEN/SF_INSTANCE are not set.")
    parser.add_argument("--replace-dashboard", action="store_true", help="Delete and recreate the dashboard if it already exists.")
    parser.add_argument("--dashboard-template", default="z_layout", help="External dashboard template to use, for example z_layout or f_layout.")
    parser.add_argument("--dashboard-name", default="Hubbell_Revenue_Pipeline_Z_Layout_dashboard", help="API name for the dashboard to create.")
    parser.add_argument("--dashboard-label", default="Hubbell Revenue and Pipeline Overview (Template)", help="Display label for the dashboard.")
    parser.add_argument("--output", default=str(ROOT / "tmp" / "hubbell-revenue-pipeline-dashboard.result.json"), help="Summary JSON output path.")
    args = parser.parse_args()

    access_token, instance_url = resolve_credentials(args.target_org)
    model = api_get_optional(access_token, instance_url, f"/services/data/v66.0/ssot/semantic/models/{MODEL_API_NAME}")
    if not model:
        raise RuntimeError(f"Semantic model {MODEL_API_NAME} was not found")

    sdm_id = model.get("id")
    if not sdm_id:
        raise RuntimeError(f"Semantic model {MODEL_API_NAME} did not return an id")

    calc_fields = {
        "Expected_Revenue_clc": build_calculated_measurement(
            api_name="Expected_Revenue_clc",
            label="Expected Revenue",
            expression=f"[{OPPORTUNITY_OBJECT}].[{EXPECTED_AMOUNT_FIELD}]",
            aggregation_type="Sum",
            data_type="Number",
            description="Expected revenue passthrough for dashboard metrics and charts.",
        ),
        "Closed_Won_Revenue_clc": build_calculated_measurement(
            api_name="Closed_Won_Revenue_clc",
            label="Closed Won Revenue",
            expression=f"IF [{OPPORTUNITY_OBJECT}].[{IS_WON_FIELD}] THEN [{OPPORTUNITY_OBJECT}].[{TOTAL_AMOUNT_FIELD}] ELSE 0 END",
            aggregation_type="Sum",
            data_type="Number",
            description="Closed won revenue for Hubbell opportunities.",
        ),
        "Open_Pipeline_clc": build_calculated_measurement(
            api_name="Open_Pipeline_clc",
            label="Open Pipeline",
            expression=f"IF NOT [{OPPORTUNITY_OBJECT}].[{IS_CLOSED_FIELD}] THEN [{OPPORTUNITY_OBJECT}].[{TOTAL_AMOUNT_FIELD}] ELSE 0 END",
            aggregation_type="Sum",
            data_type="Number",
            description="Open pipeline value for Hubbell opportunities.",
        ),
        "Revenue_Gap_clc": build_calculated_measurement(
            api_name="Revenue_Gap_clc",
            label="Revenue Gap",
            expression=(
                f"[{OPPORTUNITY_OBJECT}].[{EXPECTED_AMOUNT_FIELD}] - "
                f"(IF [{OPPORTUNITY_OBJECT}].[{IS_WON_FIELD}] THEN [{OPPORTUNITY_OBJECT}].[{TOTAL_AMOUNT_FIELD}] ELSE 0 END)"
            ),
            aggregation_type="Sum",
            data_type="Number",
            description="Difference between expected revenue and closed won revenue.",
        ),
        "Closed_Won_Count_clc": build_calculated_measurement(
            api_name="Closed_Won_Count_clc",
            label="Closed Won Count",
            expression=f"IF [{OPPORTUNITY_OBJECT}].[{IS_WON_FIELD}] THEN 1 ELSE 0 END",
            aggregation_type="Sum",
            data_type="Number",
            description="Count of closed won Hubbell opportunities.",
        ),
        "Open_Opportunity_Count_clc": build_calculated_measurement(
            api_name="Open_Opportunity_Count_clc",
            label="Open Opportunity Count",
            expression=f"IF NOT [{OPPORTUNITY_OBJECT}].[{IS_CLOSED_FIELD}] THEN 1 ELSE 0 END",
            aggregation_type="Sum",
            data_type="Number",
            description="Count of open Hubbell opportunities.",
        ),
    }

    metric_payloads = {
        "Expected_Revenue_mtc": build_semantic_metric(
            api_name="Expected_Revenue_mtc",
            label="Expected Revenue",
            calculated_field_api_name="Expected_Revenue_clc",
            time_dimension_field_name=DATE_FIELD,
            time_dimension_table_name=OPPORTUNITY_OBJECT,
            description="Expected revenue metric for Hubbell.",
            additional_dimensions=[
                {"tableFieldReference": {"fieldApiName": STAGE_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
                {"tableFieldReference": {"fieldApiName": FORECAST_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
            ],
        ),
        "Closed_Won_Revenue_mtc": build_semantic_metric(
            api_name="Closed_Won_Revenue_mtc",
            label="Closed Won Revenue",
            calculated_field_api_name="Closed_Won_Revenue_clc",
            time_dimension_field_name=DATE_FIELD,
            time_dimension_table_name=OPPORTUNITY_OBJECT,
            description="Closed won revenue metric for Hubbell.",
            additional_dimensions=[
                {"tableFieldReference": {"fieldApiName": STAGE_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
                {"tableFieldReference": {"fieldApiName": FORECAST_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
            ],
        ),
        "Open_Pipeline_mtc": build_semantic_metric(
            api_name="Open_Pipeline_mtc",
            label="Open Pipeline",
            calculated_field_api_name="Open_Pipeline_clc",
            time_dimension_field_name=DATE_FIELD,
            time_dimension_table_name=OPPORTUNITY_OBJECT,
            description="Open pipeline metric for Hubbell.",
            additional_dimensions=[
                {"tableFieldReference": {"fieldApiName": STAGE_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
                {"tableFieldReference": {"fieldApiName": FORECAST_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
            ],
        ),
        "Revenue_Gap_mtc": build_semantic_metric(
            api_name="Revenue_Gap_mtc",
            label="Revenue Gap",
            calculated_field_api_name="Revenue_Gap_clc",
            time_dimension_field_name=DATE_FIELD,
            time_dimension_table_name=OPPORTUNITY_OBJECT,
            description="Gap between expected revenue and closed won revenue for Hubbell.",
            additional_dimensions=[
                {"tableFieldReference": {"fieldApiName": STAGE_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
                {"tableFieldReference": {"fieldApiName": FORECAST_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
            ],
        ),
        "Closed_Won_Count_mtc": build_semantic_metric(
            api_name="Closed_Won_Count_mtc",
            label="Closed Won Count",
            calculated_field_api_name="Closed_Won_Count_clc",
            time_dimension_field_name=DATE_FIELD,
            time_dimension_table_name=OPPORTUNITY_OBJECT,
            description="Count of closed won Hubbell opportunities.",
            additional_dimensions=[
                {"tableFieldReference": {"fieldApiName": STAGE_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
                {"tableFieldReference": {"fieldApiName": FORECAST_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
            ],
        ),
        "Open_Opportunity_Count_mtc": build_semantic_metric(
            api_name="Open_Opportunity_Count_mtc",
            label="Open Opportunity Count",
            calculated_field_api_name="Open_Opportunity_Count_clc",
            time_dimension_field_name=DATE_FIELD,
            time_dimension_table_name=OPPORTUNITY_OBJECT,
            description="Count of open Hubbell opportunities.",
            additional_dimensions=[
                {"tableFieldReference": {"fieldApiName": STAGE_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
                {"tableFieldReference": {"fieldApiName": FORECAST_FIELD, "tableApiName": OPPORTUNITY_OBJECT}},
            ],
        ),
    }

    viz_payloads = {
        "Hubbell_Expected_Revenue_Trend": make_viz_payload(
            chart_type="line",
            name="Hubbell_Expected_Revenue_Trend",
            label="Expected Revenue Trend",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={DATE_FIELD}", f"objectName={OPPORTUNITY_OBJECT}", "function=DatePartMonth"],
                ["F2", "role=Measure", "fieldName=Expected_Revenue_clc", "objectName=None", "function=Sum"],
            ],
            encodings=None,
        ),
        "Hubbell_Open_Pipeline_By_Forecast_Category": make_viz_payload(
            chart_type="bar",
            name="Hubbell_Open_Pipeline_By_Forecast_Category",
            label="Open Pipeline by Forecast Category",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={FORECAST_FIELD}", f"objectName={OPPORTUNITY_OBJECT}"],
                ["F2", "role=Measure", "fieldName=Open_Pipeline_clc", "objectName=None", "function=Sum"],
            ],
            encodings=None,
        ),
        "Hubbell_Closed_Won_Revenue_By_Stage": make_viz_payload(
            chart_type="bar",
            name="Hubbell_Closed_Won_Revenue_By_Stage",
            label="Closed Won Revenue by Stage",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={STAGE_FIELD}", f"objectName={OPPORTUNITY_OBJECT}"],
                ["F2", "role=Measure", "fieldName=Closed_Won_Revenue_clc", "objectName=None", "function=Sum"],
            ],
            encodings=None,
        ),
        "Hubbell_Expected_Revenue_By_Stage": make_viz_payload(
            chart_type="bar",
            name="Hubbell_Expected_Revenue_By_Stage",
            label="Expected Revenue by Stage",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={STAGE_FIELD}", f"objectName={OPPORTUNITY_OBJECT}"],
                ["F2", "role=Measure", "fieldName=Expected_Revenue_clc", "objectName=None", "function=Sum"],
            ],
            encodings=None,
        ),
        "Hubbell_Open_Pipeline_Trend": make_viz_payload(
            chart_type="line",
            name="Hubbell_Open_Pipeline_Trend",
            label="Open Pipeline Trend",
            columns=["F1"],
            rows=["F2"],
            fields=[
                ["F1", "role=Dimension", f"fieldName={DATE_FIELD}", f"objectName={OPPORTUNITY_OBJECT}", "function=DatePartMonth"],
                ["F2", "role=Measure", "fieldName=Open_Pipeline_clc", "objectName=None", "function=Sum"],
            ],
            encodings=None,
        ),
    }

    calc_results = {}
    for api_name, payload in calc_fields.items():
        calc_results[api_name] = ensure_semantic_resource(access_token, instance_url, "measurements", api_name, payload)

    metric_results = {}
    metric_ids = {}
    for api_name, payload in metric_payloads.items():
        metric_result, created = ensure_semantic_resource(access_token, instance_url, "metrics", api_name, payload)
        metric_results[api_name] = (metric_result, created)
        metric_ids[api_name] = metric_result.get("id")
        if not metric_ids[api_name]:
            metric_lookup = api_get_optional(access_token, instance_url, calculated_field_endpoint(MODEL_API_NAME, "metrics", api_name))
            if not metric_lookup or not metric_lookup.get("id"):
                raise RuntimeError(f"Metric {api_name} did not return an id")
            metric_ids[api_name] = metric_lookup["id"]

    viz_results = {}
    for name, payload in viz_payloads.items():
        viz_result, created = ensure_visualization(access_token, instance_url, payload)
        viz_results[name] = (viz_result, created)

    dashboard_payload = build_dashboard_payload(args.dashboard_template, args.dashboard_name, args.dashboard_label, sdm_id)
    dashboard_result, dashboard_created = ensure_dashboard(access_token, instance_url, dashboard_payload, args.replace_dashboard)

    summary = {
        "targetOrg": args.target_org,
        "dashboardTemplate": args.dashboard_template,
        "modelApiName": MODEL_API_NAME,
        "modelId": sdm_id,
        "calcFields": {name: {"created": created, "id": result.get("id"), "apiName": result.get("apiName", name)} for name, (result, created) in calc_results.items()},
        "metrics": {name: {"created": created, "id": result.get("id"), "apiName": result.get("apiName", name)} for name, (result, created) in metric_results.items()},
        "visualizations": {name: {"created": created, "id": result.get("id"), "apiName": result.get("apiName") or result.get("name", name)} for name, (result, created) in viz_results.items()},
        "dashboard": {
            "created": dashboard_created,
            "id": dashboard_result.get("id"),
            "apiName": dashboard_result.get("apiName") or dashboard_result.get("name") or dashboard_payload["name"],
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())