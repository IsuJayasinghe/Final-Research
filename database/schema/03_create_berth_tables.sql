-- ==============================================================================
-- 03_create_berth_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Component 1: Smart Dynamic Berth Allocation System
-- ==============================================================================

-- Physical berths and handling infrastructure
CREATE TABLE IF NOT EXISTS berth.berths (
    berth_id VARCHAR(50) PRIMARY KEY,
    instance_id VARCHAR(50),
    terminal_name VARCHAR(150) NOT NULL,
    max_length_m NUMERIC(8, 2),
    max_draft_m NUMERIC(6, 2),
    crane_count INTEGER,
    crane_handling_rate NUMERIC(8, 2)
);

-- Spatio-temporal vessel tracking and AIS telemetry with meteo-oceanographic factors
CREATE TABLE IF NOT EXISTS berth.vessel_tracking (
    tracking_id BIGSERIAL PRIMARY KEY,
    vessel_id VARCHAR(100) REFERENCES common.vessels(vessel_id),
    base_datetime TIMESTAMP NOT NULL,
    latitude NUMERIC(10, 6),
    longitude NUMERIC(10, 6),
    sog NUMERIC(6, 2),
    cog NUMERIC(6, 2),
    distance_to_port_nmi NUMERIC(10, 2),
    draft_m NUMERIC(6, 2),
    wind_speed_knots NUMERIC(6, 2),
    wave_height_m NUMERIC(6, 2),
    actual_remaining_hours NUMERIC(8, 2)
);

-- Machine Learning vessel ETA predictions
CREATE TABLE IF NOT EXISTS berth.eta_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    vessel_id VARCHAR(100) NOT NULL REFERENCES common.vessels(vessel_id),
    predicted_remaining_hours NUMERIC(8, 2),
    predicted_eta TIMESTAMP,
    model_version VARCHAR(50),
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dynamic berth allocations and schedule assignments
CREATE TABLE IF NOT EXISTS berth.berth_allocations (
    allocation_id BIGSERIAL PRIMARY KEY,
    vessel_id VARCHAR(100) NOT NULL REFERENCES common.vessels(vessel_id),
    berth_id VARCHAR(50) NOT NULL REFERENCES berth.berths(berth_id),
    planned_arrival TIMESTAMP,
    planned_departure TIMESTAMP,
    actual_arrival TIMESTAMP,
    actual_departure TIMESTAMP,
    allocation_status VARCHAR(30)
);
