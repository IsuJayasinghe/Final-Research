-- ==============================================================================
-- 002_gate_appointment_conditions.sql
-- Component 4: AI-Powered Gate Appointment System
--
-- Keeps the booking-time conditions the no-show model used (weather severity and
-- linked-vessel delay) so risk can be re-scored later, e.g. after document checks.
-- Additive only; safe to re-run. Run after 001_gate_appointment_predictions.sql.
-- ==============================================================================

ALTER TABLE gate.gate_appointments
    ADD COLUMN IF NOT EXISTS weather_severity SMALLINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS vessel_delay     BOOLEAN  DEFAULT FALSE;

-- event_type now also includes DOCUMENTS_CHECKED (see gate.gate_appointment_events)
