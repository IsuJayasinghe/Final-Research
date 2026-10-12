CREATE DATABASE smart_port_db; 
 
\c smart_port_db 
 
CREATE TABLE containers ( 
    id SERIAL PRIMARY KEY, 
    container_id VARCHAR(20) NOT NULL, 
    container_type VARCHAR(20) NOT NULL, 
    container_size VARCHAR(10), 
    cargo_type VARCHAR(50), 
    shipping_line VARCHAR(50), 
    weight_category VARCHAR(20), 
    vessel_id VARCHAR(30), 
    gate_in_timestamp TIMESTAMP, 
    gate_out_timestamp TIMESTAMP, 
    predicted_dwell_days FLOAT, 
    assigned_zone VARCHAR(50), 
    zone_reason VARCHAR(100), 
    status VARCHAR(20) DEFAULT 'in_yard', 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP); 
 
-- Table 2: Dwell Time Predictions (Prophet/ARIMA) 
CREATE TABLE predictions ( 
    id SERIAL PRIMARY KEY, 
    prediction_date DATE NOT NULL, 
    predicted_dwell_days FLOAT, 
    model_used VARCHAR(20) DEFAULT 'prophet', 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
); 
-- Table 3: Zone Allocation Records 
CREATE TABLE zone_allocations ( 
    id SERIAL PRIMARY KEY, 
    container_id VARCHAR(20) NOT NULL, 
    container_type VARCHAR(20), 
    dwell_days FLOAT, 
    recommended_zone VARCHAR(50), 
    reason VARCHAR(100), 
    allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
); 
-- Table 4: Yard Occupancy Predictions (XGBoost) 
CREATE TABLE occupancy_predictions ( 
    id SERIAL PRIMARY KEY, 
    prediction_date DATE NOT NULL, 
    predicted_container_count INT, 
    actual_container_count INT, 
    model_used VARCHAR(20) DEFAULT 'xgboost', 
    r2_score FLOAT, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
