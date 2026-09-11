"""
ThermaCity — Demo Data Router

Serves real AI-powered predictions directly from training_set.csv
without requiring a PostgreSQL database. Uses the loaded ML model
and HVI calculator to compute live results.

Endpoints:
  GET  /demo/grid      — GeoJSON FeatureCollection with HVI per cell
  GET  /demo/summary   — City-wide HVI statistics
  POST /demo/predict   — Single-cell LST + HVI prediction
  POST /demo/simulate  — What-if scenario simulation
"""

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.hvi_calculator import HVICalculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo"])

import threading

# ── In-memory cache (keyed by year) ────────────────────────
_cache: dict[int, dict[str, Any]] = {}
_cache_lock = threading.Lock()

def _point_to_square(geo_str: str) -> dict | None:
    """Convert a GEE point geometry to a ~100m square polygon."""
    try:
        geom = json.loads(geo_str)
        if geom.get("type") != "Point":
            return None
        lon, lat = geom["coordinates"]
        d = 0.00045  # ~50m at Pune latitude
        return {
            "type": "Polygon",
            "coordinates": [[
                [lon - d, lat - d],
                [lon + d, lat - d],
                [lon + d, lat + d],
                [lon - d, lat + d],
                [lon - d, lat - d],
            ]],
        }
    except Exception:
        return None

def _load_year(year: int) -> dict[str, Any]:
    """Lazily load, predict, and cache a year's data."""
    with _cache_lock:
        if year in _cache:
            return _cache[year]

        # Find CSV
        csv_path = Path(__file__).resolve().parent.parent.parent.parent / "ml" / "data" / "training_set.csv"
        if not csv_path.exists():
            raise HTTPException(status_code=404, detail=f"Training CSV not found at {csv_path}")

        logger.info("Loading demo data for year %d from %s …", year, csv_path)
        df = pd.read_csv(csv_path)
        df = df[df["year"] == year].reset_index(drop=True)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for year {year}")

        # ── ML Predictions ─────────────────────────────────────
        from app.main import get_ml_predictor
        predictor = get_ml_predictor()

        if predictor:
            features = df[["ndvi", "ndbi", "ndwi", "tree_canopy_frac"]].to_dict("records")
            lst_predictions = predictor.predict_batch(features)
            df["lst_predicted"] = lst_predictions
        else:
            df["lst_predicted"] = df["lst_observed"]

        # ── HVI Calculation ────────────────────────────────────
        hvi_rows = []
        for _, row in df.iterrows():
            hvi_rows.append({
                "lst_predicted": row["lst_predicted"],
                "humidity": 55.0,
                "wind_speed": 2.0,
                "population_density": 10000.0,
                "tree_canopy_frac": row.get("tree_canopy_frac", 0.0),
            })

        hvi_results = HVICalculator.compute_batch(hvi_rows)
        df["hvi_score"] = [r["hvi_score"] for r in hvi_results]
        df["hvi_tier"] = [r["hvi_tier"] for r in hvi_results]

        # ── Build GeoJSON features ─────────────────────────────
        geojson_features = []
        for idx, row in df.iterrows():
            poly = _point_to_square(row.get(".geo", "{}"))
            if not poly:
                continue
            geojson_features.append({
                "type": "Feature",
                "geometry": poly,
                "properties": {
                    "cell_id": idx,
                    "lst_observed": round(float(row["lst_observed"]), 2) if pd.notna(row["lst_observed"]) else None,
                    "lst_predicted": round(float(row["lst_predicted"]), 2),
                    "ndvi": round(float(row["ndvi"]), 4) if pd.notna(row["ndvi"]) else None,
                    "ndbi": round(float(row["ndbi"]), 4) if pd.notna(row["ndbi"]) else None,
                    "ndwi": round(float(row["ndwi"]), 4) if pd.notna(row["ndwi"]) else None,
                    "tree_canopy_frac": round(float(row["tree_canopy_frac"]), 4) if pd.notna(row["tree_canopy_frac"]) else None,
                    "hvi_score": float(row["hvi_score"]),
                    "hvi_tier": row["hvi_tier"],
                },
            })

        # ── Build summary ──────────────────────────────────────
        tier_counts = df["hvi_tier"].value_counts().to_dict()
        summary = {
            "year": year,
            "total_cells": len(df),
            "avg_hvi": round(float(df["hvi_score"].mean()), 2),
            "max_hvi": round(float(df["hvi_score"].max()), 2),
            "min_hvi": round(float(df["hvi_score"].min()), 2),
            "avg_lst": round(float(df["lst_predicted"].mean()), 2),
            "tier_distribution": tier_counts,
            "emergency_cells": int(tier_counts.get("Emergency", 0)),
            "high_risk_cells": int(tier_counts.get("Stressed", 0)) + int(tier_counts.get("Emergency", 0)),
        }

        # ── Cache baseline averages for simulation ─────────────
        baseline = {
            "ndvi": float(df["ndvi"].mean()),
            "ndbi": float(df["ndbi"].mean()),
            "ndwi": float(df["ndwi"].mean()),
            "tree_canopy_frac": float(df["tree_canopy_frac"].mean()),
        }

        # ── Cache feature ranges for accurate simulation ───────────
        feature_ranges = {
            "lst_min": float(df["lst_predicted"].min()),
            "lst_max": float(df["lst_predicted"].max()),
            "canopy_min": float(df["tree_canopy_frac"].min()),
            "canopy_max": float(df["tree_canopy_frac"].max()),
        }

        result = {
            "geojson": {"type": "FeatureCollection", "features": geojson_features},
            "summary": summary,
            "baseline": baseline,
            "ranges": feature_ranges,
        }
        _cache[year] = result
        logger.info("Demo data cached for year %d: %d cells", year, len(geojson_features))
        return result


# ── Endpoints ──────────────────────────────────────────────

from fastapi.responses import ORJSONResponse

@router.get("/grid", response_class=ORJSONResponse)
def get_grid(
    year: int = Query(2024, ge=2021, le=2026),
    limit: int = Query(36000, ge=1, le=50000),
    bbox: str = Query(None, description="minLon,minLat,maxLon,maxLat"),
):
    """Return grid cells as GeoJSON for the map."""
    data = _load_year(year)
    features = data["geojson"]["features"]
    
    if bbox:
        try:
            minLon, minLat, maxLon, maxLat = map(float, bbox.split(","))
            filtered = []
            for f in features:
                # Approximate bounding box check using the first coordinate of the polygon
                coord = f["geometry"]["coordinates"][0][0]
                lon, lat = coord[0], coord[1]
                if minLon <= lon <= maxLon and minLat <= lat <= maxLat:
                    filtered.append(f)
            features = filtered
        except Exception:
            pass

    if len(features) > limit:
        features = features[:limit]

    return {
        "type": "FeatureCollection",
        "features": features,
    }



@router.get("/summary")
def get_summary(year: int = Query(2024, ge=2021, le=2026)):
    """Return city-wide HVI statistics."""
    data = _load_year(year)
    return data["summary"]


# ── Ward Data (41 official PMC wards) ──────────────────────
WARD_DATA = [
    {"id": 1, "name": "Kalas–Dhanori–Lohegaon", "lat": 18.5838, "lng": 73.9057},
    {"id": 2, "name": "Phulenagar–Nagpur Chawl", "lat": 18.5507, "lng": 73.8626},
    {"id": 3, "name": "Viman Nagar–Lohegaon", "lat": 18.5674, "lng": 73.9147},
    {"id": 4, "name": "Kharadi–Wagholi", "lat": 18.5562, "lng": 73.9608},
    {"id": 5, "name": "Kalyani Nagar–Vadgaonsheri", "lat": 18.5508, "lng": 73.9140},
    {"id": 6, "name": "Yerawada–Gandhinagar", "lat": 18.5481, "lng": 73.8795},
    {"id": 7, "name": "Gokhalenagar–Wakdewadi", "lat": 18.5397, "lng": 73.8320},
    {"id": 8, "name": "Aundh–Bopodi", "lat": 18.5600, "lng": 73.8204},
    {"id": 9, "name": "Sus–Baner–Pashan", "lat": 18.5527, "lng": 73.7880},
    {"id": 10, "name": "Bavdhan–Bhusari Colony", "lat": 18.5200, "lng": 73.7768},
    {"id": 11, "name": "Rambaug Colony–Shivteerthnagar", "lat": 18.5028, "lng": 73.8075},
    {"id": 12, "name": "Shivajinagar–Model Colony", "lat": 18.5295, "lng": 73.8385},
    {"id": 13, "name": "Pune Station–Jay Jawan Nagar", "lat": 18.5280, "lng": 73.8795},
    {"id": 14, "name": "Koregaon Park–Ghorpadi–Mundhwa", "lat": 18.5318, "lng": 73.8990},
    {"id": 15, "name": "Manjri Budruk–Keshavnagar–Sadesatranali", "lat": 18.5215, "lng": 73.9445},
    {"id": 16, "name": "Hadapsar–Sasane Nagar", "lat": 18.5015, "lng": 73.9280},
    {"id": 17, "name": "Wanowrie–Salunke Vihar", "lat": 18.4935, "lng": 73.9060},
    {"id": 18, "name": "Fatimanagar–Wanwadi", "lat": 18.4880, "lng": 73.9000},
    {"id": 19, "name": "Keshav Nagar–Mundhwa", "lat": 18.5280, "lng": 73.9340},
    {"id": 20, "name": "Shankar Maharaj Math–Bibwewadi", "lat": 18.4730, "lng": 73.8570},
    {"id": 21, "name": "Mukundnagar–Salisbury Park", "lat": 18.4930, "lng": 73.8730},
    {"id": 22, "name": "Kashewadi–Dias Plot", "lat": 18.5030, "lng": 73.8620},
    {"id": 23, "name": "Rawiwar Peth–Nana Peth", "lat": 18.5150, "lng": 73.8580},
    {"id": 24, "name": "Kasba Ganpati–Kamla Nehru Hospital–KEM", "lat": 18.5190, "lng": 73.8620},
    {"id": 25, "name": "Shaniwar Peth–Mahatma Phule Mandai", "lat": 18.5140, "lng": 73.8520},
    {"id": 26, "name": "Ghorpade Peth–Guruwar Peth–Samta Bhoomi", "lat": 18.5080, "lng": 73.8540},
    {"id": 27, "name": "Navi Peth–Parvati", "lat": 18.4960, "lng": 73.8440},
    {"id": 28, "name": "Janta Vasahat–Hingane Khurd", "lat": 18.4750, "lng": 73.8310},
    {"id": 29, "name": "Deccan Gymkhana–Happy Colony", "lat": 18.5180, "lng": 73.8310},
    {"id": 30, "name": "Karvenagar–Hingne Home Colony", "lat": 18.4870, "lng": 73.8160},
    {"id": 31, "name": "Mayur Colony–Kothrud", "lat": 18.5070, "lng": 73.8070},
    {"id": 32, "name": "Warje–Popular Nagar", "lat": 18.4810, "lng": 73.7830},
    {"id": 33, "name": "Shivane–Khadakwasla–Dhayari", "lat": 18.4480, "lng": 73.7880},
    {"id": 34, "name": "Vadgaon Budruk–Dhayari", "lat": 18.4610, "lng": 73.8210},
    {"id": 35, "name": "Suncity–Manikbaug", "lat": 18.4700, "lng": 73.8360},
    {"id": 36, "name": "Sahakarnagar–Padmavati", "lat": 18.4780, "lng": 73.8530},
    {"id": 37, "name": "Dhankawadi–Katraj Dairy", "lat": 18.4550, "lng": 73.8610},
    {"id": 38, "name": "Balajinagar–Ambegaon–Katraj", "lat": 18.4460, "lng": 73.8680},
    {"id": 39, "name": "Upper–Super Indiranagar", "lat": 18.4750, "lng": 73.8850},
    {"id": 40, "name": "Kondhwa Budruk–Yeolewadi", "lat": 18.4630, "lng": 73.8960},
    {"id": 41, "name": "Mohammadwadi–Undri", "lat": 18.4720, "lng": 73.9140},
]


@router.get("/ward-summary")
def get_ward_summary(year: int = Query(2024, ge=2021, le=2026)):
    """
    Return per-ward aggregate HVI statistics.

    For each of the 41 official wards, computes a ~1 km bounding box around
    its center and averages the HVI scores of grid cells falling inside.
    """
    data = _load_year(year)
    features = data["geojson"]["features"]

    RADIUS = 0.009  # ~1 km in degrees at Pune latitude

    result = []
    for ward in WARD_DATA:
        lat, lng = ward["lat"], ward["lng"]
        min_lat, max_lat = lat - RADIUS, lat + RADIUS
        min_lng, max_lng = lng - RADIUS, lng + RADIUS

        # Filter grid cells within the ward's bounding box
        ward_cells = []
        for f in features:
            coord = f["geometry"]["coordinates"][0][0]
            flon, flat = coord[0], coord[1]
            if min_lng <= flon <= max_lng and min_lat <= flat <= max_lat:
                ward_cells.append(f["properties"])

        if ward_cells:
            avg_hvi = sum(c["hvi_score"] for c in ward_cells) / len(ward_cells)
            avg_lst = sum((c.get("lst_predicted") or 0) for c in ward_cells) / len(ward_cells)
            # Determine tier from average HVI (0-100 scale)
            if avg_hvi >= 76:
                tier = "Emergency"
            elif avg_hvi >= 51:
                tier = "Stressed"
            elif avg_hvi >= 26:
                tier = "Caution"
            else:
                tier = "Heat-Safe"
        else:
            avg_hvi = 0.0
            avg_lst = 0.0
            tier = "Heat-Safe"

        result.append({
            "ward_id": ward["id"],
            "ward_name": ward["name"],
            "lat": ward["lat"],
            "lng": ward["lng"],
            "avg_hvi": round(avg_hvi, 2),
            "avg_lst": round(avg_lst, 2),
            "cell_count": len(ward_cells),
            "hvi_tier": tier,
        })

    return result


class PredictRequest(BaseModel):
    ndvi: float
    ndbi: float
    ndwi: float
    tree_canopy_frac: float


@router.post("/predict")
def predict_single(req: PredictRequest):
    """Predict LST and HVI for a single set of features."""
    from app.main import get_ml_predictor
    predictor = get_ml_predictor()
    if not predictor:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    lst = predictor.predict_lst(req.model_dump())

    hvi = HVICalculator.compute_single(
        lst=lst / 60.0,           # rough normalisation to [0,1]
        humidity=0.5,
        wind_speed=0.5,
        population_density=0.5,
        tree_canopy_frac=1.0 - req.tree_canopy_frac,  # canopy deficit
    )

    return {
        "lst_predicted": round(lst, 2),
        "hvi_score": hvi["hvi_score"],
        "hvi_tier": hvi["hvi_tier"],
    }


class SimulateRequest(BaseModel):
    ndvi_delta: float = 0.0
    ndbi_delta: float = 0.0
    ndwi_delta: float = 0.0
    tree_canopy_delta: float = 0.0
    year: int = 2024
    baseline_ndvi: float | None = None
    baseline_ndbi: float | None = None
    baseline_ndwi: float | None = None
    baseline_tree_canopy_frac: float | None = None
    baseline_lst: float | None = None
    baseline_hvi_score: float | None = None
    baseline_hvi_tier: str | None = None


@router.post("/simulate")
def simulate(req: SimulateRequest):
    """Run a what-if scenario against a specific cell baseline or city average."""
    from app.main import get_ml_predictor
    predictor = get_ml_predictor()
    if not predictor:
        raise HTTPException(status_code=503, detail="ML model not loaded")

    # Use provided baseline or fallback to city average
    data = _load_year(req.year)
    ranges = data.get("ranges", {
        "lst_min": 25.0, "lst_max": 45.0, "canopy_min": 0.0, "canopy_max": 1.0
    })

    if req.baseline_ndvi is not None:
        baseline = {
            "ndvi": req.baseline_ndvi,
            "ndbi": req.baseline_ndbi or 0.0,
            "ndwi": req.baseline_ndwi or 0.0,
            "tree_canopy_frac": req.baseline_tree_canopy_frac or 0.0,
        }
    else:
        baseline = data["baseline"]

    # Baseline LST
    if req.baseline_lst is not None:
        baseline_lst = req.baseline_lst
    else:
        baseline_lst = predictor.predict_lst(baseline)

    # Simulated prediction
    sim_features = {
        "ndvi": baseline["ndvi"] + req.ndvi_delta,
        "ndbi": baseline["ndbi"] + req.ndbi_delta,
        "ndwi": baseline["ndwi"] + req.ndwi_delta,
        "tree_canopy_frac": max(0.0, min(1.0, baseline["tree_canopy_frac"] + req.tree_canopy_delta)),
    }
    sim_lst = predictor.predict_lst(sim_features)

    # Calculate delta for LST and Canopy
    lst_delta = sim_lst - baseline_lst
    canopy_delta = sim_features["tree_canopy_frac"] - baseline["tree_canopy_frac"]

    lst_range = max(1e-12, ranges["lst_max"] - ranges["lst_min"])
    canopy_range = max(1e-12, ranges["canopy_max"] - ranges["canopy_min"])

    # Normalised deltas
    delta_norm_lst = lst_delta / lst_range
    # Canopy deficit is 1 - canopy_frac. Delta of (1-canopy) is -canopy_delta.
    delta_norm_canopy = -canopy_delta / canopy_range

    hvi_score_delta = (
        0.35 * delta_norm_lst +
        0.20 * delta_norm_canopy
    ) * 100.0

    # Determine baseline score and tier
    if req.baseline_hvi_score is not None:
        baseline_score = req.baseline_hvi_score
        baseline_tier = req.baseline_hvi_tier or HVICalculator._assign_tier(baseline_score)
    else:
        # Reconstruct baseline score roughly using city average values
        baseline_score = data["summary"]["avg_hvi"]
        baseline_tier = HVICalculator._assign_tier(baseline_score)

    sim_score = max(0.0, min(100.0, baseline_score + hvi_score_delta))
    sim_tier = HVICalculator._assign_tier(sim_score)

    return {
        "baseline": {
            "lst": round(baseline_lst, 2),
            "hvi_score": round(baseline_score, 2),
            "hvi_tier": baseline_tier,
        },
        "simulated": {
            "lst": round(sim_lst, 2),
            "hvi_score": round(sim_score, 2),
            "hvi_tier": sim_tier,
        },
        "lst_delta": round(float(lst_delta), 2),
        "hvi_delta": round(float(hvi_score_delta), 2),
    }


# ── SHAP Explainability ───────────────────────────────────────

_explainer_instance = None


def _get_explainer():
    """Lazily initialize the SHAP explainer."""
    global _explainer_instance
    if _explainer_instance is None:
        from app.main import get_ml_predictor
        predictor = get_ml_predictor()
        if predictor:
            from app.services.explainability import Explainer
            _explainer_instance = Explainer(predictor)
    return _explainer_instance


@router.post("/explain")
def explain_cell(req: PredictRequest):
    """Explain why a cell has its predicted temperature using SHAP."""
    explainer = _get_explainer()
    if not explainer:
        raise HTTPException(status_code=503, detail="SHAP explainer not available")

    result = explainer.explain_cell(req.model_dump())
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


from fastapi.responses import Response

class CellReportRequest(BaseModel):
    cell_id: int
    year: int
    baseline_lst: float
    baseline_ndvi: float
    baseline_ndbi: float
    baseline_hvi_score: float
    baseline_hvi_tier: str
    simulated_lst: float | None = None
    simulated_hvi_tier: str | None = None
    lst_delta: float | None = None
    applied_canopy_delta: float | None = None
    applied_ndbi_delta: float | None = None

@router.post("/report/cell")
def generate_cell_pdf(req: CellReportRequest):
    """Generate a PDF report for a specific grid cell."""
    from app.services.report_generator import generate_cell_report
    pdf_bytes = generate_cell_report(req.model_dump())
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=thermacity_block_{req.cell_id}.pdf"
        }
    )

