-- ==============================================================================
-- 003_gate_appointment_auto_conditions.sql
-- Component 4: AI-Powered Gate Appointment System
--
-- Weather, vessel delay and carrier reliability are now derived automatically (weather forecast, vessel
-- schedule read from the booking confirmation, carrier history) instead of typed in. This records the linked
-- vessel and where each condition came from. weather_severity and vessel_delay may now be NULL (= not known yet).
-- Additive only; safe to re-run. Run after 002_gate_appointment_conditions.sql.
-- ==============================================================================

ALTER TABLE gate.gate_appointments
    ADD COLUMN IF NOT EXISTS vessel_name        VARCHAR(100),
    ADD COLUMN IF NOT EXISTS vessel_delay_hours NUMERIC(5, 1),
    ADD COLUMN IF NOT EXISTS weather_source     VARCHAR(40);
