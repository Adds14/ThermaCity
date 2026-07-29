-- ============================================================
-- ThermaCity — PostGIS Schema Initialization
-- Run automatically by Docker on first container startup
-- ============================================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- ─────────────────────────────────────────────────
-- 1. Ward Boundaries (must exist first — referenced by FK)
-- ─────────────────────────────────────────────────
-- Source: DataMeet GitHub — Municipal_Spatial_Data (Pune PMC wards)
CREATE TABLE ward_boundaries (
    id          SERIAL PRIMARY KEY,
    ward_name   VARCHAR(100) NOT NULL,
    ward_code   VARCHAR(20) UNIQUE,
    zone_name   VARCHAR(100),           -- PMC administrative zone
    area_sq_km  REAL,                   -- computed from geometry
    geom        GEOMETRY(MultiPolygon, 4326) NOT NULL
);

CREATE INDEX idx_ward_geom ON ward_boundaries USING GIST(geom);

COMMENT ON TABLE ward_boundaries IS
    'Pune Municipal Corporation administrative ward polygons (DataMeet source)';

-- ─────────────────────────────────────────────────
-- 2. Spatial Grid (100×100 m cells covering Pune)
-- ─────────────────────────────────────────────────
CREATE TABLE spatial_grid (
    id          SERIAL PRIMARY KEY,
    cell_code   VARCHAR(20) UNIQUE NOT NULL,     -- e.g. "PUNE_R0042_C0117"
    ward_id     INTEGER REFERENCES ward_boundaries(id)
                ON DELETE SET NULL,
    centroid_lat DOUBLE PRECISION,               -- cell centroid for quick lookups
    centroid_lng DOUBLE PRECISION,
    geom        GEOMETRY(Polygon, 4326) NOT NULL
);

CREATE INDEX idx_grid_geom ON spatial_grid USING GIST(geom);
CREATE INDEX idx_grid_ward ON spatial_grid(ward_id);

COMMENT ON TABLE spatial_grid IS
    '100×100 m analysis grid cells. Each cell is the atomic spatial unit for all features and HVI computation.';

-- ─────────────────────────────────────────────────
-- 3. Environmental Features (per cell, per year)
-- ─────────────────────────────────────────────────
CREATE TABLE environmental_features (
    id                  SERIAL PRIMARY KEY,
    grid_id             INTEGER NOT NULL
                        REFERENCES spatial_grid(id) ON DELETE CASCADE,
    year                SMALLINT NOT NULL CHECK (year BETWEEN 2020 AND 2030),

    -- Satellite-derived features (from GEE pipeline)
    lst_observed        REAL,           -- Landsat 8/9 LST (°C), hot-season median
    ndvi                REAL,           -- Sentinel-2 NDVI (-1 to 1)
    ndbi                REAL,           -- Sentinel-2 NDBI (-1 to 1)
    ndwi                REAL,           -- Sentinel-2 NDWI (-1 to 1)
    tree_canopy_frac    REAL CHECK (tree_canopy_frac BETWEEN 0.0 AND 1.0),
                                        -- ESA WorldCover tree cover fraction

    -- Climate reanalysis (ERA5-Land, hot-season mean)
    humidity            REAL,           -- Relative humidity (%)
    wind_speed          REAL,           -- Wind speed (m/s)

    -- Demographics (WorldPop)
    population_density  REAL,           -- persons / km²

    -- ML model output
    lst_predicted       REAL,           -- Random Forest prediction (°C)

    -- Computed Heat Vulnerability Index
    hvi_score           REAL CHECK (hvi_score BETWEEN 0 AND 100),
    hvi_tier            VARCHAR(10) CHECK (hvi_tier IN ('Low', 'Moderate', 'High', 'Severe')),

    -- Metadata
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(grid_id, year)
);

CREATE INDEX idx_envfeat_grid_year ON environmental_features(grid_id, year);
CREATE INDEX idx_envfeat_year ON environmental_features(year);
CREATE INDEX idx_envfeat_hvi ON environmental_features(hvi_score);
CREATE INDEX idx_envfeat_tier ON environmental_features(hvi_tier);

COMMENT ON TABLE environmental_features IS
    'Per-cell, per-year environmental features extracted from GEE, plus ML predictions and computed HVI.';

-- ─────────────────────────────────────────────────
-- 4. Feature Importance (per model version)
-- ─────────────────────────────────────────────────
CREATE TABLE feature_importance (
    id                  SERIAL PRIMARY KEY,
    model_version       VARCHAR(20) NOT NULL,     -- e.g. "v1", "v2"
    feature_name        VARCHAR(50) NOT NULL,     -- e.g. "ndvi", "ndbi"
    importance_score    REAL NOT NULL CHECK (importance_score >= 0),
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(model_version, feature_name)
);

COMMENT ON TABLE feature_importance IS
    'Random Forest feature importance scores for model explainability (one row per feature per model version).';

-- ─────────────────────────────────────────────────
-- 5. Community Reports (citizen-submitted)
-- ─────────────────────────────────────────────────
CREATE TABLE community_reports (
    id              SERIAL PRIMARY KEY,
    category        VARCHAR(50) NOT NULL CHECK (category IN (
                        'extreme_heat',
                        'lack_of_shade',
                        'hot_pavement',
                        'bus_stop_no_shade',
                        'water_fountain_unavailable',
                        'cooling_shelter_closed'
                    )),
    description     TEXT,
    severity        SMALLINT NOT NULL CHECK (severity BETWEEN 1 AND 5),
    reporter_name   VARCHAR(100),           -- optional
    photo_url       VARCHAR(500),           -- optional future use

    -- Auto-assigned via ST_Contains on insert
    grid_id         INTEGER REFERENCES spatial_grid(id)
                    ON DELETE SET NULL,
    ward_id         INTEGER REFERENCES ward_boundaries(id)
                    ON DELETE SET NULL,

    -- Moderation
    is_verified     BOOLEAN DEFAULT FALSE,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    geom            GEOMETRY(Point, 4326) NOT NULL
);

CREATE INDEX idx_reports_geom ON community_reports USING GIST(geom);
CREATE INDEX idx_reports_category ON community_reports(category);
CREATE INDEX idx_reports_ward ON community_reports(ward_id);
CREATE INDEX idx_reports_created ON community_reports(created_at DESC);
CREATE INDEX idx_reports_verified ON community_reports(is_verified);

COMMENT ON TABLE community_reports IS
    'Geo-tagged citizen reports of heat-related infrastructure gaps. Auto-assigned to grid cell and ward via spatial join.';

-- ─────────────────────────────────────────────────
-- Helper: Trigger to auto-update `updated_at`
-- ─────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_envfeat_updated_at
    BEFORE UPDATE ON environmental_features
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ─────────────────────────────────────────────────
-- Helper: Function to auto-assign grid/ward on report insert
-- ─────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION assign_report_spatial_refs()
RETURNS TRIGGER AS $$
BEGIN
    -- Assign to nearest containing grid cell
    SELECT id INTO NEW.grid_id
    FROM spatial_grid
    WHERE ST_Contains(geom, NEW.geom)
    LIMIT 1;

    -- Assign to containing ward
    SELECT id INTO NEW.ward_id
    FROM ward_boundaries
    WHERE ST_Contains(geom, NEW.geom)
    LIMIT 1;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_report_assign_spatial
    BEFORE INSERT ON community_reports
    FOR EACH ROW
    EXECUTE FUNCTION assign_report_spatial_refs();
