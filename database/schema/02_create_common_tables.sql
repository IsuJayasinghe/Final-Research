-- ==============================================================================
-- 02_create_common_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Common Schema: Shared Core Dimension Entities
-- ==============================================================================

-- Vessels registry
CREATE TABLE IF NOT EXISTS common.vessels (
    vessel_id VARCHAR(100) PRIMARY KEY,
    imo_number VARCHAR(20),
    mmsi VARCHAR(20),
    vessel_name VARCHAR(150),
    vessel_type VARCHAR(100)
);

-- Containers registry
CREATE TABLE IF NOT EXISTS common.containers (
    container_id VARCHAR(30) PRIMARY KEY,
    container_size VARCHAR(20),
    container_type VARCHAR(50),
    shipping_line VARCHAR(100),
    weight_category VARCHAR(50),
    cargo_type VARCHAR(100)
);

-- Internal terminal transport routes
CREATE TABLE IF NOT EXISTS common.routes (
    route_id VARCHAR(50) PRIMARY KEY,
    route_name VARCHAR(150),
    start_zone VARCHAR(100),
    destination_zone VARCHAR(100),
    distance_meters NUMERIC(10, 2),
    is_active BOOLEAN DEFAULT TRUE
);
