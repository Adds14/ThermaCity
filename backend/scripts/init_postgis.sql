-- ============================================================
-- ThermaCity — Supabase PostGIS Initialisation
-- ============================================================
-- Run this in the Supabase SQL Editor (or via psql) to set up
-- the spatial tables for the 100×100 m Pune heat-vulnerability grid.
-- ============================================================

-- 1. Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Core grid table — one row per 100m cell
CREATE TABLE IF NOT EXISTS spatial_grid (
    id            SERIAL PRIMARY KEY,
    cell_code     VARCHAR(50) NOT NULL UNIQUE,
    ward_id       INTEGER,
    centroid_lat  DOUBLE PRECISION,
    centroid_lng  DOUBLE PRECISION,
    geom          GEOMETRY(Polygon, 4326) NOT NULL
);

-- Spatial index for blazing-fast bbox queries
CREATE INDEX IF NOT EXISTS idx_grid_geom
    ON spatial_grid USING GIST (geom);

-- 3. Environmental features — one row per cell per year
CREATE TABLE IF NOT EXISTS environmental_features (
    id                  SERIAL PRIMARY KEY,
    grid_id             INTEGER NOT NULL REFERENCES spatial_grid(id) ON DELETE CASCADE,
    year                SMALLINT NOT NULL,

    -- Satellite indices (from GEE pipeline)
    lst_observed        DOUBLE PRECISION,
    ndvi                DOUBLE PRECISION,
    ndbi                DOUBLE PRECISION,
    ndwi                DOUBLE PRECISION,
    tree_canopy_frac    DOUBLE PRECISION,

    -- Climate reanalysis
    humidity            DOUBLE PRECISION,
    wind_speed          DOUBLE PRECISION,

    -- Demographics
    population_density  DOUBLE PRECISION,

    -- ML predictions
    lst_predicted       DOUBLE PRECISION,

    -- Computed HVI
    hvi_score           DOUBLE PRECISION,
    hvi_tier            VARCHAR(15),

    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT uq_grid_year      UNIQUE (grid_id, year),
    CONSTRAINT ck_year_range      CHECK  (year BETWEEN 2020 AND 2030),
    CONSTRAINT ck_canopy_range    CHECK  (tree_canopy_frac IS NULL OR tree_canopy_frac BETWEEN 0.0 AND 1.0),
    CONSTRAINT ck_hvi_range       CHECK  (hvi_score IS NULL OR hvi_score BETWEEN 0 AND 100),
    CONSTRAINT ck_hvi_tier        CHECK  (hvi_tier IS NULL OR hvi_tier IN ('Heat-Safe', 'Caution', 'Stressed', 'Emergency'))
);

CREATE INDEX IF NOT EXISTS idx_envfeat_grid_year ON environmental_features (grid_id, year);
CREATE INDEX IF NOT EXISTS idx_envfeat_year       ON environmental_features (year);
CREATE INDEX IF NOT EXISTS idx_envfeat_hvi        ON environmental_features (hvi_score);
CREATE INDEX IF NOT EXISTS idx_envfeat_tier       ON environmental_features (hvi_tier);

-- 4. Enable RLS (Supabase best practice for public schema)
ALTER TABLE spatial_grid ENABLE ROW LEVEL SECURITY;
ALTER TABLE environmental_features ENABLE ROW LEVEL SECURITY;

-- Allow read-only access for anon/authenticated (public dashboard)
CREATE POLICY "Public read spatial_grid"
    ON spatial_grid FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Public read environmental_features"
    ON environmental_features FOR SELECT
    TO anon, authenticated
    USING (true);

-- Grant access to the roles
GRANT SELECT ON spatial_grid TO anon, authenticated;
GRANT SELECT ON environmental_features TO anon, authenticated;

-- ============================================================
-- Done! Tables ready for data migration.
-- ============================================================
