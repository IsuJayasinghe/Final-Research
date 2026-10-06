-- ==============================================================================
-- 04_create_drayage_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Component 2: Intelligent Drayage Truck Optimization System
-- ==============================================================================

-- Terminal truck drivers (human operators)
CREATE TABLE IF NOT EXISTS drayage.drivers (
    driver_id VARCHAR(50) PRIMARY KEY,
    driver_name VARCHAR(150),
    phone_number VARCHAR(30),
    status VARCHAR(30) DEFAULT 'AVAILABLE'
);

-- Terminal drayage trucks / prime movers
CREATE TABLE IF NOT EXISTS drayage.trucks (
    truck_id VARCHAR(50) PRIMARY KEY,
    vehicle_type VARCHAR(100),
    current_status VARCHAR(30) DEFAULT 'AVAILABLE',
    current_latitude NUMERIC(10, 6),
    current_longitude NUMERIC(10, 6),
    current_driver_id VARCHAR(50) REFERENCES drayage.drivers(driver_id)
);

-- Internal horizontal transport tasks
CREATE TABLE IF NOT EXISTS drayage.transport_tasks (
    task_id VARCHAR(50) PRIMARY KEY,
    vessel_id VARCHAR(100) REFERENCES common.vessels(vessel_id),
    container_id VARCHAR(30) REFERENCES common.containers(container_id),
    pickup_zone VARCHAR(100) NOT NULL,
    destination_zone VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 1,
    task_status VARCHAR(30) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Periodic GPS telemetry from truck driver mobile apps
CREATE TABLE IF NOT EXISTS drayage.truck_locations (
    location_id BIGSERIAL PRIMARY KEY,
    truck_id VARCHAR(50) NOT NULL REFERENCES drayage.trucks(truck_id),
    latitude NUMERIC(10, 6) NOT NULL,
    longitude NUMERIC(10, 6) NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Truck dispatch task assignments and optimization metrics
CREATE TABLE IF NOT EXISTS drayage.truck_assignments (
    assignment_id BIGSERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL REFERENCES drayage.transport_tasks(task_id),
    truck_id VARCHAR(50) NOT NULL REFERENCES drayage.trucks(truck_id),
    driver_id VARCHAR(50) REFERENCES drayage.drivers(driver_id),
    route_id VARCHAR(50) REFERENCES common.routes(route_id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assignment_status VARCHAR(30) DEFAULT 'ASSIGNED',
    empty_distance_meters NUMERIC(10, 2),
    estimated_travel_minutes NUMERIC(8, 2),
    actual_completion_minutes NUMERIC(8, 2),
    waiting_time_minutes NUMERIC(8, 2)
);
