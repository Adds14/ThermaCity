<div align="center">

# 🌡️ ThermaCity

### AI-Powered Urban Heat Island Monitoring & Vulnerability Index Platform

*Spatial machine learning meets citizen science to map where heat hurts most.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-336791?logo=postgresql&logoColor=white)](https://postgis.net)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7-F7931E?logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![GEE](https://img.shields.io/badge/Google%20Earth%20Engine-API-4285F4?logo=google-earth&logoColor=white)](https://earthengine.google.com)

</div>

---

## 🔍 What Is ThermaCity?

ThermaCity is an **MVP decision-support platform** for the city of **Pune, India** that goes beyond simple satellite heat maps. It uses a **Random Forest regression model** to learn how land-cover characteristics (vegetation, built-up density, water bodies, tree canopy) physically influence surface temperature — and then combines those predictions with humidity, wind, and population data to compute a continuous **Heat Vulnerability Index (HVI)** scored 0–100.

The platform also collects **geo-tagged citizen reports** of heat-related infrastructure gaps (no shade at bus stops, closed cooling shelters, hot pavement), providing ground-level context that satellites cannot capture.

### The Key Insight

> A hot place is not necessarily a *vulnerable* place. A parking lot at 50°C with nobody around is less dangerous than a crowded market at 42°C with no shade, high humidity, and zero wind. ThermaCity models this distinction.

---

## 🏗️ System Architecture

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
│              PostgreSQL + PostGIS                 │
│  ┌────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │spatial_grid│ │environmental │ │ community  │ │
│  │  (30k+     │ │  _features   │ │ _reports   │ │
│  │   cells)   │ │ (per year)   │ │ (citizen)  │ │
│  └────────────┘ └──────────────┘ └────────────┘ │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   FastAPI        │
              │   REST API       │
              │   + HVI Engine   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  React + Mapbox  │
              │  Dashboard       │
              │  (Interactive)   │
              └─────────────────┘
```

---

## 🧠 How the AI Works

ThermaCity deliberately **separates machine learning from vulnerability scoring** for scientific rigor:

### Step 1 — ML Temperature Prediction

A **Random Forest Regressor** learns the physical relationship between land-cover and surface temperature:

| Input Features | What It Measures |
|---|---|
| **NDVI** | Vegetation health & greenness |
| **NDBI** | Built-up / impervious surface density |
| **NDWI** | Proximity to cooling water bodies |
| **Tree Canopy Fraction** | Physical shade & evapotranspiration |

**Target:** Observed Land Surface Temperature (LST) from Landsat 8/9 thermal band.

This model powers the **scenario simulator** — planners can ask *"What if we increase tree canopy by 20% in Ward X?"* and get a physically meaningful temperature prediction.

### Step 2 — Deterministic HVI Computation

The **Heat Vulnerability Index** (0–100) is computed using a weighted formula, NOT predicted by ML:

```
HVI = 0.35 × norm(LST_predicted)
    + 0.20 × norm(Population_Density)
    + 0.20 × norm(1 − Tree_Canopy)
    + 0.15 × norm(Humidity)
    + 0.10 × norm(1 / Wind_Speed)
```

| HVI Range | Risk Tier |
|-----------|-----------|
| 0–25 | 🟢 Low |
| 26–50 | 🟡 Moderate |
| 51–75 | 🟠 High |
| 76–100 | 🔴 Severe |

---

## 📁 Project Structure

```
ThermaCity/
├── frontend/                    # React (Vite) + Mapbox GL JS
├── backend/                     # FastAPI + SQLAlchemy + PostGIS
│   ├── app/
│   │   ├── config.py            # Pydantic Settings (HVI weights, DB URL)
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── models/              # 5 ORM models with GeoAlchemy2
│   │   ├── routers/             # REST API endpoints
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── services/            # HVI calculator, ML predictor
│   └── alembic/                 # Database migrations
├── ml/                          # Machine Learning pipeline
│   ├── scripts/
│   │   ├── train_model.py       # RF training with sklearn Pipeline
│   │   └── evaluate_model.py    # RMSE, MAE, R² reporting
│   ├── models/                  # Serialized .joblib artifacts
│   └── data/                    # Training/test CSVs (gitignored)
├── gee/                         # Google Earth Engine pipelines
│   ├── scripts/
│   │   ├── 01_extract_lst.py    # Landsat 8/9 thermal data
│   │   ├── 02_extract_ndvi_ndbi.py  # Sentinel-2 spectral indices
│   │   ├── 04_extract_tree_canopy.py # ESA WorldCover 10m
│   │   └── 08_merge_features.py # Join all CSVs → training_set.csv
│   ├── utils/
│   │   ├── auth.py              # GEE authentication
│   │   ├── geometry.py          # Pune boundary + 100m grid generator
│   │   └── export.py            # Canonical reduce_to_grid() function
│   └── boundaries/
│       └── pune_boundary.geojson
├── db/
│   └── init.sql                 # PostGIS schema (5 tables + triggers)
└── docker-compose.yml           # PostgreSQL + PostGIS container
```

---

## 🗄️ Database Schema

All spatial data is stored in **PostgreSQL + PostGIS** with full geometry support:

| Table | Description | Geometry |
|-------|-------------|----------|
| `ward_boundaries` | Pune PMC administrative wards | MultiPolygon |
| `spatial_grid` | ~30,000+ analysis cells (100×100 m) | Polygon |
| `environmental_features` | Per-cell, per-year features + HVI | — (FK to grid) |
| `feature_importance` | RF model explainability scores | — |
| `community_reports` | Citizen heat reports | Point |

**Key trigger:** `trg_report_assign_spatial` automatically assigns each community report to its containing grid cell and ward via `ST_Contains` — zero application code needed.

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Python 3.11+
- Node.js 18+
- [Google Earth Engine account](https://earthengine.google.com/)

### 1. Clone & Configure

```bash
git clone https://github.com/Adds14/ThermaCity.git
cd ThermaCity
cp .env.example .env
# Edit .env with your database password and Mapbox token
```

### 2. Start the Database

```bash
docker compose up -d db
```

### 3. Run the GEE Pipeline

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

### 5. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 6. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 📊 Data Sources

| Dataset | Provider | Resolution | Use |
|---------|----------|------------|-----|
| Landsat 8/9 Collection 2 L2 | USGS/NASA | 30 m (thermal) | Land Surface Temperature |
| Sentinel-2 L2A Harmonized | ESA/Copernicus | 10 m (optical) | NDVI, NDBI, NDWI |
| ESA WorldCover v200 | ESA | 10 m | Tree canopy fraction |
| ERA5-Land | ECMWF | ~9 km | Humidity, wind speed |
| WorldPop | WorldPop | 100 m | Population density |

All raster data is aggregated to a uniform **100×100 m grid** using `ee.Reducer.mean()` through a [single canonical function](gee/utils/export.py) to guarantee spatial alignment.

---

## 🎯 Expected Dashboard Outputs

1. **City-wide Heat Vulnerability Map** — Interactive grid coloured by HVI risk tier
2. **Ward-wise Rankings** — Sortable table of Pune's most heat-vulnerable wards
3. **Temporal Heat Change Map (2021–2026)** — Year slider showing UHI expansion
4. **Citizen Report Overlay** — Clustered markers of ground-level observations
5. **Feature Importance Analysis** — Which land-cover variable drives heat where
6. **Scenario Simulator** — "What if we plant 1000 trees in Ward X?"

---

## 📈 Evaluation Metrics

| Metric | Target | Purpose |
|--------|--------|---------|
| RMSE | ≤ 2.5 °C | Primary prediction accuracy |
| MAE | ≤ 2.0 °C | Interpretable average error |
| R² | ≥ 0.75 | Variance explained by land-cover features |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 19 (Vite) + Mapbox GL JS |
| **Backend** | Python 3.11 + FastAPI |
| **Database** | PostgreSQL 16 + PostGIS 3.4 |
| **ML** | scikit-learn (Random Forest Regressor) |
| **Remote Sensing** | Google Earth Engine (Python API) |
| **Containerization** | Docker Compose |

---

## 📝 License

This project is developed as a B.Tech capstone project.

---

<div align="center">

**Built for Pune. Powered by open satellite data. Designed for climate resilience.**

</div>
