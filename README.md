<div align="center">

# 🌡️ ThermaCity

### Know Where the Heat Hurts Most

*Satellite intelligence + citizen reports to protect Pune's most vulnerable neighbourhoods during heatwaves.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?logo=postgresql&logoColor=white)](https://postgis.net)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![GEE](https://img.shields.io/badge/Google%20Earth%20Engine-API-4285F4?logo=google-earth&logoColor=white)](https://earthengine.google.com)

</div>

---

## The Problem

In April 2024, Pune recorded its highest-ever temperature of **42.4°C**. Across India that summer, over **46,000 suspected heatstroke cases** and **110+ confirmed heat deaths** were reported. Heatwaves are no longer rare events — they are seasonal emergencies.

But Pune Municipal Corporation has **no tool to answer the most critical question during a heat emergency:**

> **"Which neighbourhoods should we protect first?"**

Satellite temperature maps show *where it's hot*. But a hot parking lot with nobody around is not the same as a hot, crowded, shadeless marketplace. **Vulnerability** is the intersection of heat, humidity, stagnant wind, missing tree canopy, and how many people are exposed — and no existing system models this.

## The Solution

ThermaCity combines **satellite imagery, machine learning, and citizen reports** to produce a **Heat Vulnerability Score (0–100)** for every 100×100 m block across Pune. It answers three questions that temperature maps alone cannot:

| Question | Who Asks It | How ThermaCity Answers |
|----------|-------------|----------------------|
| *"Where should we send water tankers and cooling vans RIGHT NOW?"* | Disaster management | Real-time ward-level risk rankings with the most dangerous zones highlighted |
| *"Where should we plant trees for maximum cooling impact?"* | Urban planners | Scenario simulator — *"500 trees here drops felt temperature by 2.1°C for 50,000 residents"* |
| *"Is my neighbourhood heat-safe?"* | Citizens | Personal heat risk lookup + ability to report missing shade, broken fountains, closed shelters |

---

## What the Score Actually Means

ThermaCity doesn't just assign numbers. Each score tells a story about what people on the ground experience:

| Score | Risk Tier | What It Means In Practice |
|-------|-----------|--------------------------|
| 0–25 | 🟢 **Heat-Safe** | Manageable heat. Adequate shade and ventilation. |
| 26–50 | 🟡 **Caution Zone** | Uncomfortable during peak hours. Elderly and outdoor workers at mild risk. |
| 51–75 | 🟠 **Heat-Stressed** | Dangerous for prolonged outdoor exposure. Cooling infrastructure gaps exist. |
| 76–100 | 🔴 **Heat Emergency** | Life-threatening during heatwaves. Immediate intervention needed. |

**Example:** A score of **84** means: surface temperature is 46°C, tree canopy is only 8%, wind is stagnant below 1 m/s, humidity makes it *feel* like 52°C, and 18,000 people per km² are exposed to this every day from March to June.

A score of **22** means: it's warm at 34°C, but 40% tree cover, a nearby river cooling the air, decent wind flow, and low-density residential layout keep it manageable.

---

## How the AI Works

ThermaCity deliberately separates **physics** from **vulnerability** for scientific rigour:

### Step 1 — ML Temperature Prediction

A **Random Forest Regressor** learns how land-cover physically influences surface temperature:

| Input Feature | What It Captures |
|---|---|
| **NDVI** | Vegetation health — green areas cool through evapotranspiration |
| **NDBI** | Concrete & built-up density — absorbs and re-radiates heat |
| **NDWI** | Water body proximity — lakes and rivers provide localised cooling |
| **Tree Canopy Fraction** | Physical shade from tree cover — blocks direct solar radiation |

**Target:** Observed Land Surface Temperature (LST) from Landsat 8/9.

This model powers the **scenario simulator** — planners can ask *"What if we increase tree canopy by 20% in Hadapsar?"* and get a physically meaningful temperature prediction.

### Step 2 — Deterministic Vulnerability Scoring

The Heat Vulnerability Score is computed using a **weighted formula** (not ML) that layers human exposure on top of the predicted temperature:

```
Score = 0.35 × Surface Heat
      + 0.20 × Population Density (exposure risk)
      + 0.20 × Lack of Tree Canopy (shade deficit)
      + 0.15 × Humidity (feels-like amplifier)
      + 0.10 × Wind Stagnation (trapped heat)
```

> **Why separate ML from scoring?** Because the ML model captures physics (land-cover → temperature). The vulnerability formula adds the human dimension (how many people, how exposed). Mixing them would make the model uninterpretable and the scenario simulator meaningless.

---

## Community Reports: What Satellites Can't See

Satellites measure temperature. Citizens experience **reality**:

- 🚏 *"The bus stop at Swargate has zero shade. I waited 20 minutes in 44°C sun."*
- 🚰 *"The public water fountain at Deccan Gymkhana has been broken for 3 months."*
- 🏗️ *"Construction workers on Senapati Bapat Road have nowhere to cool down."*
- 🌳 *"The only park in our ward is locked during peak afternoon hours."*

These geo-tagged reports overlay on the satellite heat map, adding a **visceral, human layer** that pure data cannot capture. Municipal planners see citizen pain points directly on their dashboard — turning complaints into actionable infrastructure priorities.

**Report categories:**
| Category | What It Flags |
|----------|---------------|
| 🔥 Extreme Heat Discomfort | Dangerously hot areas with no relief |
| 🌳 Lack of Shade | Missing tree cover or shade structures |
| ♨️ Hot Pavement | Radiating surfaces that burn through footwear |
| 🚏 Bus Stop Without Shade | Transit points with zero sun protection |
| 🚰 Water Fountain Unavailable | Broken or missing public drinking water |
| 🏠 Cooling Shelter Closed | Emergency cooling centres that aren't operational |

---

## System Architecture

```
Satellite & Climate Data                    Citizens
(Landsat 8/9, Sentinel-2,                      │
 ERA5-Land, WorldCover, WorldPop)               │
         │                                      │
         ▼                                      ▼
┌─────────────────────┐              ┌──────────────────┐
│  Google Earth Engine │              │  Community Report │
│  Data Extraction     │              │  Submission Form  │
│  Pipeline (Python)   │              │  (React Frontend) │
└────────┬────────────┘              └────────┬─────────┘
         │                                     │
         ▼                                     │
┌─────────────────────┐                        │
│  Feature Engineering │                       │
│  & Grid Aggregation  │                       │
│  (100×100 m cells)   │                       │
└────────┬────────────┘                        │
         │                                     │
         ▼                                     │
┌─────────────────────┐                        │
│  Random Forest       │                       │
│  Regressor           │                       │
│  (LST Prediction)    │                       │
└────────┬────────────┘                        │
         │                                     │
         ▼                                     ▼
┌──────────────────────────────────────────────────┐
│              Supabase (PostgreSQL + PostGIS)     │
│  ┌────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │spatial_grid│ │environmental │ │ community  │ │
│  │  (19k+     │ │  _features   │ │ _reports   │ │
│  │   cells)   │ │ (per year)   │ │ (citizen)  │ │
│  └────────────┘ └──────────────┘ └────────────┘ │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
               ┌─────────────────┐
               │   FastAPI        │
               │   REST API       │
               │   + ReportLab    │
               │   + HVI Engine   │
               └────┬───────┬────┘
                    │       │
           ┌────────┘       └────────┐
           ▼                         ▼
  ┌─────────────────┐       ┌─────────────────┐
  │ Main Public App │       │ Admin Dashboard │
  │ (React+Leaflet) │       │ (React+Leaflet) │
  │ View heat map & │       │ Verify citizen  │
  │ submit reports  │       │ reports securely│
  └─────────────────┘       └─────────────────┘
```

---

## Dashboard Outputs

When a municipal officer opens ThermaCity during a heatwave alert, they see:

| View | What It Shows | Who Uses It |
|------|---------------|-------------|
| **Ward-First Navigation** | 41 official PMC wards with aggregate heat scores. Click a ward to drill down into its 100m blocks. | Disaster management |
| **City-wide Heat Risk Map** | Every 100m block colour-coded by vulnerability, bounded to Pune with a clean white basemap | Disaster management |
| **Normal / Heatmap Toggle** | Switch between a clean street map and the HVI heatmap overlay to orient yourself | All users |
| **Block-Level Simulation** | "What if we plant 500 trees here?" — block-specific precision before/after risk comparison | Budget proposals |
| **SHAP Explainability** | Click a block to see dynamic, plain-English explanations of the exact physical and demographic factors driving its specific heat risk | Public / Planners |
| **Automated PDF Reports** | Publication-ready PDF downloads for macro (city-wide) or micro (specific 100m block) risk assessment | Planners / Public |
| **Temporal Change (2021–2026)** | Year slider showing which areas got worse over time | Urban planners |
| **Verified Report Markers** | Red "!" markers on the map for admin-verified citizen reports | All users |

### Admin Dashboard (Separate Site)

| Feature | What It Does |
|---------|-------------|
| **Pending Verifications** | Review incoming citizen reports with severity, ratings, and location |
| **Verify & Publish** | Approve a report — it appears as a marker on the public map |
| **Reject** | Delete spam or misinformation before it reaches the public |
| **Published Reports** | View all live reports on the map; **Take Down & Delete** any at any time |
| **Auto-Refresh** | Dashboard polls for new reports every 10 seconds |

---

## Project Structure

```
ThermaCity/
├── frontend/                    # Main React (Vite) Public App + Leaflet
├── admin-frontend/              # Admin React (Vite) Dashboard for report verification
├── backend/                     # FastAPI + SQLAlchemy + PostGIS
│   ├── app/
│   │   ├── config.py            # Pydantic Settings (HVI weights, DB URL)
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── models/              # ORM models with GeoAlchemy2
│   │   ├── routers/             # REST API endpoints
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── services/            # HVI calculator, ML predictor
│   └── alembic/                 # Database migrations
├── ml/                          # Machine Learning pipeline
│   ├── scripts/
│   │   ├── train_model.py       # RF training with sklearn Pipeline
│   │   └── evaluate_model.py    # RMSE, MAE, R² evaluation
│   ├── models/                  # Serialized .joblib artifacts
│   └── data/                    # Training/test CSVs (gitignored)
├── gee/                         # Google Earth Engine pipelines
│   ├── scripts/
│   │   ├── 01_extract_lst.py    # Landsat 8/9 thermal data
│   │   ├── 02_extract_ndvi_ndbi.py  # Sentinel-2 spectral indices
│   │   ├── 04_extract_tree_canopy.py # ESA WorldCover 10m
│   │   └── 08_merge_features.py # Merge all layers → training set
│   ├── utils/
│   │   ├── auth.py              # GEE authentication
│   │   ├── geometry.py          # Pune boundary + 100m grid generator
│   │   └── export.py            # Canonical reduce_to_grid() function
│   └── boundaries/
│       └── pune_boundary.geojson
└── db/
    └── init.sql                 # PostGIS schema (tables + triggers)
```

---

## Data Sources

| Dataset | Provider | Resolution | What It Captures |
|---------|----------|------------|------------------|
| Landsat 8/9 Collection 2 L2 | USGS/NASA | 30 m | Surface temperature (the raw heat) |
| Sentinel-2 L2A Harmonized | ESA/Copernicus | 10 m | Vegetation, concrete, water (what controls the heat) |
| ESA WorldCover v200 | ESA | 10 m | Tree canopy (what blocks the heat) |
| ERA5-Land | ECMWF | ~9 km | Humidity and wind (what traps or amplifies the heat) |
| WorldPop | WorldPop | 100 m | Population density (who is exposed to the heat) |

All raster data is aggregated to a uniform **100×100 m grid** using a [single canonical function](gee/utils/export.py) to guarantee spatial alignment across every layer.

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.11+
- Node.js 18+
- [Google Earth Engine account](https://earthengine.google.com/)

### 1. Clone & Configure

```bash
git clone https://github.com/Adds14/ThermaCity.git
cd ThermaCity
# Set up .env files in backend/, frontend/, and admin-frontend/
# using your Supabase database credentials.

> **Note:** The repository includes a GitHub Action (`.github/workflows/keep-alive.yml`) to prevent your Supabase Free Tier project from automatically pausing. Simply add your Supabase connection string as a repository secret named `SUPABASE_DB_URL` on GitHub to enable it!
```

### 2. Run the GEE Pipeline

```bash
cd gee
pip install -r requirements.txt

# Generate the 100×100m analysis grid
python utils/geometry.py

# Extract satellite data (requires GEE authentication)
python scripts/01_extract_lst.py --project-id YOUR_PROJECT
python scripts/02_extract_ndvi_ndbi.py --project-id YOUR_PROJECT
python scripts/04_extract_tree_canopy.py --project-id YOUR_PROJECT

# Download CSVs from Google Drive, then merge
python scripts/08_merge_features.py --input-dir ./exports --output ../ml/data/training_set.csv
```

### 4. Train the Model

```bash
cd ml
pip install -r requirements.txt
python scripts/train_model.py
python scripts/evaluate_model.py
```

### 4. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 5. Start the Public Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

### 6. Start the Admin Dashboard

```bash
cd admin-frontend
npm install
npm run dev -- --port 5174
# Runs on http://localhost:5174
```

---

## Model Evaluation Targets

| Metric | Target | What It Tells Us |
|--------|--------|------------------|
| RMSE | ≤ 2.5 °C | "Our temperature predictions are off by at most 2.5 degrees on average" |
| MAE | ≤ 2.0 °C | "The typical prediction error a planner would see" |
| R² | ≥ 0.75 | "Land-cover features explain 75%+ of temperature variation" |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontends** | React 19 (Vite) + Leaflet |
| **Backend** | Python 3.11 + FastAPI |
| **Database** | Supabase (PostgreSQL 16 + PostGIS) |
| **ML** | scikit-learn (Random Forest Regressor) |
| **Remote Sensing** | Google Earth Engine (Python API) |

---

## License

This project is developed as a B.Tech capstone project.

---

<div align="center">

**Built for Pune. Powered by open satellite data. Designed to save lives during heatwaves.**

</div>
