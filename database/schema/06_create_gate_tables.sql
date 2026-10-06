-- ==============================================================================
-- 06_create_gate_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Component 4: AI-Powered Gate Appointment System
-- ==============================================================================

-- Physical terminal gates and entry/exit lanes
CREATE TABLE IF NOT EXISTS gate.gates (
    gate_id VARCHAR(50) PRIMARY KEY,
    gate_name VARCHAR(100) NOT NULL,
    gate_status VARCHAR(30) DEFAULT 'ACTIVE'
);

-- Gate appointments booked by external hauliers and logistics providers
CREATE TABLE IF NOT EXISTS gate.gate_appointments (
    appointment_id BIGSERIAL PRIMARY KEY,
    container_id VARCHAR(30) REFERENCES common.containers(container_id),
    external_truck_id VARCHAR(50),
    driver_id VARCHAR(50),
    gate_id VARCHAR(50) REFERENCES gate.gates(gate_id),
    requested_arrival TIMESTAMP,
    assigned_arrival TIMESTAMP,
    appointment_status VARCHAR(30) DEFAULT 'PENDING'
);

-- Digital paperwork and cargo declarations submitted via web/mobile interface
CREATE TABLE IF NOT EXISTS gate.gate_submissions (
    submission_id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT NOT NULL REFERENCES gate.gate_appointments(appointment_id),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submission_status VARCHAR(30) DEFAULT 'SUBMITTED',
    cargo_details TEXT,
    vehicle_details TEXT,
    clearance_information TEXT
);

-- Gate pre-clearance and automated inspection timelines
CREATE TABLE IF NOT EXISTS gate.gate_clearances (
    clearance_id BIGSERIAL PRIMARY KEY,
    appointment_id BIGINT NOT NULL REFERENCES gate.gate_appointments(appointment_id),
    predicted_clearance_time TIMESTAMP,
    actual_clearance_time TIMESTAMP,
    clearance_status VARCHAR(30) DEFAULT 'PENDING'
);
