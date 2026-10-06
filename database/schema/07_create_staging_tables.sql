-- ==============================================================================
-- 07_create_staging_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Staging Schema: Landing Zone for Raw Research Data Ingestion
-- ==============================================================================

-- Raw staging table for internal drayage truck movements and dispatch jobs
CREATE TABLE IF NOT EXISTS staging.truck_details (
    job_id VARCHAR(50),
    vessel_id VARCHAR(150),
    container_id VARCHAR(30),
    truck_id VARCHAR(50),
    vehicle_type VARCHAR(100),
    driver_id VARCHAR(50),
    event_timestamp TIMESTAMP,
    start_zone VARCHAR(100),
    destination_zone VARCHAR(100),
    distance_meters NUMERIC(10, 2),
    route_id VARCHAR(50)
);

-- Raw staging table for container yard transitions and gate-in records
CREATE TABLE IF NOT EXISTS staging.container_yard_data (
    job_id VARCHAR(50),
    container_id VARCHAR(30),
    container_size VARCHAR(20),
    container_type VARCHAR(50),
    shipping_line VARCHAR(100),
    weight_category VARCHAR(50),
    cargo_type VARCHAR(100),
    vessel_id VARCHAR(150),
    gate_in_timestamp TIMESTAMP,
    start_terminal_zone VARCHAR(100),
    destination_yard_zone VARCHAR(100),
    vehicle_type VARCHAR(100),
    route_id VARCHAR(50)
);

-- Raw staging table for physical berth infrastructure and crane specifications
CREATE TABLE IF NOT EXISTS staging.berth_characteristics (
    instance_id VARCHAR(50),
    terminal_name VARCHAR(150),
    berth_id VARCHAR(50),
    max_length_m NUMERIC(8, 2),
    max_draft_m NUMERIC(6, 2),
    crane_count INTEGER,
    crane_handling_rate NUMERIC(8, 2)
);

-- Raw staging table for historical AIS telemetry and meteorological observations
CREATE TABLE IF NOT EXISTS staging.vessel_historical_data (
    mmsi VARCHAR(30),
    imo_number VARCHAR(30),
    vessel_name VARCHAR(150),
    vessel_type VARCHAR(100),
    base_datetime TIMESTAMP,
    latitude NUMERIC(10, 6),
    longitude NUMERIC(10, 6),
    sog NUMERIC(8, 2),
    cog NUMERIC(8, 2),
    distance_to_port_nmi NUMERIC(10, 2),
    draft_m NUMERIC(8, 2),
    wind_speed_knots NUMERIC(8, 2),
    wave_height_m NUMERIC(8, 2),
    actual_remaining_hours NUMERIC(10, 2)
);
