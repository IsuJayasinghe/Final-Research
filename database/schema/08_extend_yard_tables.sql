-- ==============================================================================
-- 08_extend_yard_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Component 3: Smart Container Yard Allocation & Space Utilization Optimization System
-- Extends the yard tables from 05_create_yard_tables.sql for slot-level allocation,
-- accept/override decisions and model outputs. Run after 01, 02 and 05.
-- ==============================================================================

-- Yard blocks: access zone, stack layout and description
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS access_zone VARCHAR(30);
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS stack_count INTEGER;
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS tier_height INTEGER DEFAULT 4;
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS description VARCHAR(200);

-- Allocations: AI recommendation, exact slot and the yard manager's decision
-- allocation_status: RECOMMENDED -> ACCEPTED / OVERRIDDEN -> RELEASED (or CANCELLED)
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS stack_number INTEGER;
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS tier INTEGER;
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS slot_id VARCHAR(20);
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS predicted_dwell_days NUMERIC(6, 2);
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS predicted_departure TIMESTAMP;
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS dwell_class VARCHAR(20);
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS recommended_zone VARCHAR(30);
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS recommended_yard_zone_id VARCHAR(50) REFERENCES yard.yard_zones(yard_zone_id);
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS recommendation_reason TEXT;
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS model_used VARCHAR(50);
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS decided_at TIMESTAMP;
ALTER TABLE yard.yard_allocations ADD COLUMN IF NOT EXISTS override_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_yard_allocations_container ON yard.yard_allocations(container_id);
CREATE INDEX IF NOT EXISTS idx_yard_allocations_status ON yard.yard_allocations(allocation_status);

-- Daily dwell time forecasts (Prophet / ARIMA) and per-container predictions
CREATE TABLE IF NOT EXISTS yard.dwell_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    container_id VARCHAR(30) REFERENCES common.containers(container_id),
    prediction_date DATE NOT NULL,
    predicted_dwell_days NUMERIC(6, 2),
    model_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Yard occupancy forecasts (XGBoost) with capacity alerts
CREATE TABLE IF NOT EXISTS yard.occupancy_forecasts (
    forecast_id BIGSERIAL PRIMARY KEY,
    forecast_date DATE NOT NULL,
    predicted_containers INTEGER,
    planned_arrivals INTEGER,
    utilization_percentage NUMERIC(5, 2),
    capacity_alert BOOLEAN DEFAULT FALSE,
    model_name VARCHAR(50) DEFAULT 'XGBoost',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Colombo yard blocks. Stack counts come from the yard layout used in the stacking
-- simulation (notebook Cell 9); capacity = stacks x 4 tiers.
INSERT INTO yard.yard_zones (yard_zone_id, zone_name, access_zone, stack_count, tier_height, capacity, description)
VALUES
    ('Yard_Block_A',      'Yard Block A',          'Fast-Access',   218, 4, 872, 'Near the gate, for short-stay containers'),
    ('Yard_Block_B',      'Yard Block B',          'Fast-Access',   218, 4, 872, 'Near the gate, for short-stay containers'),
    ('Yard_Block_C',      'Yard Block C',          'Medium-Access', 183, 4, 732, 'Middle of the yard, for medium-stay containers'),
    ('Yard_Block_D',      'Yard Block D',          'Medium-Access', 183, 4, 732, 'Middle of the yard, for medium-stay containers'),
    ('Yard_Block_E',      'Yard Block E',          'Long-Term',      25, 4, 100, 'Back of the yard, for long-stay containers'),
    ('Reefer_Yard_01',    'Reefer Yard 01',        'Reefer',        229, 4, 916, 'Powered slots for refrigerated containers'),
    ('Hazardous_Yard_01', 'Hazardous Yard 01',     'Hazardous',     173, 4, 692, 'Isolated storage for dangerous cargo')
ON CONFLICT (yard_zone_id) DO UPDATE SET
    zone_name = EXCLUDED.zone_name,
    access_zone = EXCLUDED.access_zone,
    stack_count = EXCLUDED.stack_count,
    tier_height = EXCLUDED.tier_height,
    capacity = EXCLUDED.capacity,
    description = EXCLUDED.description;
