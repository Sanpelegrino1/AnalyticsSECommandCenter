# Visualization Format Patterns

Format configuration for Tableau Next visualizations. Applied via `style.encodings.fields.{key}.defaults.format` or `style.axis.fields.{key}.scale.format`. The semantic model does not support rich formatting; formats are set at the visualization layer.

**Structure:** `numberFormatInfo` with `type`, `decimalPlaces`, `prefix`, `suffix`, `displayUnits`, `includeThousandSeparator`, `negativeValuesFormat`.

---

## Format Types (Tableau Next API)

| `type` | Example Output | Use Case |
|--------|----------------|----------|
| `"Number"` | 1,234,567.89 | Standard numeric |
| `"NumberShort"` | 1.2M | Compact (axes, KPI cards) |
| `"Currency"` | $1,234,567.89 | Full currency (tooltips, tables) |
| `"CurrencyShort"` | $1.2M | Compact currency (axes) |
| `"Percent"` | 12.34% | Percentages, rates |

---

## Currency Formats

Use `type: "Currency"` or `"CurrencyShort"` with `prefix` for symbol. Default `type: "Currency"` uses locale; override with prefix for explicit symbol.

| Use Case | numberFormatInfo |
|----------|------------------|
| **Dollar** | `{"type": "Currency", "decimalPlaces": 2, "prefix": "$", "suffix": "", ...}` |
| **Euro** | `{"type": "Currency", "decimalPlaces": 2, "prefix": "€ ", "suffix": "", ...}` |
| **Pound** | `{"type": "Currency", "decimalPlaces": 2, "prefix": "£ ", "suffix": "", ...}` |
| **Yen** | `{"type": "Currency", "decimalPlaces": 0, "prefix": "¥ ", "suffix": "", ...}` |
| **Swiss Franc** | `{"type": "Currency", "decimalPlaces": 2, "prefix": "CHF ", "suffix": "", ...}` |
| **Generic (locale)** | `{"type": "Currency", "decimalPlaces": 2, "prefix": "", "suffix": "", ...}` |

**Base structure:**
```json
{
  "decimalPlaces": 2,
  "displayUnits": "Auto",
  "includeThousandSeparator": true,
  "negativeValuesFormat": "Auto",
  "prefix": "€ ",
  "suffix": "",
  "type": "Currency"
}
```

---

## Percentage Formats

| Use Case | decimalPlaces | Example |
|----------|---------------|---------|
| Integer % | 0 | 50% |
| One decimal | 1 | 50.5% |
| Two decimals | 2 | 50.55% |
| Variance (+/-) | 1 | +5.5% / -5.5% (negativeValuesFormat) |

```json
{"type": "Percent", "decimalPlaces": 1, "prefix": "", "suffix": "", ...}
```

---

## Numeric Formats

| Use Case | type | decimalPlaces | Example |
|----------|------|---------------|---------|
| Integer | Number | 0 | 1,234 |
| One decimal | Number | 1 | 1,234.5 |
| Two decimals | Number | 2 | 1,234.56 |
| Compact (K/M) | NumberShort | 2 | 1.2M |
| Thousands suffix | Number | 0 | 1K (use suffix " K" if needed) |

---

## Time Duration Formats

Use `type: "Number"` with `suffix` for unit. Apply to measures like days-to-close, contract duration.

| Use Case | suffix | decimalPlaces |
|----------|--------|---------------|
| Years | `" yr"` | 1 |
| Months | `" mo"` | 1 |
| Days | `" d"` | 0 |
| Hours | `" hr"` | 1 |
| Minutes | `" min"` | 0 |
| Seconds | `" s"` | 0 |

```json
{"type": "Number", "decimalPlaces": 1, "prefix": "", "suffix": " yr", ...}
```

---

## Where to Apply

| Location | Use |
|----------|-----|
| `style.encodings.fields.{F2}.defaults.format` | Tooltips, mark labels |
| `style.axis.fields.{F2}.scale.format` | Axis ticks (prefer CurrencyShort/NumberShort) |
| `style.headers.fields.{key}` | Table column headers |

**Critical:** Every measure in `marks.panes.encodings` needs an entry in `style.encodings.fields` with at least `{"defaults": {"format": {}}}`.

---

**Source:** Adapted from Lintao Linpack format patterns. Tableau Next uses `numberFormatInfo` JSON; Lintao used Desktop format strings (`c"€ "#,##0`). Custom prefix/suffix support may vary by Tableau Next version.
