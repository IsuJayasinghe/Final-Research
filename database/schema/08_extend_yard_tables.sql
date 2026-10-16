-- ==============================================================================
-- 08_extend_yard_tables.sql
-- AI-Powered Autonomous Smart Port Management System
-- Component 3: Smart Container Yard Allocation & Space Utilization Optimization System
-- Extends the yard tables from 05_create_yard_tables.sql for one yard block (Yard Block 01):
-- zone bay ranges, slot-level allocation, accept/override decisions and model outputs.
-- Run after 01, 02 and 05.
-- ==============================================================================

-- The component manages ONE yard block (Yard Block 01). Each row of yard.yard_zones is one
-- zone of that block: a range of bays, every bay has rows_per_bay stacks of tier_height tiers.
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS block_name VARCHAR(50);
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS access_zone VARCHAR(30);
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS first_bay INTEGER;
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS bay_count INTEGER;
ALTER TABLE yard.yard_zones ADD COLUMN IF NOT EXISTS rows_per_bay INTEGER DEFAULT 6;
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

-- Zones of Yard Block 01, in bay order from the gate end (bays 47-48 are an empty buffer
-- before the hazardous bays). Bay ranges come from the yard layout used in the stacking
-- simulation (notebook Cell 9); stacks = bays x 6 rows, capacity = stacks x 4 tiers.
INSERT INTO yard.yard_zones (yard_zone_id, zone_name, block_name, access_zone, first_bay, bay_count,
                             rows_per_bay, stack_count, tier_height, capacity, description)
VALUES
    ('YB01_FAST',   'Fast-Access zone',   'Yard Block 01', 'Fast-Access',    1, 19, 6, 114, 4, 456, 'Bays nearest the gate, for short-stay containers'),
    ('YB01_MEDIUM', 'Medium-Access zone', 'Yard Block 01', 'Medium-Access', 20, 16, 6,  96, 4, 384, 'Middle bays, for medium-stay containers'),
    ('YB01_LONG',   'Long-Term zone',     'Yard Block 01', 'Long-Term',     36,  1, 6,   6, 4,  24, 'Far bays, for long-stay containers'),
    ('YB01_REEFER', 'Reefer zone',        'Yard Block 01', 'Reefer',        37, 10, 6,  60, 4, 240, 'Powered bays for refrigerated containers'),
    ('YB01_HAZARD', 'Hazardous zone',     'Yard Block 01', 'Hazardous',     49,  8, 6,  48, 4, 192, 'Isolated bays for dangerous cargo, behind a buffer')
ON CONFLICT (yard_zone_id) DO UPDATE SET
    zone_name = EXCLUDED.zone_name,
    block_name = EXCLUDED.block_name,
    access_zone = EXCLUDED.access_zone,
    first_bay = EXCLUDED.first_bay,
    bay_count = EXCLUDED.bay_count,
    rows_per_bay = EXCLUDED.rows_per_bay,
    stack_count = EXCLUDED.stack_count,
    tier_height = EXCLUDED.tier_height,
    capacity = EXCLUDED.capacity,
    description = EXCLUDED.description;

-- Earlier versions of this file seeded seven separate blocks; remove them if nothing uses them
DELETE FROM yard.yard_zones z
WHERE z.yard_zone_id IN ('Yard_Block_A', 'Yard_Block_B', 'Yard_Block_C', 'Yard_Block_D', 'Yard_Block_E',
                         'Reefer_Yard_01', 'Hazardous_Yard_01')
  AND NOT EXISTS (SELECT 1 FROM yard.yard_allocations a
                  WHERE a.yard_zone_id = z.yard_zone_id OR a.recommended_yard_zone_id = z.yard_zone_id)
  AND NOT EXISTS (SELECT 1 FROM yard.yard_occupancy o WHERE o.yard_zone_id = z.yard_zone_id);
