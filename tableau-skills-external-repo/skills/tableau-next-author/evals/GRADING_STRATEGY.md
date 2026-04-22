# Viz creation evals: triage and grading

Use this after the eval runner produces `results.jsonl` and optional files under `evals/runs/<run_id>/`.

Run from **repo root** (`tableau-next-author/`):

`python scripts/run_viz_creation_evals.py --manifest evals/viz_creation_eval_manifest.json`

Or from **`skills/tableau-next-author/`**: same command (paths are relative to that directory).

## Failure buckets

| Status | Phase | Likely cause |
|--------|--------|----------------|
| `discover_failed` | discover | Wrong SDM API name, auth, or org |
| `field_match_failed` | match | SDM lacks required roles/types for the template (e.g. no lat/lon for Map) |
| `build_failed` | build | Template builder bug or unexpected SDM field shape |
| `validation_failed` | validate | Payload does not satisfy `validators.py` (fix templates or validators) |
| `post_failed` | post | API rejected JSON at `minorVersion=12` (schema drift, workspace, limits) |
| `skipped` | match | Unknown template name in manifest/filter |

## Artifacts

- `viz_<case_id>.json` — exact POST body (or attempted body).
- `field_mappings_<case_id>.json` — auto-match result for replay.
- `request_meta_<case_id>.json` — workspace, SDM, template, status (no tokens).

Payloads may contain field API names; do not treat as public.

## Model-as-judge prompt (optional)

```markdown
You are reviewing Tableau Next visualization eval failures at API v66.0 minor 12.

For each JSONL row with status other than `posted` or `validated`:
1. Classify: SDM mismatch vs template bug vs validator vs API schema.
2. List strengths of the payload (what is already correct).
3. List weaknesses and the smallest fix (file or template area).
4. Priority P1/P2/P3.

Row:
{{paste one JSON line}}

If artifact_paths.viz exists, consider the structure of that JSON.
```

## Strengths-first scoring (human or LLM)

Ask for strengths and weaknesses before a numeric score so ratings do not collapse to the middle.
