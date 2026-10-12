-- ==============================================================================
-- 001_gate_appointment_predictions.sql
-- Component 4: AI-Powered Gate Appointment System
--
-- Extends gate.gate_appointments (06_create_gate_tables.sql) so a booking can
-- store what the models predicted and why the slot decision was made, and adds
-- an audit table for slot reassignments. Additive only: no existing column or
-- table is changed or dropped. Safe to re-run.
-- ==============================================================================

ALTER TABLE gate.gate_appointments
    ADD COLUMN IF NOT EXISTS carrier_company             VARCHAR(100),
    ADD COLUMN IF NOT EXISTS container_type              VARCHAR(50),
    ADD COLUMN IF NOT EXISTS cargo_category              VARCHAR(20),
    ADD COLUMN IF NOT EXISTS customs_risk_flag           VARCHAR(20),
    ADD COLUMN IF NOT EXISTS missing_documents_count     INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS carrier_reliability_score   NUMERIC(4, 2),
    ADD COLUMN IF NOT EXISTS no_show_probability         NUMERIC(6, 4),
    ADD COLUMN IF NOT EXISTS late_probability            NUMERIC(6, 4),
    ADD COLUMN IF NOT EXISTS predicted_clearance_minutes NUMERIC(8, 1),
    ADD COLUMN IF NOT EXISTS overbooked                  BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS decision_reason             TEXT,
    ADD COLUMN IF NOT EXISTS risk_summary                TEXT,
    ADD COLUMN IF NOT EXISTS created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_gate_appointments_assigned_arrival
    ON gate.gate_appointments (assigned_arrival);

-- Audit trail: every assignment, reassignment and status change with its reason
CREATE TABLE IF NOT EXISTS gate.gate_appointment_events (
    event_id        BIGSERIAL PRIMARY KEY,
    appointment_id  BIGINT NOT NULL REFERENCES gate.gate_appointments(appointment_id),
    event_time      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type      VARCHAR(30) NOT NULL,   -- ASSIGNED | REASSIGNED | CONFIRMED | CANCELLED | WAITLISTED
    old_arrival     TIMESTAMP,
    new_arrival     TIMESTAMP,
    reason          TEXT
);

CREATE INDEX IF NOT EXISTS idx_gate_appointment_events_appointment
    ON gate.gate_appointment_events (appointment_id);

-- The six terminal gate lanes referenced by gate_appointments.gate_id
INSERT INTO gate.gates (gate_id, gate_name)
SELECT 'GATE-' || n, 'Gate Lane ' || n
FROM generate_series(1, 6) AS n
ON CONFLICT (gate_id) DO NOTHING;
