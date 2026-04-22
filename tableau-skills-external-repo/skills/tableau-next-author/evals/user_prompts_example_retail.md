# F-Layout

## Retail Dashboard Spec

**Org:** MY_ORG  
**SDM:** Retail_Orders  
**Workspace:** (your choice, e.g. `LayouTestF`)    
**Name:** (your choice, e.g. `LayoutTest_F`)

---

Executive retail view: KPIs → trend → mix/flow → geo/heatmap for where volume and basket economics concentrate, filterable by store, region, format, product family, and order channel.

### Metrics
- Average Order Amount
- Total amount
- Number of Customers

### Visualizations

1. **Sales trend** – line chart, total amount over date by product family
2. **Revenue by Region** – donut, total amount by Region
3. **Sales Flow** – Sankey with 3 dimensions Product Family, Store Type and Region. Total amount as link measure
4. **Sales Heatmap** – heatmap, Total amount by store type x Region  (gradient low -> warm high->cool)
5. **Store performance map** – Map, using store (location /latitude and longitude) and Total amount as measure. Size by Total amount

### Filters
Store, Region, Store Type, Product Family, Order Type, Order Date


### Special Ask
Do not show the legends in the charts


---

Here is copy-paste Markdown in the same shape as your Retail / F-layout brief—one block per layout. (Not saved as separate repo files, per your single-README preference.)

---

# Z-layout

## Retail dashboard spec

**Org:** MY_ORG  
**SDM:** Retail_Orders  
**Workspace:** (your choice, e.g. `LayoutTestZ`)  
**Name:** (your choice, e.g. `LayoutTest_Z`)

---

Operational retail view: **metrics across the top** (six KPIs), then **five charts in a Z-style flow**—same story as the executive board (trend → share → flow → concentration → map), with **six filters** across the top.

### Metrics (six, top row)

- Total Sales (`Total_Amount_mtc`)  
- Average Order Amount (`Average_Order_Amount_mtc`)  
- Distinct Customers (`Distinct_Customers_mtc`)  
- Distinct Products Sold (`Distinct_Products_Sold_mtc`)  
- Units Sold (`Units_Sold_mtc`)  
- Items Per Order (`Items_Per_Order_mtc`)

### Visualizations

1. **Sales trend** – multi-series line: total amount over order date by product family  
2. **Revenue by region** – donut: total amount by region  
3. **Sales flow** – three-level flow: product family → store type → region, total amount on links  
4. **Sales heatmap** – total amount by store type × region (custom gradient)  
5. **Store performance map** – map: lat/lon, total amount, size by total amount, store name labels  

### Filters

Store name, region, store type, product family, order type, order date  

### Special ask

Hide chart legends where supported.

---

## Performance-overview retail dashboard spec

**Org:** MY_ORG  
**SDM:** Retail_Orders  
**Workspace:** (e.g. `LayoutTestPerf`)  
**Name:** (e.g. `LayoutTest_Performance`)

---

**Performance** view: **one primary KPI** (large, left), **four secondary KPIs**, **time-period pages** (e.g. Week / Month / Day), **three filters**, and **five charts** for mix, flow, concentration, and geo—aligned to a “how did we perform this period?” narrative.

### Metrics (five: one primary + four secondary)

- **Primary:** Total Sales  
- **Secondary:** Average Order Amount, Distinct Customers, Distinct Products Sold, Units Sold  

### Visualizations

1. **Sales trend** – multi-series line by product family  
2. **Revenue by region** – donut  
3. **Sales flow** – product family → store type → region  
4. **Sales heatmap** – store type × region  
5. **Store map** – lat/lon, sized by total sales  

### Filters

Region, store type, order date  


### Special ask

Hide chart legends where supported
