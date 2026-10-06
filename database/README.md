# Database Architecture & Documentation

## Overview

The **AI-Powered Autonomous Smart Port Management System** uses a multi-schema relational architecture hosted on **PostgreSQL 18** to segregate operational domains while providing relational consistency across shared terminal entities.

- **Local Database Name**: `smart_port_management`
- **Database Engine**: PostgreSQL 18
- **Port**: Default `5432`

---

## Schema Architecture

The database is partitioned into six distinct schemas:

```
┌────────────────────────────────────────────────────────┐
│                     common Schema                      │
│            (vessels, containers, routes)               │
└──────────┬──────────────┬──────────────┬───────────────┘
           │              │              │
           ▼              ▼              ▼
    ┌─────────────┐┌─────────────┐┌─────────────┐┌─────────────┐
    │berth Schema ││drayage Schema││ yard Schema ││ gate Schema │
    │(Component 1)││(Component 2)││(Component 3)││(Component 4)│
    └─────────────┘└─────────────┘└─────────────┘└─────────────┘
           ▲
           │ (ETL Clean & Transform)
    ┌──────────────┐
    │staging Schema│
    │(Raw Datasets)│
    └──────────────┘
```

### 1. `common` Schema (Shared Core Entities)
Contains foundational terminal entities referenced across all functional subsystems:
- **`common.vessels`**: Global registry of vessels calling at the terminal (`vessel_id`, `imo_number`, `mmsi`, `vessel_name`, `vessel_type`).
- **`common.containers`**: Global registry of containers handled by the terminal (`container_id`, `container_size`, `container_type`, `shipping_line`, `weight_category`, `cargo_type`).
- **`common.routes`**: Internal terminal roadways and predefined route segments connecting terminal zones (`route_id`, `route_name`, `start_zone`, `destination_zone`, `distance_meters`, `is_active`).

### 2. `berth` Schema (Component 1 — Smart Dynamic Berth Allocation)
Manages quayside infrastructure, incoming vessel AIS telemetry, arrival forecasting, and dynamic berth scheduling:
- **`berth.berths`**: Berth physical characteristics and infrastructure specifications (`berth_id`, `instance_id`, `terminal_name`, `max_length_m`, `max_draft_m`, `crane_count`, `crane_handling_rate`).
- **`berth.vessel_tracking`**: Spatio-temporal vessel telemetry and AIS tracking points with maritime meteorological observations (`tracking_id`, `vessel_id`, `base_datetime`, `latitude`, `longitude`, `sog`, `cog`, `distance_to_port_nmi`, `draft_m`, `wind_speed_knots`, `wave_height_m`, `actual_remaining_hours`).
- **`berth.eta_predictions`**: Inference results from the ETA prediction ML model (`prediction_id`, `vessel_id`, `predicted_remaining_hours`, `predicted_eta`, `model_version`, `predicted_at`).
- **`berth.berth_allocations`**: Scheduled and actual berthing windows for arriving vessels (`allocation_id`, `vessel_id`, `berth_id`, `planned_arrival`, `planned_departure`, `actual_arrival`, `actual_departure`, `allocation_status`).

### 3. `drayage` Schema (Component 2 — Intelligent Drayage Truck Optimization)
Coordinates internal terminal tractors, drivers, container transport jobs, real-time vehicle positioning, and dispatch optimization:
- **`drayage.drivers`**: Internal fleet operators and human drivers (`driver_id`, `driver_name`, `phone_number`, `status`).
- **`drayage.trucks`**: Fleet inventory of terminal tractors / prime movers (`truck_id`, `vehicle_type`, `current_status`, `current_latitude`, `current_longitude`, `current_driver_id`).
- **`drayage.transport_tasks`**: Internal container transport requests between quayside, yard, and gates (`task_id`, `vessel_id`, `container_id`, `pickup_zone`, `destination_zone`, `priority`, `task_status`, `created_at`, `started_at`, `completed_at`).
- **`drayage.truck_locations`**: Periodic GPS tracking points recorded from truck driver mobile devices (`location_id`, `truck_id`, `latitude`, `longitude`, `recorded_at`).
- **`drayage.truck_assignments`**: Dispatch assignments matching tasks to trucks with travel metrics (`assignment_id`, `task_id`, `truck_id`, `driver_id`, `route_id`, `assigned_at`, `assignment_status`, `empty_distance_meters`, `estimated_travel_minutes`, `actual_completion_minutes`, `waiting_time_minutes`).

### 4. `yard` Schema (Component 3 — Smart Container Yard Allocation & Space Utilization)
Monitors yard storage zones, container spatial placement, and storage block occupancy:
- **`yard.yard_zones`**: Storage blocks and terminal yard partitions (`yard_zone_id`, `zone_name`, `capacity`, `current_occupancy`, `zone_status`).
- **`yard.yard_allocations`**: Spatial assignment logs allocating containers to designated yard zones (`yard_allocation_id`, `container_id`, `yard_zone_id`, `allocated_at`, `released_at`, `allocation_status`).
- **`yard.yard_occupancy`**: Time-series snapshots of yard block capacity and utilization percentage (`occupancy_id`, `yard_zone_id`, `recorded_at`, `occupied_slots`, `available_slots`, `utilization_percentage`).

### 5. `gate` Schema (Component 4 — AI-Powered Gate Appointment System)
Facilitates external haulier gate access, pre-clearance validation, and appointment scheduling:
- **`gate.gates`**: Physical terminal entrance/exit gate lanes and checkpoints (`gate_id`, `gate_name`, `gate_status`).
- **`gate.gate_appointments`**: Scheduled gate arrival reservations for external trucks (`appointment_id`, `container_id`, `external_truck_id`, `driver_id`, `gate_id`, `requested_arrival`, `assigned_arrival`, `appointment_status`).
- **`gate.gate_submissions`**: Digital paperwork and cargo declaration data submitted via portal/mobile interfaces (`submission_id`, `appointment_id`, `submitted_at`, `submission_status`, `cargo_details`, `vehicle_details`, `clearance_information`).
- **`gate.gate_clearances`**: Gate clearance and inspection timeline records (`clearance_id`, `appointment_id`, `predicted_clearance_time`, `actual_clearance_time`, `clearance_status`).

### 6. `staging` Schema (Raw Data Ingestion & ETL)
Provides an isolated landing zone for loading raw research datasets prior to data validation and migration into production schemas:
- **`staging.truck_details`**: Raw ingestion table for internal drayage movement logs.
- **`staging.container_yard_data`**: Raw ingestion table for container yard transitions.
- **`staging.berth_characteristics`**: Raw ingestion table for physical berth specifications.
- **`staging.vessel_historical_data`**: Raw ingestion table for maritime AIS tracks and meteorological readings.

---

## Schema Execution Order

Execute the SQL scripts in numerical order to satisfy foreign key dependencies:

1. **`01_create_schemas.sql`** — Creates all six database schemas (`common`, `berth`, `drayage`, `yard`, `gate`, `staging`).
2. **`02_create_common_tables.sql`** — Creates core shared dimension tables (`common.vessels`, `common.containers`, `common.routes`).
3. **`03_create_berth_tables.sql`** — Creates Component 1 tables (`berth.berths`, `berth.vessel_tracking`, `berth.eta_predictions`, `berth.berth_allocations`).
4. **`04_create_drayage_tables.sql`** — Creates Component 2 tables (`drayage.drivers`, `drayage.trucks`, `drayage.transport_tasks`, `drayage.truck_locations`, `drayage.truck_assignments`).
5. **`05_create_yard_tables.sql`** — Creates Component 3 tables (`yard.yard_zones`, `yard.yard_allocations`, `yard.yard_occupancy`).
6. **`06_create_gate_tables.sql`** — Creates Component 4 tables (`gate.gates`, `gate.gate_appointments`, `gate.gate_submissions`, `gate.gate_clearances`).
7. **`07_create_staging_tables.sql`** — Creates staging ingestion tables for ETL processing.

### Running Schemas in PostgreSQL

Execute using `psql`:

```bash
# Connect to PostgreSQL and create database if needed
psql -U postgres -c "CREATE DATABASE smart_port_management;"

# Run scripts sequentially
psql -U postgres -d smart_port_management -f database/schema/01_create_schemas.sql
psql -U postgres -d smart_port_management -f database/schema/02_create_common_tables.sql
psql -U postgres -d smart_port_management -f database/schema/03_create_berth_tables.sql
psql -U postgres -d smart_port_management -f database/schema/04_create_drayage_tables.sql
psql -U postgres -d smart_port_management -f database/schema/05_create_yard_tables.sql
psql -U postgres -d smart_port_management -f database/schema/06_create_gate_tables.sql
psql -U postgres -d smart_port_management -f database/schema/07_create_staging_tables.sql
```

All SQL scripts include `CREATE SCHEMA IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS` clauses, enabling safe and idempotent re-execution.
