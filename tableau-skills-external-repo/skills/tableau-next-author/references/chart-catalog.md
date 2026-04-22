# Tableau Next Chart Catalog

Most **Vizql** templates below were extracted from real production packages. **Map** and **Flow** layouts use a different `visualSpecification` shape than Vizql (no top-level `measureValues` / `columns` / `rows` on those layouts).

**POST endpoint:** `POST /services/data/v66.0/tableau/visualizations?minorVersion=12`

---

## Quick Start Examples

These are minimal working examples for the most common chart types. For complete templates with all features, see the sections below.

**IMPORTANT:** **Vizql** visualizations require `measureValues`, `mode`, `referenceLines`, `forecasts`, and a full `style` object (`fonts`, `lines`, etc.). **Map** and **Flow** omit those top-level keys; use the sections below instead.

### Simple Bar Chart

```json
{
  "name": "Simple_Bar_Chart",
  "label": "Simple Bar Chart",
  "dataSource": {
    "name": "C360SemanticModel_c360_unlocked",
    "label": "C360 Semantic Model",
    "type": "SemanticModel"
  },
  "workspace": {
    "name": "Sales_Analytics_Workspace",
    "label": "Sales Analytics"
  },
  "interactions": [],
  "fields": {
    "F1": {
      "type": "Field",
      "displayCategory": "Discrete",
      "role": "Dimension",
      "objectName": "Opportunity",
      "fieldName": "Opportunity_Stage"
    },
    "F2": {
      "type": "Field",
      "displayCategory": "Continuous",
      "role": "Measure",
      "objectName": "Opportunity",
      "fieldName": "Total_Amount",
      "function": "Sum"
    }
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "measureValues": [],
    "mode": "Visualization",
    "referenceLines": {},
    "forecasts": {},
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "legends": {},
    "style": {
      "axis": {
        "fields": {
          "F2": {
            "isVisible": true,
            "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "",
                  "suffix": "",
                  "type": "Number"
                }
              }
            },
            "ticks": {
              "majorTicks": {"type": "Auto"},
              "minorTicks": {"type": "Auto"}
            }
          }
        }
      },
      "encodings": {
        "fields": {
          "F2": {
            "defaults": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "",
                  "suffix": "",
                  "type": "Number"
                }
              }
            }
          }
        }
      },
      "fieldLabels": {
        "columns": {"showDividerLine": false, "showLabels": true},
        "rows": {"showDividerLine": false, "showLabels": true}
      },
      "fit": "Entire",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13},
        "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13},
        "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13},
        "markLabels": {"color": "#2E2E2E", "size": 13},
        "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {
          "F1": {
            "hiddenValues": [],
            "isVisible": true,
            "showMissingValues": false
          }
        },
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {
        "axisLine": {"color": "#C9C9C9"},
        "fieldLabelDividerLine": {"color": "#C9C9C9"},
        "separatorLine": {"color": "#C9C9C9"},
        "zeroLine": {"color": "#C9C9C9"}
      },
      "marks": {
        "fields": {},
        "headers": {
          "color": {"color": ""},
          "isAutomaticSize": true,
          "label": {
            "canOverlapLabels": false,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": false
          }
        },
        "panes": {
          "color": {"color": ""},
          "isAutomaticSize": true,
          "label": {
            "canOverlapLabels": false,
            "marksToLabel": {"type": "All"},
            "showMarkLabels": false
          },
          "range": {"reverse": false},
          "size": {"isAutomatic": true, "type": "Percentage", "value": 75}
        }
      },
      "referenceLines": {},
      "shading": {
        "backgroundColor": "#FFFFFF",
        "banding": {"rows": {"color": "#E5E5E5"}}
      },
      "showDataPlaceholder": false,
      "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default",
    "name": "Simple_Bar_Chart_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {},
        "rows": []
      }
    }
  }
}
```

### Simple Line Chart

```json
{
  "name": "Simple_Line_Chart",
  "label": "Revenue Trend",
  "dataSource": {
    "name": "C360SemanticModel_c360_unlocked",
    "label": "C360 Semantic Model",
    "type": "SemanticModel"
  },
  "workspace": {
    "name": "Sales_Analytics_Workspace",
    "label": "Sales Analytics"
  },
  "interactions": [],
  "fields": {
    "F1": {
      "type": "Field",
      "displayCategory": "Discrete",
      "role": "Dimension",
      "objectName": "Opportunity",
      "fieldName": "Opportunity_Close_Date",
      "function": "DatePartMonth"
    },
    "F2": {
      "type": "Field",
      "displayCategory": "Continuous",
      "role": "Measure",
      "objectName": "Opportunity",
      "fieldName": "Total_Amount",
      "function": "Sum"
    }
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {},
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Line",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "fit": "Entire",
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {"color": {"color": ""}, "isAutomaticSize": false, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}, "size": {"isAutomatic": false, "type": "Pixel", "value": 3}}
      }
    }
  },
  "view": {
    "label": "default",
    "name": "Simple_Line_Chart_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {},
        "rows": []
      }
    }
  }
}
```

### Simple Donut Chart

```json
{
  "name": "Simple_Donut_Chart",
  "label": "Win Rate Distribution",
  "dataSource": {
    "name": "C360SemanticModel_c360_unlocked",
    "label": "C360 Semantic Model",
    "type": "SemanticModel"
  },
  "workspace": {
    "name": "Sales_Analytics_Workspace",
    "label": "Sales Analytics"
  },
  "interactions": [],
  "fields": {
    "F1": {
      "type": "Field",
      "displayCategory": "Continuous",
      "role": "Measure",
      "objectName": "Opportunity",
      "fieldName": "Total_Amount",
      "function": "Sum"
    },
    "F2": {
      "type": "Field",
      "displayCategory": "Discrete",
      "role": "Dimension",
      "objectName": "Opportunity",
      "fieldName": "Opportunity_Stage"
    }
  },
  "visualSpecification": {
    "columns": [],
    "rows": [],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {
      "F2": {
        "isVisible": true,
        "position": "Right",
        "title": {"isVisible": true}
      }
    },
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F1", "type": "Angle"},
          {"fieldKey": "F2", "type": "Color"}
        ],
        "isAutomatic": false,
        "type": "Donut",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "encodings": {
        "fields": {
          "F1": {"defaults": {"format": {}}},
          "F2": {"defaults": {"format": {}}}
        }
      },
      "fit": "Entire",
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""},
          "isAutomaticSize": true,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true},
          "size": {"isAutomatic": true, "type": "Percentage", "value": 80}
        }
      }
    }
  },
  "view": {
    "label": "default",
    "name": "Simple_Donut_Chart_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {},
        "rows": []
      }
    }
  }
}
```

### Testing Quick Start Examples

```bash
# 1. Set up authentication
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')

# 2. Create a workspace first (if needed)
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/tableau/workspaces" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Sales_Analytics_Workspace", "label": "Sales Analytics"}'

# 3. Create visualization
curl -X POST \
  "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=12" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @bar_chart.json
```

---

## Required Root Structure (All Charts)

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {...},
  "visualSpecification": {...},
  "view": {
    "label": "default",
    "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {"columns": [], "fields": {}, "rows": []}
    }
  }
}
```

## Encoding Types (marks.panes.encodings)

| Type | Effect |
|------|--------|
| `"Color"` | Colors marks by field value |
| `"Label"` | Shows field value as label on mark |
| `"Angle"` | Controls slice size (Donut only) |
| `"Size"` | Scales mark size by measure value |
| `"Detail"` | Breaks aggregation to individual points (Scatter) |

## All Mark Types

| Chart | `marks.panes.type` | `layout` | Key Pattern |
|-------|-------------------|----------|-------------|
| Bar (stacked/grouped) | `"Bar"` | `"Vizql"` | Color encoding = stack by color |
| Funnel | `"Bar"` | `"Vizql"` | `isStackingAxisCentered: true` + `connector.type: "Origami"` |
| Heatmap | `"Bar"` | `"Vizql"` | 2 dims + Continuous color palette |
| Line | `"Line"` | `"Vizql"` | Date dim in columns |
| Donut | `"Donut"` | `"Vizql"` | Angle + Color encodings |
| Table | `"Text"` | `"Table"` | All fields in rows |
| Scatter | `"Circle"` | `"Vizql"` | 2 measures + Detail encoding |
| Dot Matrix | `"Circle"` | `"Vizql"` | 2 dims + Color + Size encodings |

---

## 1. Stacked Bar (Vertical) — Color by Dimension

**Use For:** Revenue by Product, stacked by Region

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Discrete", "fieldName": "{{X_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F2": {"displayCategory": "Discrete", "fieldName": "{{COLOR_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F3": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F4": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F3"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {
      "F2": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}
    },
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F2", "type": "Color"},
          {"fieldKey": "F4", "type": "Label"}
        ],
        "isAutomatic": false,
        "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {
        "fields": {
          "F3": {
            "isVisible": true, "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "CurrencyShort"}}},
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}
          }
        }
      },
      "encodings": {
        "fields": {
          "F3": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}},
          "F4": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Entire",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {"F1": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}},
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": true, "isStackingAxisCentered": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true}, "size": {"isAutomatic": true, "type": "Percentage", "value": 75}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "showDataPlaceholder": false,
      "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**Key:** F3 and F4 reference the same measure — F3 drives the bar height, F4 drives the Label on each segment.

---

## 2. Bar (Horizontal, Ranked) with Reference Line

**Use For:** Revenue by Region sorted top-to-bottom, with an average line

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Discrete", "fieldName": "{{DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F2": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F3": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F6": {"displayCategory": "Discrete", "fieldName": "{{DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F8": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {
      "F6": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}
    },
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F3", "type": "Label"},
          {"fieldKey": "F6", "type": "Color"}
        ],
        "isAutomatic": false, "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "measureValues": [],
    "referenceLines": {
      "RL1": {
        "fieldKey": "F2",
        "line": {
          "bandFill": {"color": "", "opacity": 0.3},
          "color": "#FF0000",
          "opacity": 1,
          "style": "Solid",
          "thickness": 2
        },
        "type": "Average",
        "label": {
          "isVisible": true,
          "text": "Average"
        }
      }
    },
    "style": {
      "axis": {
        "fields": {
          "F2": {
            "isVisible": true, "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "CurrencyShort"}}},
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}
          }
        }
      },
      "encodings": {
        "fields": {
          "F2": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}},
          "F3": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Entire",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {"F1": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}},
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": true, "isStackingAxisCentered": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true}, "size": {"isAutomatic": true, "type": "Percentage", "value": 75}
        }
      },
      "referenceLines": {
        "RL1": {"color": "#FF0000", "label": {"isVisible": true}}
      },
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {"F1": {"byField": "F8", "order": "Descending", "type": "Nested"}},
        "rows": []
      }
    }
  }
}
```

**Key differences from simple bar:**
- `referenceLines.RL1` in both `visualSpecification` (definition) and `style` (appearance)
- Sort `type: "Nested"` for dimension sorted by measure
- F2, F3, F8 all reference same measure — F2 = axis, F3 = label, F8 = sort anchor

---

## 3. Side-by-Side Bar (Multi-Measure) — MeasureValues Pattern

**Use For:** Comparing 2+ measures side by side per category (Revenue vs Pipeline by Region)

This uses the special `MeasureValues` / `MeasureNames` field types.

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Continuous", "role": "Measure", "type": "MeasureValues"},
    "F2": {"displayCategory": "Discrete", "role": "Dimension", "type": "MeasureNames"},
    "F3": {"displayCategory": "Discrete", "role": "Dimension", "type": "MeasureNames"},
    "F4": {"displayCategory": "Continuous", "role": "Measure", "type": "MeasureValues"},
    "F6": {"displayCategory": "Continuous", "fieldName": "{{MEASURE_1}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F8": {"displayCategory": "Continuous", "fieldName": "{{MEASURE_2}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F2"],
    "rows": ["F1"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {
      "F3": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}
    },
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F3", "type": "Color"},
          {"fieldKey": "F4", "type": "Label"}
        ],
        "isAutomatic": false, "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "measureValues": ["F8", "F6"],
    "referenceLines": {},
    "style": {
      "axis": {
        "fields": {
          "F1": {
            "isVisible": true, "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "NumberShort"}}},
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}
          }
        }
      },
      "encodings": {
        "fields": {
          "F1": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}}},
          "F4": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}}},
          "F6": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}},
          "F8": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Standard",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {"F2": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}},
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": true, "isStackingAxisCentered": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true}, "size": {"isAutomatic": true, "type": "Percentage", "value": 75}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**MeasureValues pattern:**
- `F1`: `type: "MeasureValues"` — the combined value axis
- `F2`/`F3`: `type: "MeasureNames"` — the measure name dimension (shows in columns + color)
- `F4`: `type: "MeasureValues"` — for label encoding
- `F6`, `F8`: the actual measure fields
- `measureValues: ["F8", "F6"]` — lists which real fields contribute

---

## 4. Funnel

**Use For:** Sales pipeline stages, conversion funnels

Same as a stacked bar but with `isStackingAxisCentered: true` and `connector.type: "Origami"`.

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F2": {"displayCategory": "Discrete", "fieldName": "{{STAGE_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F3": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {},
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [],
        "isAutomatic": false, "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {
        "fields": {
          "F1": {
            "isVisible": true, "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "CurrencyShort"}}},
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}
          }
        }
      },
      "encodings": {
        "fields": {
          "F1": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Entire",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {"F2": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}},
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""},
          "connector": {"type": "Origami"},
          "isAutomaticSize": true,
          "isStackingAxisCentered": true,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false},
          "range": {"reverse": true},
          "size": {"isAutomatic": true, "type": "Percentage", "value": 75}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**Funnel keys:** `style.marks.panes.isStackingAxisCentered: true` + `connector: {"type": "Origami"}`

**To add Color encoding to a Funnel** (e.g., color by Account Type):
1. Add a Dimension field for color: `"F4": {"displayCategory": "Discrete", "fieldName": "Account_Type", "objectName": "Account_TAB_Sales_Cloud", "role": "Dimension", "type": "Field"}`
2. Add to `visualSpecification.legends`: `"F4": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}`
3. Add to `marks.panes.encodings`: `{"fieldKey": "F4", "type": "Color"}`
4. Do NOT add F4 to `style.headers.fields` — only dimensions on `rows`/`columns` go there
5. Do NOT add F4 to `style.encodings.fields` — only measure fields go there

---

## 5. Heatmap

**Use For:** Revenue by Product × Region grid with color intensity

Bar chart with 2 dimensions and a continuous color gradient.

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Discrete", "fieldName": "{{X_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F2": {"displayCategory": "Discrete", "fieldName": "{{Y_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F3": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F4": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {
      "F3": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}
    },
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F3", "type": "Color"},
          {"fieldKey": "F4", "type": "Label"}
        ],
        "isAutomatic": false, "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {"fields": {}},
      "encodings": {
        "fields": {
          "F3": {
            "colors": {
              "palette": {
                "end": "#FF906E",
                "start": "#5867E8",
                "startToEndSteps": []
              },
              "type": "Continuous"
            },
            "defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}
          },
          "F4": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Standard",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {
          "F1": {"hiddenValues": [], "isVisible": true, "showMissingValues": false},
          "F2": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}
        },
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": true, "isStackingAxisCentered": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true},
          "size": {"isAutomatic": true, "type": "Percentage", "value": 100}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**Heatmap keys:**
- `colors.type: "Continuous"` — gradient instead of discrete colors
- `colors.palette.start`/`end` with `startToEndSteps: []` — sequential 2-color gradient
- `size.value: 100` — bars fill full cell width (no gaps)

---

## 6. Line (Continuous — with Color and Labels)

**Use For:** Revenue trend over time with value labels on each point

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Discrete", "fieldName": "{{DATE_FIELD}}", "function": "DatePartMonth", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F2": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F3": {"displayCategory": "Discrete", "fieldName": "{{COLOR_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F4": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {
      "F3": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}
    },
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F3", "type": "Color"},
          {"fieldKey": "F4", "type": "Label"}
        ],
        "isAutomatic": false, "type": "Line",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {
        "fields": {
          "F2": {
            "isVisible": true, "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "CurrencyShort"}}},
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}
          }
        }
      },
      "encodings": {
        "fields": {
          "F2": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}},
          "F4": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Entire",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {"F1": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}},
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": false},
          "size": {"isAutomatic": false, "type": "Pixel", "value": 3}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**For Line Discrete (Year + Month hierarchy):** Put two date dims in columns:
```json
"columns": ["F1", "F3"]
```
Where F1 = `DatePartYear`, F3 = `DatePartMonth` — creates Year / Month header hierarchy.

---

## 7. Donut

**Use For:** Open Pipeline by Region, Market Share

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Discrete", "fieldName": "{{DIMENSION}}", "label": "{{DIM_LABEL}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F2": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F3": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F4": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": [],
    "rows": [],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {"F1": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}},
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F1", "type": "Color"},
          {"fieldKey": "F2", "type": "Angle"},
          {"fieldKey": "F3", "type": "Label"},
          {"fieldKey": "F4", "type": "Label"}
        ],
        "isAutomatic": false, "type": "Donut",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {"fields": {}},
      "encodings": {
        "fields": {
          "F2": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "NumberShort"}}}},
          "F3": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "NumberShort"}}}},
          "F4": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "NumberShort"}}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Entire",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {"columns": {"mergeRepeatedCells": true, "showIndex": false}, "fields": {}, "rows": {"mergeRepeatedCells": true, "showIndex": false}},
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": true,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true}, "size": {"isAutomatic": true, "type": "Percentage", "value": 80}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {"columns": [], "fields": {"F1": {"byField": "F2", "order": "Descending", "type": "Field"}}, "rows": []}
    }
  }
}
```

**Two Label encodings** (F3, F4) can show different formats — e.g. one absolute value, one percentage.

---

## 8. Table

**Use For:** Campaign details, Opportunity list, Employee roster

> **IMPORTANT:** Tables use `marks.panes.type: "Text"` (NOT `"Circle"`), and `fit: "RowHeadersWidth"`.

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Discrete", "fieldName": "{{ID_FIELD}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F2": {"displayCategory": "Discrete", "fieldName": "{{NAME_FIELD}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F3": {"displayCategory": "Discrete", "fieldName": "{{MEASURE_1}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F4": {"displayCategory": "Discrete", "fieldName": "{{MEASURE_2}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F5": {"displayCategory": "Discrete", "fieldName": "{{DIMENSION_2}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"}
  },
  "visualSpecification": {
    "layout": "Table",
    "legends": {},
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [],
        "isAutomatic": false,
        "type": "Text",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "rows": ["F1", "F2", "F3", "F4", "F5"],
    "style": {
      "encodings": {
        "fields": {
          "F3": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}}},
          "F4": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}}}
        }
      },
      "fieldLabels": {
        "columns": {"backgroundColor": "#E5E5E5", "showDividerLine": false, "showLabels": true},
        "rows": {"backgroundColor": "#E5E5E5", "showDividerLine": false, "showLabels": true}
      },
      "fit": "RowHeadersWidth",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 12}, "axisTickLabels": {"color": "#2E2E2E", "size": 12},
        "fieldLabels": {"color": "#2E2E2E", "size": 12}, "grandTotalLabel": {"color": "#2E2E2E", "size": 12},
        "grandTotalValues": {"color": "#2E2E2E", "size": 12}, "headers": {"color": "#2E2E2E", "size": 12},
        "legendLabels": {"color": "#2E2E2E", "size": 12}, "markLabels": {"color": "#2E2E2E", "size": 12}, "marks": {"color": "#2E2E2E", "size": 12}
      },
      "grandTotals": {"rows": {"position": "Start"}},
      "headers": {
        "columns": {"mergeRepeatedCells": false, "showIndex": false},
        "fields": {
          "F1": {"hiddenValues": [], "isVisible": true, "showMissingValues": false},
          "F2": {"hiddenValues": [], "isVisible": true, "showMissingValues": false},
          "F3": {
            "defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Currency"}}},
            "hiddenValues": [], "isVisible": true, "showMissingValues": false
          },
          "F4": {
            "defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}},
            "hiddenValues": [], "isVisible": true, "showMissingValues": false
          },
          "F5": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}
        },
        "rows": {"mergeRepeatedCells": false, "showIndex": true}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}, "range": {"reverse": true}, "size": {"isAutomatic": true, "type": "Pixel", "value": 12}}
      },
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**Table differences from charts:**
- `marks.panes.type: "Text"` (NOT "Circle")
- `layout: "Table"` (no `columns`, `forecasts`, `measureValues`, `referenceLines` at top level)
- `fit: "RowHeadersWidth"`
- `headers.rows.showIndex: true` (shows row numbers)
- `headers.fields.{key}` includes format config for measure columns
- Extra fonts: `grandTotalLabel`, `grandTotalValues`
- `grandTotals: {rows: {position: "Start"}}`

---

## 9. Scatter Plot (with Detail encoding)

**Use For:** Deal Size vs Sales Cycle Days, colored by Stage — individual data points

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Continuous", "fieldName": "{{X_MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F2": {"displayCategory": "Continuous", "fieldName": "{{Y_MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F3": {"displayCategory": "Discrete", "fieldName": "{{DETAIL_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F5": {"displayCategory": "Discrete", "fieldName": "{{COLOR_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {"F5": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}},
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F3", "type": "Detail"},
          {"fieldKey": "F5", "type": "Color"}
        ],
        "isAutomatic": false, "type": "Circle",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {
        "fields": {
          "F1": {
            "isVisible": true, "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "CurrencyShort"}}},
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}
          },
          "F2": {
            "isVisible": true, "isZeroLineVisible": true,
            "range": {"includeZero": true, "type": "Auto"},
            "scale": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "NumberShort"}}},
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}}
          }
        }
      },
      "encodings": {
        "fields": {
          "F1": {"defaults": {"format": {}}},
          "F2": {"defaults": {"format": {}}}
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Standard",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {"columns": {"mergeRepeatedCells": true, "showIndex": false}, "fields": {}, "rows": {"mergeRepeatedCells": true, "showIndex": false}},
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false},
          "range": {"reverse": false},
          "size": {"isAutomatic": false, "type": "Pixel", "value": 10}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**`Detail` encoding** breaks aggregation — each row becomes its own point. Without it, all values aggregate to a single dot.

**`style.encodings.fields`** only includes measure fields F1 and F2 — dimension fields F3 (Detail) and F5 (Color) must NOT appear here or the API returns `"encodings can have only measure fields"`.

---

## 10. Dot Matrix

**Use For:** Win Rate by Product × Region — circle size = magnitude, color = intensity

```json
{
  "name": "{{VIZ_API_NAME}}",
  "label": "{{VIZ_LABEL}}",
  "dataSource": {"name": "{{SDM_API_NAME}}", "label": "{{SDM_LABEL}}", "type": "SemanticModel"},
  "workspace": {"name": "{{WORKSPACE_API_NAME}}", "label": "{{WORKSPACE_LABEL}}"},
  "interactions": [],
  "fields": {
    "F1": {"displayCategory": "Discrete", "fieldName": "{{X_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F2": {"displayCategory": "Discrete", "fieldName": "{{Y_DIMENSION}}", "objectName": "{{OBJECT}}", "role": "Dimension", "type": "Field"},
    "F3": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Avg", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"},
    "F4": {"displayCategory": "Continuous", "fieldName": "{{MEASURE}}", "function": "Sum", "objectName": "{{OBJECT}}", "role": "Measure", "type": "Field"}
  },
  "visualSpecification": {
    "columns": ["F1"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {"F3": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}},
    "marks": {
      "fields": {},
      "headers": {"encodings": [], "isAutomatic": true, "type": "Text"},
      "panes": {
        "encodings": [
          {"fieldKey": "F3", "type": "Color"},
          {"fieldKey": "F4", "type": "Size"}
        ],
        "isAutomatic": false, "type": "Circle",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {"fields": {}},
      "encodings": {
        "fields": {
          "F3": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}}},
          "F4": {
            "defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 2, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}},
            "isAutomaticSize": false,
            "size": {"isAutomatic": true, "max": 80, "min": 20, "type": "Percentage"}
          }
        }
      },
      "fieldLabels": {"columns": {"showDividerLine": false, "showLabels": true}, "rows": {"showDividerLine": false, "showLabels": true}},
      "fit": "Entire",
      "fonts": {
        "actionableHeaders": {"color": "#0250D9", "size": 13}, "axisTickLabels": {"color": "#2E2E2E", "size": 13},
        "fieldLabels": {"color": "#2E2E2E", "size": 13}, "headers": {"color": "#2E2E2E", "size": 13},
        "legendLabels": {"color": "#2E2E2E", "size": 13}, "markLabels": {"color": "#2E2E2E", "size": 13}, "marks": {"color": "#2E2E2E", "size": 13}
      },
      "headers": {
        "columns": {"mergeRepeatedCells": true, "showIndex": false},
        "fields": {
          "F1": {"hiddenValues": [], "isVisible": true, "showMissingValues": false},
          "F2": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}
        },
        "rows": {"mergeRepeatedCells": true, "showIndex": false}
      },
      "lines": {"axisLine": {"color": "#C9C9C9"}, "fieldLabelDividerLine": {"color": "#C9C9C9"}, "separatorLine": {"color": "#C9C9C9"}, "zeroLine": {"color": "#C9C9C9"}},
      "marks": {
        "fields": {},
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {
          "color": {"color": ""}, "isAutomaticSize": false, "isStackingAxisCentered": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false},
          "range": {"reverse": true},
          "size": {"isAutomatic": false, "type": "Pixel", "value": 111}
        }
      },
      "referenceLines": {},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "showDataPlaceholder": false, "title": {"isVisible": true}
    }
  },
  "view": {
    "label": "default", "name": "{{VIZ_API_NAME}}_default",
    "viewSpecification": {"filters": [], "sortOrders": {"columns": [], "fields": {}, "rows": []}}
  }
}
```

**Dot Matrix keys:**
- F3 (Avg) → Color encoding — shows intensity
- F4 (Sum) → Size encoding — `encodings.fields.F4.size: {isAutomatic: true, max: 80, min: 20, type: "Percentage"}` controls size range

---

## Map (layout: `Map`)

**Common shape:** `visualSpecification.layout` = `"Map"`, `locations` = field keys for `MapPosition` (usually `["F1"]`). One field uses `type: "MapPosition"` with `positional.type` = `"Xy"` and `latitudeOrY` / `longitudeOrX` (`fieldName` + `objectName`). `style.axis` is not used.

**Basemap:** Current exports use `style.background`: `{"type": "Map", "styleName": "light"}`. Older samples used `{"type": "Map", "style": {"type": "Name", "value": "light"}}` — both are valid in the wild; the skill builder emits `styleName` by default.

### Map variants (from real packages)

| Pattern | Template | Fields | `marks.panes.type` | `panes.encodings` | Legends |
|--------|----------|--------|-------------------|-------------------|---------|
| Location only | `geomap_location_only` | F1 MapPosition only | Circle (default) | `[]` | `{}` |
| Styled points, no measure | — (manual / UI) | F1 only | Circle or Square | `[]` | `{}` — color/size in `style.marks.panes` only |
| Text + dimension label | — (manual / UI) | F1 + label dim | Text | Label(dim) | `{}` |
| Measure Color + dim Label | `geomap_points` | F1 + measure + label dim | Circle | Color(M), Label(D) | Color measure |
| Advanced Color + Size + labels | `geomap_advanced` | F1 + dim + **3× same measure** (F3 Color, F4 Label, F5 Size) | Circle | Label(D), Color(M), Label(M), Size(M) | Often `F3` legend hidden |

**Mark types:** Maps use **`Circle`**, **`Square`**, or **`Text`** in `marks.panes.type` (all supported by the validator). **`geomap_location_only`** / **`geomap_points`** / **`geomap_advanced`** default to **Circle**; use package JSON or overrides for Square/Text.

**Advanced map:** The same SDM measure is duplicated as three fields (F3/F4/F5) so the API can bind **Color**, **Label** (measure value), and **Size** independently — same pattern as duplicating measures elsewhere. Color may use a **diverging** palette (`middle` + `start`/`end`).

### Reference: `geomap_points` (measure + label)

```json
{
  "fields": {
    "F1": {
      "type": "MapPosition",
      "displayCategory": "Continuous",
      "positionName": "Store Location",
      "positional": {
        "latitudeOrY": {"fieldName": "Latitude", "objectName": "Store_Home"},
        "longitudeOrX": {"fieldName": "Longitude", "objectName": "Store_Home"},
        "type": "Xy"
      },
      "role": "Dimension"
    },
    "F2": {
      "displayCategory": "Continuous",
      "fieldName": "Total_Amount_clc",
      "function": "UserAgg",
      "role": "Measure",
      "type": "Field"
    },
    "F3": {
      "displayCategory": "Discrete",
      "fieldName": "Store_Name",
      "objectName": "Store_Home",
      "role": "Dimension",
      "type": "Field"
    }
  },
  "visualSpecification": {
    "layout": "Map",
    "legends": {
      "F2": {"isVisible": true, "position": "Right", "title": {"isVisible": true}}
    },
    "locations": ["F1"],
    "marks": {
      "fields": {},
      "panes": {
        "encodings": [
          {"fieldKey": "F2", "type": "Color"},
          {"fieldKey": "F3", "type": "Label"}
        ],
        "isAutomatic": true,
        "stack": {"isAutomatic": true, "isStacked": false},
        "type": "Circle"
      }
    },
    "style": {
      "background": {"styleName": "light", "type": "Map"},
      "encodings": {"fields": {}},
      "fieldLabels": {
        "columns": {"showDividerLine": false, "showLabels": true},
        "rows": {"showDividerLine": false, "showLabels": true}
      },
      "fonts": {},
      "lines": {},
      "marks": {"fields": {}, "panes": {}},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "title": {"isVisible": true}
    }
  }
}
```

Omit empty `fonts`/`lines`/`marks` in hand-written payloads — template builders fill production defaults.

**CLI examples:**

```bash
# Location-only map
python scripts/apply_viz_template.py --template geomap_location_only --sdm YOUR_SDM --workspace YOUR_WS \
  --name Store_Locations --label "Store locations" \
  --latitude Latitude --longitude Longitude --post

# Color + label (default geomap)
python scripts/apply_viz_template.py --template geomap_points --sdm YOUR_SDM --workspace YOUR_WS \
  --name Store_Map --label "Stores on map" \
  --latitude Latitude --longitude Longitude --measure Total_Amount_clc --label-dim Store_Name --post

# Advanced: Color + Size + measure label (measure triplicated in payload)
python scripts/apply_viz_template.py --template geomap_advanced --sdm YOUR_SDM --workspace YOUR_WS \
  --name Map_Advanced --label "Map advanced" \
  --latitude Latitude --longitude Longitude --measure Total_Amount_clc --label-dim Store_Name --post
```

---

## Flow / Sankey (layout: `Flow`)

**Source of truth:** full export **`New_Dashboard1_package (4).json`** (`apiVersion` 66.12). An earlier **`New_Dashboard1_package (2).json`** had **`"visualizations": {}`** (no embedded viz bodies)—only dashboard widget names—so templates inferred from names were not guaranteed to match real `visualSpecification` JSON. Use **`flow_package_*`** templates for parity with `(4).json`.

**Field layout in `(4).json` (two-level flows):** **`F1` = link measure**, **`F2` / `F3` = level dimensions** (`levels`: `["F2","F3"]`, `link`: `"F1"`). That is **measure-first** numbering. Older skill templates **`flow_simple`**, **`flow_sankey`**, etc. use **levels-first** (`F1`/`F2` = levels, `F3` = link) and remain valid for backward compatibility.

**“Measure on marks” in the package** means **`Color`** on **links** (duplicate link measure) and **`Color`** on **nodes** (duplicate **level2** dimension as **`F4`**). The raw export references **`F4` in encodings without defining `F4` in `fields`** in two vizzes (broken refs). Generated payloads from this skill **always define `F4`**.

| Package viz key | Skill template | Encodings (summary) |
|-----------------|----------------|---------------------|
| `Base_Flow` | **`flow_package_base`** | All `[]`; empty mark fills in style |
| `Base_Flow_single_color_all_nodes` | **`flow_package_single_color`** | Same; uniform `#F9E3B6` on bars/nodes |
| `Copy_of_Base_Flow_single_color_all_nodes_measure_on_marks` | **`flow_package_link_color_nodes_color`** | Links `Color(F5)` dup measure; nodes `Color(F4)` dup level2 |
| `Base_Flow_colors_variations_measure_on_marks` | **`flow_package_colors_variations`** | First-level bar `Color(F6)` dup level1; links `Color(F5)`; nodes `Color(F4)` dup level2; legends often hidden |
| `Base_Flow_colors_variations_measure_on_marks1` | **`flow_package_three_level`** | Three dimensions; links `Color(F5)` dup measure; bar encodings `[]`; legend hidden by default |

**Alternate / legacy templates (levels-first, different encodings):** **`flow_simple`**, **`flow_simple_measure_on_marks`** (node **Size**, not package Color-on-marks), **`flow_sankey`**, **`flow_sankey_measure_on_marks`**.

**Shape:** `marks.fields` = one **Bar** per level id; `marks.links` = **Line**; `marks.nodes` = **Bar**. `style.fieldLabels.levels` replaces row/column labels.

**Overrides (JSON via `--overrides`):** `flow_uniform_fill` (hex or `""` for package-style empty fills); `flow_package_hide_color_legends`; `flow_dup_measure_legend_visible`; `flow_link_legend_visible` / `flow_link_color_continuous_palette` (three-level); for legacy flows: `flow_link_legend_visible`, `flow_node_size_legend_visible`, `flow_node_size_min_px` / `max_px`.

```json
{
  "visualSpecification": {
    "layout": "Flow",
    "legends": {},
    "levels": ["F2", "F3"],
    "link": "F1",
    "marks": {
      "fields": {
        "F2": {
          "encodings": [],
          "isAutomatic": true,
          "stack": {"isAutomatic": true, "isStacked": false},
          "type": "Bar"
        },
        "F3": {
          "encodings": [],
          "isAutomatic": true,
          "stack": {"isAutomatic": true, "isStacked": false},
          "type": "Bar"
        }
      },
      "links": {
        "encodings": [],
        "isAutomatic": true,
        "stack": {"isAutomatic": true, "isStacked": false},
        "type": "Line"
      },
      "nodes": {
        "encodings": [],
        "isAutomatic": true,
        "stack": {"isAutomatic": true, "isStacked": false},
        "type": "Bar"
      }
    },
    "style": {
      "encodings": {"fields": {"F1": {"defaults": {"format": {}}}}},
      "fieldLabels": {"levels": {"showDividerLine": false, "showLabels": true}},
      "fonts": {},
      "lines": {},
      "marks": {"fields": {}, "links": {}, "nodes": {}},
      "shading": {"backgroundColor": "#FFFFFF", "banding": {"rows": {"color": "#E5E5E5"}}},
      "title": {"isVisible": true}
    }
  }
}
```

**CLI examples (package parity, measure-first field mapping in JSON):**

```bash
# Base_Flow
python scripts/apply_viz_template.py --template flow_package_base --sdm YOUR_SDM --workspace YOUR_WS \
  --name Base_Flow --label "Base flow" \
  --level1 Product_Family1 --level2 Store_Type --link-measure Total_Orders_clc --post

# Base_Flow_single_color_all_nodes
python scripts/apply_viz_template.py --template flow_package_single_color --sdm YOUR_SDM --workspace YOUR_WS \
  --name Flow_Single_Color --label "Flow single color" \
  --level1 Product_Family1 --level2 Store_Type --link-measure Total_Orders_clc --post

# Copy_of_Base_Flow_*_measure_on_marks (link + node Color; F4 defined in output)
python scripts/apply_viz_template.py --template flow_package_link_color_nodes_color --sdm YOUR_SDM --workspace YOUR_WS \
  --name Flow_Link_Node_Color --label "Flow link and node color" \
  --level1 Product_Family1 --level2 Store_Type --link-measure Total_Orders_clc --post

# Base_Flow_colors_variations_measure_on_marks
python scripts/apply_viz_template.py --template flow_package_colors_variations --sdm YOUR_SDM --workspace YOUR_WS \
  --name Flow_Color_Var --label "Flow color variations" \
  --level1 Product_Family1 --level2 Store_Type --link-measure Total_Orders_clc --post

# Three-level + link Color (Base_Flow_colors_variations_measure_on_marks1)
python scripts/apply_viz_template.py --template flow_package_three_level --sdm YOUR_SDM --workspace YOUR_WS \
  --name Flow_Three_Level --label "Flow three levels" \
  --level1 Store_Type --level2 Region --level3 Status1 --link-measure Total_Amount_clc --post
```

**Legacy levels-first templates** (different `F` key order in JSON): `flow_simple`, `flow_simple_measure_on_marks`, `flow_sankey`, `flow_sankey_measure_on_marks` — optional `--link-color-measure`, `--level2-color-dim` on the Sankey variants.

**Strict checks (generated JSON):** `validate(payload, strict_encoding_field_refs=True)` ensures every `marks` encoding `fieldKey` exists under root `fields`.

---

## Field Naming Conventions

| Suffix | Type | Example |
|--------|------|---------|
| `_clc` | Calculated field | `Open_Pipeline_clc`, `Headcount_clc` |
| `_mtc` | Metric (dashboard widget only) | `Headcount_mtc`, `Turnover_Rate_mtc` |
| `_prm` | List parameter | `Region_Filter_prm` |
| none | Standard SDM field | `Region`, `Amount_USD`, `Stage` |

`objectName: null` for `_clc` fields — they have no object.

## Number Format Types

| `type` | Example output |
|--------|---------------|
| `"Number"` | `1,234,567.89` |
| `"NumberShort"` | `1.2M` |
| `"Currency"` | `$1,234,567.89` |
| `"CurrencyShort"` | `$1.2M` |
| `"Percent"` | `12.34%` |

## Dashboard Widget Types

```json
"widgets": {
  "viz_1":    {"type": "visualization", "source": {"name": "{{VIZ_NAME}}"}, "parameters": {"legendPosition": "Right", "receiveFilterSource": {"filterMode": "all", "widgetIds": []}}},
  "metric_1": {"type": "metric", "source": {"name": "{{METRIC_NAME}}"}, "parameters": {"metricOption": {"sdmApiName": "{{SDM_NAME}}", "layout": {"componentVisibility": {"chart": true, "value": true, "comparison": true, "title": true}}}}},
  "filter_1": {"type": "filter", "label": "{{LABEL}}", "source": {"name": "{{SDM_NAME}}"}, "parameters": {"filterOption": {"dataType": "Text", "fieldName": "{{FIELD}}", "objectName": "{{OBJECT}}", "selectionType": "multiple"}, "viewType": "list"}}
}
```

> **Critical:** `source` must only contain `"name"`. Adding `"label"` or `"type"` to source causes `JSON_PARSER_ERROR`. The widget's own `"type"` field (visualization/metric/filter) is correct at the widget level, not inside source.
