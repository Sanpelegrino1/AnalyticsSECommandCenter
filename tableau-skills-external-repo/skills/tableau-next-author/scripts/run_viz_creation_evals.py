#!/usr/bin/env python3
"""Matrix-eval: build (and optionally POST) template x SDM cases from a manifest.

Uses v66.0 and minorVersion=12 via lib.sf_api.visualization_endpoint.

  # From skill directory:
  cd skills/tableau-next-author
  python scripts/run_viz_creation_evals.py --manifest evals/viz_creation_eval_manifest.json --post

  # From repo root (uses scripts/run_viz_creation_evals.py wrapper):
  python scripts/run_viz_creation_evals.py --manifest evals/viz_creation_eval_manifest.json --post

Exit codes: 0 = matrix finished; 1 = preflight/config error; 2 = strict failure (--strict-exit).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.sf_api import (  # noqa: E402
    get_credentials,
    sf_get,
    sf_post,
    sdm_detail_endpoint,
    visualization_endpoint,
    workspace_endpoint,
)
from lib.sdm_discovery import discover_sdm_fields  # noqa: E402
from lib.templates import build_viz_from_template_def  # noqa: E402
from lib.validators import validate  # noqa: E402
from lib.viz_templates import find_matching_fields, get_template, list_templates  # noqa: E402

API_ERROR_MAX_LEN = 4096
VIZ_NAME_MAX_LEN = 75


def _skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _rel_skill_path(path: Path) -> str:
    path = path.resolve()
    root = _skill_root().resolve()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _safe_api_segment(s: str, max_len: int = 14) -> str:
    t = re.sub(r"[^0-9A-Za-z_]", "_", s).strip("_")
    return (t or "x")[:max_len]


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _fingerprint(message: str, api_error: Optional[str]) -> str:
    src = (api_error or message or "").strip()
    if not src:
        return ""
    lines = [ln.strip() for ln in src.split("\n") if ln.strip()]
    line = lines[0]
    # Include 2nd line (e.g. INVALID_INPUT Message:) so summaries distinguish filters vs stack vs parser errors
    if len(lines) >= 2 and line.startswith("HTTP "):
        line = f"{lines[0]} | {lines[1]}"
    if len(line) > 120:
        return hashlib.sha256(line.encode()).hexdigest()[:12]
    return line[:120]


def _http_status_from_error(err: str) -> Optional[int]:
    m = re.match(r"HTTP (\d+) ", err)
    return int(m.group(1)) if m else None


def _slim_field_mapping(fm: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    keys = (
        "fieldName",
        "objectName",
        "role",
        "displayCategory",
        "dataType",
        "function",
        "label",
        "aggregationType",
    )
    out: Dict[str, Dict[str, Any]] = {}
    for slot, d in fm.items():
        out[slot] = {k: d.get(k) for k in keys if k in d}
    return out


def _viz_name(prefix: str, run_id: str, case_index: int, template: str, sdm: str) -> str:
    core = (
        f"{_safe_api_segment(prefix, 12)}_{run_id[:6]}_{case_index:04d}_"
        f"{_safe_api_segment(template, 10)}_{_safe_api_segment(sdm, 12)}"
    )
    return core[:VIZ_NAME_MAX_LEN]


def _case_file_id(case_index: int, template: str, sdm: str) -> str:
    h = hashlib.sha256(f"{case_index}|{template}|{sdm}".encode()).hexdigest()[:8]
    return f"{case_index:04d}_{_safe_api_segment(template, 12)}_{_safe_api_segment(sdm, 12)}_{h}"


def _write_artifacts(
    artifacts_dir: Path,
    case_file_id: str,
    *,
    viz_json: Optional[Dict[str, Any]] = None,
    field_mappings: Optional[Dict[str, Dict[str, Any]]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    rel: Dict[str, str] = {}
    if viz_json is not None:
        p = artifacts_dir / f"viz_{case_file_id}.json"
        p.write_text(json.dumps(viz_json, indent=2) + "\n", encoding="utf-8")
        rel["viz"] = _rel_skill_path(p)
    if field_mappings is not None:
        p = artifacts_dir / f"field_mappings_{case_file_id}.json"
        p.write_text(json.dumps(_slim_field_mapping(field_mappings), indent=2) + "\n", encoding="utf-8")
        rel["field_mappings"] = _rel_skill_path(p)
    if meta is not None:
        p = artifacts_dir / f"request_meta_{case_file_id}.json"
        p.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        rel["request_meta"] = _rel_skill_path(p)
    return rel


def _load_manifest(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _resolve_templates(manifest: Dict[str, Any], cli_templates: Optional[List[str]]) -> List[str]:
    if cli_templates:
        return cli_templates
    t = manifest.get("templates", "all")
    if t == "all":
        return sorted(list_templates())
    if isinstance(t, list):
        return list(t)
    raise ValueError("manifest 'templates' must be 'all' or a JSON array of template names")


def _preflight_workspace(workspace_name: str) -> None:
    token, instance = get_credentials()
    data = sf_get(token, instance, workspace_endpoint(workspace_name))
    if data is None:
        print(
            f"Error: Workspace '{workspace_name}' not found or not accessible. "
            "Create it in the org or fix workspace_name in the manifest.",
            file=sys.stderr,
        )
        sys.exit(1)


def run_case(
    *,
    case_index: int,
    template_name: str,
    sdm_name: str,
    workspace_name: str,
    workspace_label: str,
    name_prefix: str,
    run_id: str,
    auto_match: bool,
    do_post: bool,
    save_payloads: str,
    artifacts_dir: Path,
    sleep_s: float,
) -> Dict[str, Any]:
    case_file_id = _case_file_id(case_index, template_name, sdm_name)
    viz_name = _viz_name(name_prefix, run_id, case_index, template_name, sdm_name)
    label = f"Eval {template_name} / {sdm_name}"[:80]

    base_row: Dict[str, Any] = {
        "run_id": run_id,
        "case_id": case_file_id,
        "case_index": case_index,
        "template": template_name,
        "sdm": sdm_name,
        "workspace_name": workspace_name,
        "viz_name_requested": viz_name,
    }

    template = get_template(template_name)
    if not template:
        return {
            **base_row,
            "status": "skipped",
            "phase": "match",
            "message": f"Unknown template '{template_name}'",
            "details": {},
            "error_fingerprint": "unknown_template",
            "artifact_paths": {},
        }

    sdm_fields = discover_sdm_fields(sdm_name)
    if sdm_fields is None:
        msg = f"Could not discover SDM '{sdm_name}'"
        return {
            **base_row,
            "status": "discover_failed",
            "phase": "discover",
            "message": msg,
            "details": {},
            "error_fingerprint": _fingerprint(msg, None),
            "artifact_paths": {},
        }

    token, instance = get_credentials()
    sdm_data = sf_get(token, instance, sdm_detail_endpoint(sdm_name))
    sdm_label = sdm_data.get("label", sdm_name) if sdm_data else sdm_name

    field_mappings: Dict[str, Dict[str, Any]] = {}
    if auto_match:
        all_template_fields = {**template["required_fields"], **template.get("optional_fields", {})}
        field_mappings = find_matching_fields(
            sdm_fields,
            all_template_fields,
            user_overrides=None,
        )
    required_fields = template["required_fields"]
    missing = sorted(set(required_fields.keys()) - set(field_mappings.keys()))
    if missing:
        row = {
            **base_row,
            "status": "field_match_failed",
            "phase": "match",
            "message": "Missing required template field mappings",
            "details": {"missing_fields": missing},
            "error_fingerprint": "field_match:" + ",".join(missing[:5]),
            "artifact_paths": {},
        }
        if save_payloads == "failures_only":
            meta = {
                **{k: row[k] for k in ("run_id", "case_id", "template", "sdm", "workspace_name", "viz_name_requested")},
                "status": row["status"],
                "phase": row["phase"],
                "missing_fields": missing,
            }
            row["artifact_paths"] = _write_artifacts(
                artifacts_dir, case_file_id, meta=meta
            )
        return row

    try:
        viz_json = build_viz_from_template_def(
            template_def=template,
            sdm_name=sdm_name,
            sdm_label=sdm_label,
            workspace_name=workspace_name,
            workspace_label=workspace_label,
            field_mappings=field_mappings,
            name=viz_name,
            label=label,
            overrides=None,
        )
    except Exception as exc:
        msg = f"build_viz_from_template_def failed: {exc}"
        row = {
            **base_row,
            "status": "build_failed",
            "phase": "build",
            "message": msg,
            "details": {"exception_type": type(exc).__name__},
            "error_fingerprint": _fingerprint(msg, None),
            "artifact_paths": {},
        }
        if save_payloads == "failures_only":
            meta = {
                **{k: row[k] for k in ("run_id", "case_id", "template", "sdm", "workspace_name", "viz_name_requested")},
                "status": row["status"],
                "phase": row["phase"],
                "details": row["details"],
            }
            row["artifact_paths"] = _write_artifacts(
                artifacts_dir, case_file_id, field_mappings=field_mappings, meta=meta
            )
        return row

    val_results = validate(viz_json)
    failures = [r for r in val_results if not r.ok]
    if failures:
        row = {
            **base_row,
            "status": "validation_failed",
            "phase": "validate",
            "message": "Local validate() failed",
            "details": {
                "validation_results": [{"rule": r.rule, "message": r.message} for r in failures],
            },
            "error_fingerprint": _fingerprint(failures[0].message, None),
            "artifact_paths": {},
        }
        if save_payloads in ("failures_only", "all"):
            meta = {
                **{k: row[k] for k in ("run_id", "case_id", "template", "sdm", "workspace_name", "viz_name_requested")},
                "status": row["status"],
                "phase": row["phase"],
            }
            row["artifact_paths"] = _write_artifacts(
                artifacts_dir,
                case_file_id,
                viz_json=viz_json,
                field_mappings=field_mappings,
                meta=meta,
            )
        return row

    if not do_post:
        row = {
            **base_row,
            "status": "validated",
            "phase": "validate",
            "message": "Built and passed validate(); POST skipped",
            "details": {},
            "error_fingerprint": "",
            "artifact_paths": {},
        }
        if save_payloads == "all":
            meta = {
                **{k: row[k] for k in ("run_id", "case_id", "template", "sdm", "workspace_name", "viz_name_requested")},
                "status": row["status"],
            }
            row["artifact_paths"] = _write_artifacts(
                artifacts_dir,
                case_file_id,
                viz_json=viz_json,
                field_mappings=field_mappings,
                meta=meta,
            )
        return row

    response, error = sf_post(token, instance, visualization_endpoint(), viz_json)
    if sleep_s > 0:
        time.sleep(sleep_s)

    if error:
        api_err = _truncate(error, API_ERROR_MAX_LEN)
        row = {
            **base_row,
            "status": "post_failed",
            "phase": "post",
            "message": "POST visualization failed",
            "details": {
                "http_status": _http_status_from_error(error),
                "api_error": api_err,
            },
            "error_fingerprint": _fingerprint(error, api_err),
            "artifact_paths": {},
        }
        if save_payloads in ("failures_only", "all"):
            meta = {
                **{k: row[k] for k in ("run_id", "case_id", "template", "sdm", "workspace_name", "viz_name_requested")},
                "status": row["status"],
            }
            row["artifact_paths"] = _write_artifacts(
                artifacts_dir,
                case_file_id,
                viz_json=viz_json,
                field_mappings=field_mappings,
                meta=meta,
            )
        return row

    row = {
        **base_row,
        "status": "posted",
        "phase": "posted",
        "message": "Created visualization",
        "details": {},
        "error_fingerprint": "",
        "viz_id": response.get("id"),
        "viz_url": response.get("url"),
        "viz_name_actual": response.get("name", viz_name),
        "artifact_paths": {},
    }
    if save_payloads == "all":
        meta = {
            **{k: base_row[k] for k in ("run_id", "case_id", "template", "sdm", "workspace_name", "viz_name_requested")},
            "status": "posted",
            "viz_id": response.get("id"),
        }
        row["artifact_paths"] = _write_artifacts(
            artifacts_dir,
            case_file_id,
            viz_json=viz_json,
            field_mappings=field_mappings,
            meta=meta,
        )
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Viz creation matrix eval (v66.0 minor 12)")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=_skill_root() / "evals" / "viz_creation_eval_manifest.json",
        help="Path to eval manifest JSON",
    )
    parser.add_argument("--workspace", type=str, help="Override workspace API name")
    parser.add_argument("--workspace-label", type=str, help="Override workspace label")
    parser.add_argument("--sdm", action="append", dest="sdms", help="Restrict to SDM (repeatable)")
    parser.add_argument("--template", action="append", dest="templates", help="Restrict to template (repeatable)")
    parser.add_argument("--post", action="store_true", help="POST each visualization after validate")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        help="Directory for payload artifacts (default: evals/runs/<timestamp>_<runid>)",
    )
    parser.add_argument(
        "--save-payloads",
        choices=("failures_only", "all", "none"),
        help="Override manifest defaults.save_payloads",
    )
    parser.add_argument("--output", type=Path, help="JSONL results path (default: under artifacts-dir)")
    parser.add_argument("--max-failures", type=int, default=0, help="Stop after N failing cases (0=disabled)")
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit 2 if any case did not reach posted (with --post) or validated (without --post)",
    )
    parser.add_argument("--skip-workspace-check", action="store_true", help="Skip GET workspace preflight")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    if not manifest_path.is_file():
        print(f"Error: manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    manifest = _load_manifest(manifest_path)
    workspace_name = args.workspace or manifest["workspace_name"]
    workspace_label = args.workspace_label or manifest.get("workspace_label") or workspace_name
    sdms = args.sdms if args.sdms else list(manifest["sdms"])
    defaults = manifest.get("defaults") or {}
    auto_match = bool(defaults.get("auto_match", True))
    name_prefix = str(defaults.get("name_prefix", "Eval_Viz"))
    sleep_s = float(defaults.get("sleep_seconds_between_posts", 0))
    save_payloads = args.save_payloads or defaults.get("save_payloads", "failures_only")
    if save_payloads not in ("failures_only", "all", "none"):
        save_payloads = "failures_only"

    try:
        template_list = _resolve_templates(manifest, args.templates)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    run_id = secrets.token_hex(6)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.artifacts_dir is None:
        artifacts_dir = _skill_root() / "evals" / "runs" / f"{ts}_{run_id}"
    else:
        artifacts_dir = args.artifacts_dir.resolve()

    output_path = args.output if args.output else artifacts_dir / "results.jsonl"

    if not args.skip_workspace_check:
        _preflight_workspace(workspace_name)

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("", encoding="utf-8")

    total = len(template_list) * len(sdms)
    print(
        f"Eval run {run_id}: {len(template_list)} templates x {len(sdms)} SDMs = {total} cases; "
        f"post={'yes' if args.post else 'no'}; save_payloads={save_payloads}",
        file=sys.stderr,
    )
    print(f"Artifacts: {artifacts_dir}", file=sys.stderr)
    print(f"JSONL: {output_path}", file=sys.stderr)

    results: List[Dict[str, Any]] = []
    failure_count = 0
    case_index = 0
    stop = False

    for sdm_name in sdms:
        if stop:
            break
        for template_name in template_list:
            case_index += 1
            row = run_case(
                case_index=case_index,
                template_name=template_name,
                sdm_name=sdm_name,
                workspace_name=workspace_name,
                workspace_label=workspace_label,
                name_prefix=name_prefix,
                run_id=run_id,
                auto_match=auto_match,
                do_post=args.post,
                save_payloads=save_payloads,
                artifacts_dir=artifacts_dir,
                sleep_s=sleep_s,
            )
            results.append(row)
            with output_path.open("a", encoding="utf-8") as out:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")

            st = row["status"]
            ok = st == "posted" if args.post else st == "validated"
            if not ok:
                failure_count += 1
                print(f"[{case_index}] FAIL {st} {template_name} @ {sdm_name}: {row.get('message')}", file=sys.stderr)
            else:
                print(f"[{case_index}] OK  {st} {template_name} @ {sdm_name}", file=sys.stderr)

            if args.max_failures > 0 and failure_count >= args.max_failures:
                print(f"Stopped: max_failures={args.max_failures}", file=sys.stderr)
                stop = True
                break

    by_status = Counter(r["status"] for r in results)
    fp = Counter(r["error_fingerprint"] for r in results if r.get("error_fingerprint"))

    print("\n=== Summary ===", file=sys.stderr)
    print(f"By status: {dict(by_status)}", file=sys.stderr)
    print("Top error fingerprints:", file=sys.stderr)
    for f, c in fp.most_common(8):
        print(f"  {c}x  {f}", file=sys.stderr)

    if args.strict_exit:
        if args.post:
            bad = [r for r in results if r["status"] != "posted"]
        else:
            bad = [r for r in results if r["status"] != "validated"]
        if bad:
            sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
