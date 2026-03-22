-- ============================================
-- Ahmedabad Urban Environmental Database Schema
-- Cleaned satellite data for LST, NDVI, NO2
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Land Surface Temperature (LST) - Cleaned Data
-- Range: 16.75 to 47.92°C
CREATE TABLE IF NOT EXISTS areas_lst (
    id SERIAL PRIMARY KEY,
    area VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    lst NUMERIC(15, 10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_lst_area_date UNIQUE(area, date),
    CONSTRAINT positive_lst CHECK (lst >= 0)
);

-- Normalized Difference Vegetation Index (NDVI) - Cleaned Data
-- Range: -0.117 to 0.607
CREATE TABLE IF NOT EXISTS areas_ndvi (
    id SERIAL PRIMARY KEY,
    area VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    ndvi NUMERIC(15, 10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_ndvi_area_date UNIQUE(area, date),
    CONSTRAINT ndvi_range CHECK (ndvi >= -1 AND ndvi <= 1)
);

-- Nitrogen Dioxide (NO2) - Cleaned Data
-- Range: 0.000017 to 0.000920 ppb
CREATE TABLE IF NOT EXISTS areas_no2 (
    id SERIAL PRIMARY KEY,
    area VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    no2 NUMERIC(15, 10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_no2_area_date UNIQUE(area, date),
    CONSTRAINT positive_no2 CHECK (no2 >= 0)
);

-- ============================================
-- Performance Indexes
-- ============================================

-- LST Table Indexes
CREATE INDEX IF NOT EXISTS idx_lst_area ON areas_lst(area);
CREATE INDEX IF NOT EXISTS idx_lst_date ON areas_lst(date);
CREATE INDEX IF NOT EXISTS idx_lst_area_date ON areas_lst(area, date);

-- NDVI Table Indexes
CREATE INDEX IF NOT EXISTS idx_ndvi_area ON areas_ndvi(area);
CREATE INDEX IF NOT EXISTS idx_ndvi_date ON areas_ndvi(date);
CREATE INDEX IF NOT EXISTS idx_ndvi_area_date ON areas_ndvi(area, date);

-- NO2 Table Indexes
CREATE INDEX IF NOT EXISTS idx_no2_area ON areas_no2(area);
CREATE INDEX IF NOT EXISTS idx_no2_date ON areas_no2(date);
CREATE INDEX IF NOT EXISTS idx_no2_area_date ON areas_no2(area, date);

-- ============================================
-- Grant Permissions
-- ============================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO urban_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO urban_admin;

-- Log initialization completion
SELECT 'Ahmedabad Urban Environmental Database initialized successfully' as status;