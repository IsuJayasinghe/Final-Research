-- ==============================================================================
-- 05_create_yard_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Component 3: Smart Container Yard Allocation & Space Utilization Optimization System
-- ==============================================================================

-- Yard storage blocks and terminal zone definitions
CREATE TABLE IF NOT EXISTS yard.yard_zones (
    yard_zone_id VARCHAR(50) PRIMARY KEY,
    zone_name VARCHAR(100) NOT NULL,
    capacity INTEGER,
    current_occupancy INTEGER DEFAULT 0,
    zone_status VARCHAR(30) DEFAULT 'AVAILABLE'
);

-- Container yard space allocations and tracking
CREATE TABLE IF NOT EXISTS yard.yard_allocations (
    yard_allocation_id BIGSERIAL PRIMARY KEY,
    container_id VARCHAR(30) NOT NULL REFERENCES common.containers(container_id),
    yard_zone_id VARCHAR(50) NOT NULL REFERENCES yard.yard_zones(yard_zone_id),
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    released_at TIMESTAMP,
    allocation_status VARCHAR(30) DEFAULT 'ALLOCATED'
);

-- Historical snapshots of yard block occupancy and space utilization
CREATE TABLE IF NOT EXISTS yard.yard_occupancy (
    occupancy_id BIGSERIAL PRIMARY KEY,
    yard_zone_id VARCHAR(50) NOT NULL REFERENCES yard.yard_zones(yard_zone_id),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    occupied_slots INTEGER,
    available_slots INTEGER,
    utilization_percentage NUMERIC(5, 2)
);
