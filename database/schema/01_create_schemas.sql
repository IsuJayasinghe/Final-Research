-- ==============================================================================
-- 01_create_schemas.sql
-- AI-Powered Autonomous Smart Port Management System
-- Schema Initialization for PostgreSQL 18
-- ==============================================================================

-- Core shared schema (vessels, containers, transport routes)
CREATE SCHEMA IF NOT EXISTS common;

-- Component 1: Smart Dynamic Berth Allocation System
CREATE SCHEMA IF NOT EXISTS berth;

-- Component 2: Intelligent Drayage Truck Optimization System
CREATE SCHEMA IF NOT EXISTS drayage;

-- Component 3: Smart Container Yard Allocation & Space Utilization Optimization System
CREATE SCHEMA IF NOT EXISTS yard;

-- Component 4: AI-Powered Gate Appointment System
CREATE SCHEMA IF NOT EXISTS gate;

-- Staging Schema: Landing zone for raw research data ingestion & ETL processing
CREATE SCHEMA IF NOT EXISTS staging;
