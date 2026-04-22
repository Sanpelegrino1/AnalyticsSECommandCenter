# Troubleshooting Guide

> **Back to main skill:** [SKILL.md](SKILL.md)

When creating visualizations, these are the **most common errors** that cause API failures and how to fix them.

## Common API Errors

### Missing visualSpecification Fields

**Error:** `"Value required for [fonts]"` or `"Value required for [measureValues]"`

**Cause:** Incomplete visualSpecification structure.

**Fix:** Include ALL required visualSpecification fields:

```json
{
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "measureValues": [],        // REQUIRED (Vizql only — omit for Table)
    "referenceLines": {},       // REQUIRED (Vizql only — omit for Table)
    "forecasts": {},            // REQUIRED (Vizql only — omit for Table)
    // NOTE: "mode": "Visualization" is NOT valid — API returns JSON_PARSER_ERROR if included
    "marks": {...},
    "legends": {},
    "style": {
      "fit": "Entire",
      "fonts": {...},           // REQUIRED - 7 font definitions
      "lines": {...},           // REQUIRED - 4 line definitions
      "shading": {...},
      "headers": {...},         // REQUIRED (was allHeaders in v65.11)
      "fieldLabels": {...},
      "marks": {...},
      "showDataPlaceholder": false,
      "title": {"isVisible": true}
    }
  }
}
```

**Why so verbose?** Production Salesforce templates include ALL these fields. The API validates against the complete schema and will reject partial structures.

**Solution:** Always use templates from [templates-guide.md](templates-guide.md) or [chart-catalog.md](chart-catalog.md).

**Note:** The `generate_viz.py` script automatically adds encoding style entries for measures in encodings. If you encounter this error, ensure you're using the latest version of the script.

### style.marks.panes.range is Always Required

**Error:** `"Value required for [range]"`

**Cause:** Line and Scatter charts fail without `range` in `style.marks.panes`.

**Fix:** Every chart type needs it:

```json
"marks": {
  "panes": {
    "range": {"reverse": false}
  }
}
```

**Values:**
- Use `"reverse": true` for Bar/Donut/Funnel (category axis reads top-to-bottom)
- Use `"reverse": false` for Line/Scatter

### style.axis is Always Required — Even for Charts Without Axes

**Error:** `"Value required for [axis]"`

**Cause:** Donut fails without `style.axis`.

**Fix:** All chart types must include:

```json
"style": {
  "axis": {"fields": {}},
  ...
}
```

**Values:**
- For charts with visible axes (Bar, Line, Scatter): populate `axis.fields` with per-field scale/format config
- For Donut/Funnel: keep it as `{"fields": {}}`

**Critical:** The field config must be nested under a `"fields"` key — not directly under `"axis"`:

```python
# ❌ Wrong — causes "Unrecognized field F1" JSON_PARSER_ERROR
"axis": {"F1": {...}, "F2": {...}}

# ✅ Correct
"axis": {"fields": {"F1": {...}, "F2": {...}}}
```

Same applies to `style.encodings` — must be `{"fields": {"F1": {...}}}` not `{"F1": {...}}`.

### style.encodings.fields Only Accepts Measure Fields

**Error:** `"F3 field key in encodings is not valid. encodings can have only measure fields."`

**Cause:** Including dimension fields in `style.encodings.fields`.

**Rule:**
- ✅ Include fields where `role: "Measure"` in `style.encodings.fields`
- ❌ Never include `role: "Dimension"` fields — even if they appear as Color or Detail encodings

**Fix:**
```json
// ❌ Wrong — F3 is a Dimension (Detail encoding)
"encodings": {"fields": {"F1": {...}, "F2": {...}, "F3": {...}}}

// ✅ Correct — only measures
"encodings": {"fields": {"F1": {...}, "F2": {...}}}
```

### Table Viz: All Fields Must Use displayCategory "Discrete"

**Error:** `AnalyticsError: Axes are not supported in RowHeadersWidth mode` (browser render error, not API error)

**Cause:** Any field with `"displayCategory": "Continuous"` in a Table viz causes the renderer to initialize a continuous axis. Table mode (`fit: "RowHeadersWidth"`) bans axes entirely, so it crashes at render time — not at API creation time. The API accepts the payload, but the viz breaks when opened.

**Fix:** In Table vizzes, all fields — including measures — must use `"displayCategory": "Discrete"`. Do NOT use the standard `calc_measure()` helper (which always sets `"Continuous"`). Define table measures inline:

```python
# ❌ Wrong — triggers axis initialization at render time
"F3": calc_measure("My_Calc_clc", "Balance ($)")
# → {"type": "Field", "displayCategory": "Continuous", ...}

# ✅ Correct — no axis, renders cleanly in RowHeadersWidth mode
"F3": {"type": "Field", "fieldName": "My_Calc_clc", "function": "Sum",
       "role": "Measure", "displayCategory": "Discrete", "label": "Balance ($)"}
```

**Note:** Once fields are `"Discrete"`, they also require entries in `style.headers.fields` (see rule below). This is consistent — the API requires `headers.fields` for all discrete fields.

---

### style.headers.fields Only Accepts Dimension Fields on rows/columns

**Error:** `"F4 field key in headers.fields is not valid. headers.fields can have only discrete fields."`

**Cause:** Color-encoding and detail-encoding dimensions must NOT appear in `style.headers.fields`. Only dimensions explicitly placed on `rows` or `columns` belong there. Exception: in Table viz, measures with `"displayCategory": "Discrete"` are permitted and required.

**Fix:**
```json
// Funnel with F2 on rows, F4 as Color encoding
// ❌ Wrong — F4 is only used as Color, not a row/column dimension
"headers": {"fields": {"F2": {...}, "F4": {...}}}

// ✅ Correct — only the rows/columns dimension
"headers": {"fields": {"F2": {...}}}
```

### Dashboard widget.source Must Only Contain name

**Error:** `JSON_PARSER_ERROR`

**Cause:** The `source` object in a dashboard widget definition must only have `"name"`. Including `"label"` or `"type"` causes errors.

**Fix:**
```json
// ❌ Wrong
"source": {"name": "My_Viz", "label": "My Label", "type": "Visualization"}

// ✅ Correct
"source": {"name": "My_Viz"}
```

**Solution:** Always use dashboard patterns from [templates-guide.md](templates-guide.md).

### Encoding Field Styles Required

**Error:** `"encodings style is required for the <field> field."`

**Cause:** Any field with `role: "Measure"` or a `function` that appears in `marks.panes.encodings` **MUST** have an entry under `style.encodings.fields` — even a minimal one.

**Fix:**
```json
"style": {
  "encodings": {
    "fields": {
      "F2": {"defaults": {"format": {}}}  // Required for any measure in encodings
    }
  }
}
```

### Palette Schema Validation

**Error:** `"startToMiddleSteps isn't available with sequential palettes"` or similar palette errors

**Cause:** Palette step properties don't match palette type.

**Fix:**
- **Sequential palettes** (2 colors): only `startToEndSteps` is valid — remove `startToMiddleSteps`/`middleToEndSteps`
- **Diverging palettes** (3 colors, has `middle` key): only `startToMiddleSteps`/`middleToEndSteps` valid — remove `startToEndSteps`

## Field & Data Errors

### SDM Not Found

**Error:** `"Semantic model not found"` or `404 Not Found`

**Cause:** SDM API name is incorrect or doesn't exist.

**Fix:**
- Call list SDMs endpoint to see available models: `GET /services/data/v66.0/ssot/semantic/models`
- Check spelling of `apiName` (case-sensitive)
- Verify SDM is unlocked/available in your org

**Discovery:**
```bash
python scripts/discover_sdm.py --list
```

### KeyError: 'objectName' on Filters

**Error:** `KeyError: 'objectName'` when creating dashboard

**Cause:** Filter definitions in `viz_specs.json` are missing `objectName` because the field name doesn't exist in the SDM, or the enrichment process failed.

**Fix:**
- **Simplest:** Only include `fieldName` in filter definitions - the system will auto-enrich `objectName`, `dataType`, and `label` from the SDM
- If you see unresolved filter errors, check that field names match SDM `apiName` values exactly
- Run `discover_sdm.py --sdm <SDM_NAME> --json` to see available dimension fields
- The error message will list unresolved filters and suggest available fields

**Example:**
```json
{
  "filters": [
    {"fieldName": "Primary_Industry"}  // ✅ Correct - only fieldName needed
  ]
}
```

Not:
```json
{
  "filters": [
    {"fieldName": "Account_Industry"}  // ❌ Wrong - field doesn't exist, use "Primary_Industry"
  ]
}
```

### Field Not Found

**Error:** `"Field not found"` or field-related validation errors

**Cause:** Field reference is incorrect.

**Fix:**
- Re-check GET SDM definition response
- Verify `objectName` matches `semanticDataObjects[].apiName`
- Verify `fieldName` matches dimension/measure `apiName` or `fieldName`
- For calculated fields (`_clc`): `objectName` will be automatically set to `null` by enrichment

**Discovery:**
```bash
python scripts/discover_sdm.py --sdm {{SDM_NAME}} --json
```

### Calculated Field Function Mismatch

**Error:** Aggregation type errors with `_clc` fields

**Cause:** Using wrong `function` value for calculated measures.

**Fix:** Always read `aggregationType` from `semanticCalculatedMeasurements[]` in the SDM response:
- `aggregationType: "Sum"` → `"function": "Sum"`
- `aggregationType: "UserAgg"` → `"function": "UserAgg"`
- `aggregationType: "Min"` → `"function": "Min"`

**Never assume `"Sum"`** — always read it from the SDM.

## Authentication Errors

### Invalid Authentication

**Error:** `401 Unauthorized`

**Cause:** Bearer token is invalid or expired.

**Fix:**
- Ensure Bearer token is valid
- Check token has proper Tableau Next permissions
- Refresh token: `export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')`

**Quick check:**
```bash
echo $SF_TOKEN
echo $SF_INSTANCE
```

See [authentication.md](authentication.md) for complete auth setup.

## Dashboard Errors

### Dashboard Widget Not Showing

**Error:** Widget appears in JSON but not in UI

**Cause:** Common dashboard structure issues.

**Fix:**
- Verify visualization API name is correct (must match `name` from POST response)
- Check grid positioning doesn't overlap
- Ensure column + colspan ≤ 48
- Verify `style.widgetStyle` exists at dashboard level
- Verify `layouts[].style` exists with spacing
- Ensure widget has explicit `"name"` field matching its key

**Required structure:**
```json
{
  "style": {
    "widgetStyle": {
      "backgroundColor": "#ffffff",
      "borderColor": "#cccccc",
      "borderEdges": [],
      "borderRadius": 0,
      "borderWidth": 1
    }
  },
  "layouts": [{
    "style": {
      "backgroundColor": "#ffffff",
      "cellSpacingX": 4,
      "cellSpacingY": 4,
      "gutterColor": "#f3f3f3"
    }
  }]
}
```

### Empty/Blank Dashboard

**Error:** Dashboard POSTs successfully but appears blank

**Cause:** Missing required style fields.

**Fix:**
- Ensure `style.widgetStyle` exists at dashboard level
- Ensure `layouts[].style` exists with `cellSpacingX`, `cellSpacingY`, `gutterColor`
- Verify widgets have correct `source.name` format (no `id`, `label`, or `type`)

**Solution:** Always use dashboard patterns from [templates-guide.md](templates-guide.md).

## PATCH Update Errors

### PATCH Fails with Read-Only Field Errors

**Error:** `"Field is read-only"` or similar

**Cause:** PATCH payload includes read-only fields from GET response.

**Fix:** Before PATCHing, strip the following from the GET response:

**Top-level fields to remove:**
```
url, id, createdBy, createdDate, lastModifiedBy, lastModifiedDate, permissions, sourceVersion, workspaceIdOrApiName
```

**Nested fields to remove:**
- `dataSource.id`, `dataSource.url`
- `fields.{key}.id` (each field entry has a system-generated id)
- `view.id`, `view.url`, `view.isOriginal`

**Use `workspace` not `workspaceIdOrApiName`:**
```json
"workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"}
```

**Minimal valid PATCH payload structure:**
```json
{
  "name": "...",
  "label": "...",
  "dataSource": {"name": "...", "label": "...", "type": "SemanticModel"},
  "workspace": {"name": "...", "label": "..."},
  "fields": {"F1": {...}, "F2": {...}},
  "interactions": [],
  "view": {"label": "default", "name": "..._default", "viewSpecification": {...}},
  "visualSpecification": {...}
}
```

## Validation Checklist

Before POSTing, verify all required fields are present. This checklist covers every required field verified against production templates.

### Root Level Structure

- [ ] `name` - Visualization API name
- [ ] `label` - Display label
- [ ] `dataSource` - Object with `name`, `label`, `type`
- [ ] `workspace` - Object with `name`, `label`
- [ ] `interactions` - Array (can be empty `[]`)
- [ ] `fields` - Object with field definitions (F1, F2, etc.)
- [ ] `visualSpecification` - Complete specification object
- [ ] `view` - Object with `label`, `name`, `viewSpecification`

### visualSpecification Level

- [ ] `columns` - Array (can be empty `[]`)
- [ ] `rows` - Array (can be empty `[]`)
- [ ] `measureValues` - Array (can be empty `[]`)
- [ ] `mode` - String: `"Visualization"`
- [ ] `referenceLines` - Object (can be empty `{}`)
- [ ] `forecasts` - Object (can be empty `{}`)
- [ ] `marks` - Object with `fields`, `headers`, `panes`
- [ ] `legends` - Object (can be empty `{}`)
- [ ] `style` - Complete style object

### visualSpecification.style Level

**Required Top-Level Keys:**
- [ ] `fit` - String (e.g., `"Entire"`, `"Standard"`, `"RowHeadersWidth"`)
- [ ] `fonts` - Object with all 7 font definitions:
  - [ ] `actionableHeaders`
  - [ ] `axisTickLabels`
  - [ ] `fieldLabels`
  - [ ] `headers`
  - [ ] `legendLabels`
  - [ ] `markLabels`
  - [ ] `marks`
- [ ] `lines` - Object with all 4 line definitions:
  - [ ] `axisLine`
  - [ ] `fieldLabelDividerLine`
  - [ ] `separatorLine`
  - [ ] `zeroLine`
- [ ] `axis` - Object with `fields` sub-object
- [ ] `encodings` - Object with `fields` sub-object
- [ ] `headers` - Object with `columns`, `fields`, `rows`
- [ ] `fieldLabels` - Object with `columns` and `rows`
- [ ] `marks` - Object with `fields`, `headers`, `panes`
- [ ] `shading` - Object with `backgroundColor` and `banding`
- [ ] `referenceLines` - Object (can be empty `{}`)
- [ ] `showDataPlaceholder` - Boolean: `false`
- [ ] `title` - Object with `isVisible: true`

**Field-Specific Requirements:**

For each DIMENSION field (e.g., F1):
- [ ] Must appear in `style.headers.fields.F1` with `hiddenValues`, `isVisible`, `showMissingValues`

For each MEASURE field (e.g., F2):
- [ ] Must appear in `style.axis.fields.F2` with complete axis configuration
- [ ] Must appear in `style.encodings.fields.F2` with format configuration

**Marks Configuration:**
- [ ] `style.marks.panes.range` exists (even if empty `{"reverse": false}`)
- [ ] `style.marks.headers` exists with proper structure
- [ ] `style.marks.panes` exists with proper structure

**Dashboard-Specific (if creating dashboard):**
- [ ] Dashboard has `style.widgetStyle` and `layouts[].style`
- [ ] Dashboard widgets have `source.name` only (no `label` or `type`)

**Data Validation:**
- [ ] Field `function` matches SDM `aggregationType` for calculated fields
- [ ] Calculated fields use `objectName: null`
- [ ] Authentication token is valid

**Use validation script:**
```bash
python scripts/validate_viz.py viz.json
```

### Common Mistakes to Avoid

- ❌ **Empty `fields: {}` in headers** - Must have field-specific config for each dimension
- ❌ **Missing axis for measure fields** - Each measure needs axis config
- ❌ **Missing encodings for measure fields** - Each measure in encodings needs format config
- ❌ **Using `marks.ALL`** - Must use `marks.panes` + `marks.headers` (v66.8)
- ❌ **Using `style.allHeaders`** - Must use `style.headers` (v66.8)
- ❌ **Missing `layout` field** - Must include `layout: "Vizql"` or `"Table"` in visualSpecification

## Debugging Workflow

**1. Validate JSON before POST:**
```bash
python scripts/validate_viz.py viz.json
```

**2. POST to API:**
```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @viz.json
```

**3. If error occurs:**
- Read error message carefully (API provides specific field names)
- Check error against this troubleshooting guide
- Verify field references against SDM discovery
- Use templates to ensure proper structure

**4. For PATCH updates:**
- GET current visualization: `GET /services/data/v66.0/tableau/visualizations/{id}?minorVersion=8`
- Strip all read-only fields
- Make changes
- PATCH with cleaned payload

## Error Message Catalog

| Error Message | Section | Quick Fix |
|--------------|---------|-----------|
| `"Value required for [fonts]"` | Missing visualSpecification Fields | Include all 7 font definitions in `style.fonts` |
| `"Value required for [range]"` | style.marks.panes.range | Add `"range": {"reverse": false}` to `marks.panes` |
| `"Value required for [axis]"` | style.axis | Add `"axis": {"fields": {}}` to `style` |
| `"encodings can have only measure fields"` | style.encodings.fields | Remove dimension fields from `style.encodings.fields` |
| `"headers.fields can have only discrete fields"` | style.headers.fields | Remove color-encoding dimensions from `style.headers.fields` |
| `"encodings style is required for the <field> field"` | Encoding Field Styles | Add field entry to `style.encodings.fields` |
| `"startToMiddleSteps isn't available with sequential palettes"` | Palette Schema Validation | Remove `startToMiddleSteps` from 2-color palette |
| `JSON_PARSER_ERROR` (dashboard) | Dashboard widget.source | Remove `label` and `type` from `widget.source` |
| `401 Unauthorized` | Invalid Authentication | Refresh token: `sf org display --target-org $SF_ORG --json` |
| `"Semantic model not found"` | SDM Not Found | Verify SDM name with `discover_sdm.py --list` |
| `"Field not found"` | Field Not Found | Verify field name in SDM discovery response |

## Related Documentation

- [workflow.md](workflow.md) - Step-by-step dashboard creation process
- [templates-guide.md](templates-guide.md) - Templates that prevent these errors
- [scripts-guide.md](scripts-guide.md) - Validation scripts
- [chart-catalog.md](chart-catalog.md) - Complete JSON templates (includes quick start examples)

---

## Dashboard Layout — Common Problems

### Cards appear edge-to-edge with no outer margins

**Cause:** A widget spanning the full 72-column grid (e.g. `colspan=72`, starting at col 1) renders with no outer margin. Other rows with multiple widgets get `cellSpacingX` applied as gaps between widgets, so they appear narrower.

**Fix:** Reserve col 1 and col 72 as empty margin gutters. Run **all content through cols 2–71** (`colspan=70` max for a full-width widget).

```python
# Wrong — goes edge to edge:
page_cells.append(dash_pos("container_filters", 1, 1, 72, 3))

# Correct — consistent outer margins:
page_cells.append(dash_pos("container_filters", 2, 1, 70, 3))
```

### Card borders not showing (cards blend into page background)

**Cause:** `"borderEdges": []` explicitly suppresses all borders. Setting `borderColor` and `borderWidth` has no effect when `borderEdges` is empty.

**Fix:** Set `borderEdges` to include all four sides:

```python
_BORDER_EDGES = ["Top", "Right", "Bottom", "Left"]

# In any widget that should look like a card:
"widgetStyle": {
    "backgroundColor": "#FFFFFF",
    "borderColor": "#DDDBDA",
    "borderEdges": ["Top", "Right", "Bottom", "Left"],
    "borderRadius": 8,
    "borderWidth": 1
}
```

Also ensure page background is `#F4F6F9` (SF gray), not white — white cards on a white page are invisible.

### Toggle filter buttons overflow horizontally (horizontal scroll appears)

**Cause:** Toggle filters with 5+ values don't have enough room to display all buttons inline.

**Fix:** Only use `dash_toggle_filter` for fields with **≤4 distinct values** (e.g. Segment: Commercial/Corporate/Middle Market/Small Business = 4). Switch to `dash_list_filter` for fields with 5+ values (Region with 5 regions, Industry, RM Name, etc.).

### Text label above a viz has a scrollbar / too much whitespace below it

**Cause:** Text widgets render from the top of their grid cell downward. There is no vertical alignment property in the Tableau Next text widget API. If the cell is too tall, there's dead space below the text.

**Fix option A:** Reduce the text widget's rowspan to 2 rows (tight but no scrollbar).
**Fix option B:** Use the container pattern — place a `dash_container` as background, put `dash_text_inner` (3 rows) and `dash_viz_inner` at overlapping grid positions. The title sits at the top of the card naturally.

### Unified card (title + description + chart as one card)

Use three overlapping widgets at the same column range:

```python
# 1. Container — background card with border (spans all rows)
widgets["container_trend"] = dash_container("container_trend")
page_cells.append(dash_pos("container_trend", 2, 10, 45, 13))  # 13 rows total

# 2. Text inner — title + description, no border, white bg (top 3 rows)
widgets["label_trend"] = dash_text_inner("label_trend", "Balance Trend",
    description="Aggregate deposit balance across all clients over the selected period.")
page_cells.append(dash_pos("label_trend", 2, 10, 45, 3))

# 3. Viz inner — chart, no border, white bg (bottom 10 rows)
widgets["visualization_1"] = dash_viz_inner("visualization_1", viz_api, viz_id)
page_cells.append(dash_pos("visualization_1", 2, 13, 45, 10))
```

The container renders behind the text and viz, providing one unified bordered card.
