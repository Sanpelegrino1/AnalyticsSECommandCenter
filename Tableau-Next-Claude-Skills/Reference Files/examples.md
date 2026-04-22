# Tableau Next Visualization Examples (v66.8)

Real-world, production-quality examples extracted from actual Tableau Next deployments.
All examples use API `v66.0` with `minorVersion=8`.

---

## Example 1: Sales Intelligence Dashboard

**Industry:** Sales / CRM  
**Source:** Sales Intelligence v2 production package  
**What it builds:** Open Pipeline by Region (Donut) + Closed Won by Region (Horizontal Bar) + a full dashboard

---

### Step 1: Auth & Discover

```bash
export SF_ORG=myorg
export SF_TOKEN=$(sf org display --target-org $SF_ORG --json | jq -r '.result.accessToken')
export SF_INSTANCE=$(sf org display --target-org $SF_ORG --json | jq -r '.result.instanceUrl')

# List SDMs
curl -X GET "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models" \
  -H "Authorization: Bearer ${SF_TOKEN}"

# Get field details for your Sales SDM
curl -X GET "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/TUA_DEMO_Sales" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Fields used from SDM `TUA_DEMO_Sales`:**
- Object: `TUA_DEMO_Sales`
- Dimensions: `Region`
- Measures: `Amount_USD`, `Open_Pipeline_clc` (calculated), `Closed_Won_clc` (calculated)

---

### Step 2: Create Workspace

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/workspaces" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Sales_Intelligence_Workspace", "label": "Sales Intelligence"}'
```

---

### Step 3: Create Visualization 1 — Open Pipeline by Region (Donut)

**File: `open_pipeline_donut.json`**

```json
{
  "name": "Open_Pipe_by_Region",
  "label": "Open Pipe by Region",
  "dataSource": {
    "label": "Sales Intelligence",
    "name": "TUA_DEMO_Sales",
    "type": "SemanticModel"
  },
  "workspace": {
    "label": "Sales Intelligence",
    "name": "Sales_Intelligence_Workspace"
  },
  "interactions": [],
  "fields": {
    "F3": {
      "displayCategory": "Discrete",
      "fieldName": "Region",
      "label": "Region",
      "objectName": "TUA_DEMO_Sales",
      "role": "Dimension",
      "type": "Field"
    },
    "F7": {
      "displayCategory": "Continuous",
      "fieldName": "Open_Pipeline_clc",
      "function": "Sum",
      "role": "Measure",
      "type": "Field"
    },
    "F8": {
      "displayCategory": "Continuous",
      "fieldName": "Open_Pipeline_clc",
      "function": "Sum",
      "role": "Measure",
      "type": "Field"
    }
  },
  "visualSpecification": {
    "columns": [],
    "rows": [],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {
      "F3": {
        "isVisible": true,
        "position": "Right",
        "title": {"isVisible": true}
      }
    },
    "marks": {
      "fields": {},
      "headers": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Text"
      },
      "panes": {
        "encodings": [
          {"fieldKey": "F3", "type": "Color"},
          {"fieldKey": "F7", "type": "Angle"},
          {"fieldKey": "F8", "type": "Label"}
        ],
        "isAutomatic": false,
        "type": "Donut",
        "stack": {"isAutomatic": true, "isStacked": false}
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
              "customColors": [
                {"color": "#01C3B3", "value": "EMEA"},
                {"color": "#4992FE", "value": "North America"},
                {"color": "#022AC0", "value": "APAC"},
                {"color": "#D8E6FE", "value": "LATAM"}
              ],
              "palette": {
                "colors": ["#4992fe", "#ba01ff", "#06a59a", "#3a49da", "#fe5c4c", "#024d4c", "#3ba755", "#8a033e"],
                "type": "Custom"
              },
              "type": "Discrete"
            },
            "defaults": {"format": {}}
          },
          "F7": {
            "defaults": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "",
                  "suffix": "",
                  "type": "NumberShort"
                }
              }
            }
          },
          "F8": {
            "defaults": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "",
                  "suffix": "",
                  "type": "NumberShort"
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
        "fields": {},
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
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}
        },
        "panes": {
          "color": {"color": ""},
          "isAutomaticSize": true,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true},
          "size": {"isAutomatic": true, "type": "Percentage", "value": 80}
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
    "name": "Open_Pipe_by_Region_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {
          "F3": {"byField": "F7", "order": "Descending", "type": "Field"}
        },
        "rows": []
      }
    }
  }
}
```

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @open_pipeline_donut.json
```

**What makes this compelling:**
- `customColors` maps specific hex colors to each region value (EMEA, North America, APAC, LATAM)
- F7 and F8 reference the same calculated field (`Open_Pipeline_clc`) — F7 drives the angle (slice size), F8 adds the label on each slice
- `showMarkLabels: true` on panes shows values directly on the donut
- `sortOrders.fields.F3.byField: "F7"` sorts slices descending by pipeline value

---

### Step 4: Create Visualization 2 — Closed Won by Region (Horizontal Bar, sorted)

**File: `closed_won_bar.json`**

```json
{
  "name": "Closed_Won_by_Region",
  "label": "Closed Won by Region",
  "dataSource": {
    "label": "Sales Intelligence",
    "name": "TUA_DEMO_Sales",
    "type": "SemanticModel"
  },
  "workspace": {
    "label": "Sales Intelligence",
    "name": "Sales_Intelligence_Workspace"
  },
  "interactions": [],
  "fields": {
    "F3": {
      "displayCategory": "Discrete",
      "fieldName": "Region",
      "label": "Region",
      "objectName": "TUA_DEMO_Sales",
      "role": "Dimension",
      "type": "Field"
    },
    "F7": {
      "displayCategory": "Continuous",
      "fieldName": "Closed_Won_clc",
      "function": "Sum",
      "role": "Measure",
      "type": "Field"
    }
  },
  "visualSpecification": {
    "columns": ["F7"],
    "rows": ["F3"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {},
    "marks": {
      "fields": {},
      "headers": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Text"
      },
      "panes": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "axis": {
        "fields": {
          "F7": {
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
                  "prefix": "$",
                  "suffix": "",
                  "type": "CurrencyShort"
                }
              }
            },
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}},
            "titleText": "Closed Won"
          }
        }
      },
      "encodings": {
        "fields": {
          "F7": {
            "defaults": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "$",
                  "suffix": "",
                  "type": "CurrencyShort"
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
          "F3": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}
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
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}
        },
        "panes": {
          "color": {"color": ""},
          "isAutomaticSize": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false},
          "range": {"reverse": true},
          "size": {"isAutomatic": false, "type": "Percentage", "value": 60}
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
    "name": "Closed_Won_by_Region_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {
          "F3": {"byField": "F7", "order": "Descending", "type": "Field"}
        },
        "rows": []
      }
    }
  }
}
```

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @closed_won_bar.json
```

---

### Step 5: Create the Sales Dashboard

**File: `sales_dashboard.json`**

```json
{
  "name": "Sales_Intelligence_Dashboard",
  "label": "Sales Intelligence",
  "workspaceIdOrApiName": "Sales_Intelligence_Workspace",
  "layouts": [{
    "name": "default",
    "columnCount": 48,
    "rowHeight": 20,
    "maxWidth": 1200,
    "pages": [{
      "name": "main_page",
      "label": "Overview",
      "widgets": [
        {"name": "filter_region",   "column": 0,  "row": 0,  "colspan": 12, "rowspan": 2},
        {"name": "filter_stage",    "column": 12, "row": 0,  "colspan": 12, "rowspan": 2},
        {"name": "viz_donut",       "column": 0,  "row": 2,  "colspan": 24, "rowspan": 15},
        {"name": "viz_bar",         "column": 24, "row": 2,  "colspan": 24, "rowspan": 15}
      ]
    }]
  }],
  "widgets": {
    "filter_region": {
      "type": "filter",
      "label": "Region",
      "source": {"name": "TUA_DEMO_Sales"},
      "parameters": {
        "filterOption": {"dataType": "Text", "fieldName": "Region", "objectName": "TUA_DEMO_Sales", "selectionType": "multiple"},
        "viewType": "list"
      }
    },
    "filter_stage": {
      "type": "filter",
      "label": "Stage",
      "source": {"name": "TUA_DEMO_Sales"},
      "parameters": {
        "filterOption": {"dataType": "Text", "fieldName": "Stage", "objectName": "TUA_DEMO_Sales", "selectionType": "multiple"},
        "viewType": "list"
      }
    },
    "viz_donut": {
      "type": "visualization",
      "source": {"name": "Open_Pipe_by_Region"},
      "parameters": {
        "legendPosition": "Right",
        "receiveFilterSource": {"filterMode": "all", "widgetIds": []}
      }
    },
    "viz_bar": {
      "type": "visualization",
      "source": {"name": "Closed_Won_by_Region"},
      "parameters": {
        "legendPosition": "Right",
        "receiveFilterSource": {"filterMode": "all", "widgetIds": []}
      }
    }
  }
}
```

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/dashboards?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @sales_dashboard.json
```

---

## Example 2: Marketing Campaign Intelligence

**Industry:** Marketing  
**Source:** Embedded Marketing Intelligence v2 production package  
**What it builds:** Spend by Campaign (Bar) + Campaign Detail Table

---

### Step 1: SDM Fields

```bash
curl -X GET "${SF_INSTANCE}/services/data/v66.0/ssot/semantic/models/TUA_DEMO_Marketing" \
  -H "Authorization: Bearer ${SF_TOKEN}"
```

**Fields:**
- Object: `TUA_DEMO_Marketing`
- Dimensions: `Account_Name2` (Campaign), `Channel1`, `Product2`, `Campaign_Id`
- Measures: `Spend`, `Revenue`, `ROAS`

---

### Step 2: Create Visualization 1 — Spend by Campaign (Horizontal Bar with Currency Format)

**File: `spend_by_campaign.json`**

```json
{
  "name": "Spend_by_Campaign",
  "label": "Spend by Campaign",
  "dataSource": {
    "label": "Marketing Intelligence",
    "name": "TUA_DEMO_Marketing",
    "type": "SemanticModel"
  },
  "workspace": {
    "label": "Marketing Intelligence",
    "name": "Marketing_Intelligence_Workspace"
  },
  "interactions": [],
  "fields": {
    "F2": {
      "displayCategory": "Discrete",
      "fieldName": "Account_Name2",
      "label": "Campaign",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Dimension",
      "type": "Field"
    },
    "F3": {
      "displayCategory": "Continuous",
      "fieldName": "Spend",
      "function": "Sum",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Measure",
      "type": "Field"
    }
  },
  "visualSpecification": {
    "columns": ["F3"],
    "rows": ["F2"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {},
    "marks": {
      "fields": {},
      "headers": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Text"
      },
      "panes": {
        "encodings": [],
        "isAutomatic": true,
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
                  "type": "CurrencyShort"
                }
              }
            },
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}},
            "titleText": "Spend"
          }
        }
      },
      "encodings": {
        "fields": {
          "F3": {
            "defaults": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "",
                  "suffix": "",
                  "type": "Currency"
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
          "F2": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}
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
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}
        },
        "panes": {
          "color": {"color": ""},
          "isAutomaticSize": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false},
          "range": {"reverse": true},
          "size": {"isAutomatic": false, "type": "Percentage", "value": 60}
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
    "name": "Spend_by_Campaign_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {
          "F2": {"byField": "F3", "order": "Descending", "type": "Field"}
        },
        "rows": []
      }
    }
  }
}
```

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @spend_by_campaign.json
```

**What makes this compelling:**
- `axis.fields.F3.scale.format.type: "CurrencyShort"` shows `$1.2M` on axis ticks
- `encodings.fields.F3.format.type: "Currency"` shows full `$1,234,567.89` in tooltips
- `axis.fields.F3.titleText: "Spend"` adds a custom axis label
- `size.value: 60` (60% width bars) for a cleaner look than full-width

---

### Step 3: Create Visualization 2 — Campaign Detail Table

**File: `marketing_table.json`**

```json
{
  "name": "Marketing_Campaign_Table",
  "label": "Campaign Details",
  "dataSource": {
    "label": "Marketing Intelligence",
    "name": "TUA_DEMO_Marketing",
    "type": "SemanticModel"
  },
  "workspace": {
    "label": "Marketing Intelligence",
    "name": "Marketing_Intelligence_Workspace"
  },
  "interactions": [],
  "fields": {
    "F1": {
      "displayCategory": "Discrete",
      "fieldName": "Campaign_Id",
      "label": "Campaign ID",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Dimension",
      "type": "Field"
    },
    "F2": {
      "displayCategory": "Discrete",
      "fieldName": "Account_Name2",
      "label": "Campaign",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Dimension",
      "type": "Field"
    },
    "F3": {
      "displayCategory": "Discrete",
      "fieldName": "Channel1",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Dimension",
      "type": "Field"
    },
    "F4": {
      "displayCategory": "Discrete",
      "fieldName": "Product2",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Dimension",
      "type": "Field"
    },
    "F5": {
      "displayCategory": "Discrete",
      "fieldName": "Spend",
      "function": "Sum",
      "label": "Spend",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Measure",
      "type": "Field"
    },
    "F6": {
      "displayCategory": "Discrete",
      "fieldName": "Revenue",
      "function": "Sum",
      "label": "Revenue",
      "objectName": "TUA_DEMO_Marketing",
      "role": "Measure",
      "type": "Field"
    }
  },
  "visualSpecification": {
    "columns": [],
    "rows": ["F1", "F2", "F3", "F4", "F5", "F6"],
    "forecasts": {},
    "layout": "Table",
    "legends": {},
    "marks": {
      "fields": {},
      "headers": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Text"
      },
      "panes": {
        "encodings": [],
        "isAutomatic": false,
        "type": "Circle",
        "stack": {"isAutomatic": true, "isStacked": false}
      }
    },
    "measureValues": [],
    "referenceLines": {},
    "style": {
      "encodings": {
        "fields": {
          "F5": {
            "defaults": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "$",
                  "suffix": "",
                  "type": "Currency"
                }
              }
            }
          },
          "F6": {
            "defaults": {
              "format": {
                "numberFormatInfo": {
                  "decimalPlaces": 2,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "$",
                  "suffix": "",
                  "type": "Currency"
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
      "fit": "Standard",
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
        "fields": {},
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
        "headers": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}},
        "panes": {"color": {"color": ""}, "isAutomaticSize": true, "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}, "range": {"reverse": false}}
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
    "name": "Marketing_Campaign_Table_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {"columns": [], "fields": {}, "rows": []}
    }
  }
}
```

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/visualizations?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @marketing_table.json
```

**Table key patterns:**
- `layout: "Table"` (not `"Vizql"`)
- `marks.panes.type: "Circle"` + `isAutomatic: false`
- All fields in `rows: [...]`, empty `columns: []`
- Measures use `displayCategory: "Discrete"` in table context

---

## Example 3: HR Workforce Analytics

**Industry:** Human Resources  
**Source:** HR Workforce production package  
**What it builds:** A dashboard combining KPI metric widgets with headcount visualization

This example highlights the **metrics pattern** — using `_mtc` metric names in dashboard widgets alongside `_clc` calculated fields in visualizations.

---

### Dashboard Requirements from the HR Package

```json
{
  "requirements": {
    "metrics": [
      "Average_Seniority_mtc",
      "Avg_Employee_Age_mtc",
      "Headcount_mtc",
      "Leavers_mtc",
      "New_Hires_mtc",
      "Turnover_Rate_mtc"
    ],
    "fields": [
      {"fieldName": "Average_Seniority_clc", "objectName": null},
      {"fieldName": "Headcount_clc", "objectName": null},
      {"fieldName": "department_name1", "objectName": "qb_hw_department"},
      {"fieldName": "gender", "objectName": "qb_hw_employee"},
      {"fieldName": "hire_date", "objectName": "qb_hw_employee"}
    ]
  }
}
```

**Key patterns:**
- `objectName: null` = calculated field (`_clc` suffix) — not tied to a specific object
- `objectName: "qb_hw_employee"` = standard field from data object
- `_mtc` metrics live outside visualizations — referenced only in dashboard metric widgets

---

### Step 1: Create Headcount by Department (Horizontal Bar)

**File: `headcount_by_dept.json`**

```json
{
  "name": "Headcount_by_Department",
  "label": "Headcount by Department",
  "dataSource": {
    "label": "HR Workforce",
    "name": "HR_Workforce_SDM",
    "type": "SemanticModel"
  },
  "workspace": {
    "label": "HR Analytics",
    "name": "HR_Analytics_Workspace"
  },
  "interactions": [],
  "fields": {
    "F1": {
      "displayCategory": "Discrete",
      "fieldName": "department_name1",
      "label": "Department",
      "objectName": "qb_hw_department",
      "role": "Dimension",
      "type": "Field"
    },
    "F2": {
      "displayCategory": "Continuous",
      "fieldName": "Headcount_clc",
      "function": "Sum",
      "role": "Measure",
      "type": "Field"
    }
  },
  "visualSpecification": {
    "columns": ["F2"],
    "rows": ["F1"],
    "forecasts": {},
    "layout": "Vizql",
    "legends": {},
    "marks": {
      "fields": {},
      "headers": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Text"
      },
      "panes": {
        "encodings": [],
        "isAutomatic": true,
        "type": "Bar",
        "stack": {"isAutomatic": true, "isStacked": true}
      }
    },
    "measureValues": [],
    "referenceLines": {},
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
                  "decimalPlaces": 0,
                  "displayUnits": "Auto",
                  "includeThousandSeparator": true,
                  "negativeValuesFormat": "Auto",
                  "prefix": "",
                  "suffix": "",
                  "type": "Number"
                }
              }
            },
            "ticks": {"majorTicks": {"type": "Auto"}, "minorTicks": {"type": "Auto"}},
            "titleText": "Headcount"
          }
        }
      },
      "encodings": {
        "fields": {
          "F2": {"defaults": {"format": {"numberFormatInfo": {"decimalPlaces": 0, "displayUnits": "Auto", "includeThousandSeparator": true, "negativeValuesFormat": "Auto", "prefix": "", "suffix": "", "type": "Number"}}}}
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
          "F1": {"hiddenValues": [], "isVisible": true, "showMissingValues": false}
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
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": false}
        },
        "panes": {
          "color": {"color": ""},
          "isAutomaticSize": false,
          "label": {"canOverlapLabels": false, "marksToLabel": {"type": "All"}, "showMarkLabels": true},
          "range": {"reverse": true},
          "size": {"isAutomatic": false, "type": "Percentage", "value": 60}
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
    "name": "Headcount_by_Department_default",
    "viewSpecification": {
      "filters": [],
      "sortOrders": {
        "columns": [],
        "fields": {
          "F1": {"byField": "F2", "order": "Descending", "type": "Field"}
        },
        "rows": []
      }
    }
  }
}
```

---

### Step 2: Create the HR Dashboard with KPI Metric Cards

**File: `hr_dashboard.json`**

```json
{
  "name": "HR_Workforce_Dashboard",
  "label": "HR Workforce Overview",
  "workspaceIdOrApiName": "HR_Analytics_Workspace",
  "layouts": [{
    "name": "default",
    "columnCount": 48,
    "rowHeight": 20,
    "maxWidth": 1200,
    "pages": [{
      "name": "main_page",
      "label": "Workforce",
      "widgets": [
        {"name": "filter_dept",      "column": 0,  "row": 0,  "colspan": 16, "rowspan": 2},
        {"name": "filter_gender",    "column": 16, "row": 0,  "colspan": 16, "rowspan": 2},
        {"name": "metric_headcount", "column": 0,  "row": 2,  "colspan": 16, "rowspan": 8},
        {"name": "metric_turnover",  "column": 16, "row": 2,  "colspan": 16, "rowspan": 8},
        {"name": "metric_newhires",  "column": 32, "row": 2,  "colspan": 16, "rowspan": 8},
        {"name": "viz_headcount",    "column": 0,  "row": 10, "colspan": 48, "rowspan": 18}
      ]
    }]
  }],
  "widgets": {
    "filter_dept": {
      "type": "filter",
      "label": "Department",
      "source": {"name": "HR_Workforce_SDM"},
      "parameters": {
        "filterOption": {"dataType": "Text", "fieldName": "department_name1", "objectName": "qb_hw_department", "selectionType": "multiple"},
        "viewType": "list"
      }
    },
    "filter_gender": {
      "type": "filter",
      "label": "Gender",
      "source": {"name": "HR_Workforce_SDM"},
      "parameters": {
        "filterOption": {"dataType": "Text", "fieldName": "gender", "objectName": "qb_hw_employee", "selectionType": "multiple"},
        "viewType": "list"
      }
    },
    "metric_headcount": {
      "type": "metric",
      "source": {"name": "Headcount_mtc"},
      "parameters": {
        "metricOption": {
          "sdmApiName": "HR_Workforce_SDM",
          "layout": {"componentVisibility": {"chart": true, "value": true, "comparison": true, "title": true}}
        }
      }
    },
    "metric_turnover": {
      "type": "metric",
      "source": {"name": "Turnover_Rate_mtc"},
      "parameters": {
        "metricOption": {
          "sdmApiName": "HR_Workforce_SDM",
          "layout": {"componentVisibility": {"chart": true, "value": true, "comparison": true, "title": true}}
        }
      }
    },
    "metric_newhires": {
      "type": "metric",
      "source": {"name": "New_Hires_mtc"},
      "parameters": {
        "metricOption": {
          "sdmApiName": "HR_Workforce_SDM",
          "layout": {"componentVisibility": {"chart": true, "value": true, "comparison": true, "title": true}}
        }
      }
    },
    "viz_headcount": {
      "type": "visualization",
      "source": {"name": "Headcount_by_Department"},
      "parameters": {
        "legendPosition": "Right",
        "receiveFilterSource": {"filterMode": "all", "widgetIds": []}
      }
    }
  }
}
```

```bash
curl -X POST "${SF_INSTANCE}/services/data/v66.0/tableau/dashboards?minorVersion=8" \
  -H "Authorization: Bearer ${SF_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @hr_dashboard.json
```

**What makes this compelling:**
- 3 metric KPI cards in the top row — each shows trend chart + value + comparison
- `receiveFilterSource: {"filterMode": "all"}` makes the visualization respond to all dashboard filters
- Calculated field (`Headcount_clc`) has no `objectName` — correct for `_clc` fields
- Dashboard grid is 48 columns: 3 metric cards each at `colspan: 16` = full width top row

---

## Workflow Summary

### Simple Visualization (5 min)

```bash
# 1. Discover
curl GET .../ssot/semantic/models
curl GET .../ssot/semantic/models/{name}

# 2. Create
curl POST .../tableau/visualizations?minorVersion=8 -d @viz.json
```

### Full Dashboard (15-20 min)

```bash
# 1. Create workspace
curl POST .../tableau/workspaces

# 2. Create 2-5 visualizations
curl POST .../tableau/visualizations?minorVersion=8 -d @viz1.json
curl POST .../tableau/visualizations?minorVersion=8 -d @viz2.json

# 3. Create dashboard referencing those viz names
curl POST .../tableau/dashboards?minorVersion=8 -d @dashboard.json
```

---

## v66.8 Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `"encodings style is required for the F2 field"` | Measure in `marks.panes.encodings` missing `style.encodings.fields` entry | Add `"F2": {"defaults": {"format": {}}}` to `style.encodings.fields` |
| `"startToMiddleSteps isn't available with sequential palettes"` | Sequential palette has diverging step properties | Remove `startToMiddleSteps`/`middleToEndSteps` from 2-color palettes |
| `"Field 'X' not found"` | Wrong `fieldName` or `objectName` | Re-check SDM definition response; use `apiName` not `fieldName` |
| `"Value required for [fonts]"` | Missing `style.fonts` with all 7 definitions | Copy full fonts block from template |
| `401 Unauthorized` | Token expired | Run `sf org display` again to get fresh token |
