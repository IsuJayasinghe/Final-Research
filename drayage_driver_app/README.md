# Port Drayage Driver Mobile Application

> **Project**: AI-Powered Autonomous Smart Port Management System  
> **Subsystem**: Component 2 – Intelligent Drayage Truck Optimization System  
> **Target Audience**: Human-driven internal terminal truck operators  
> **Framework**: Flutter (Dart)  
> **Primary Target**: Android (with future iOS cross-platform compatibility)

---

## 1. System Overview

The **Port Drayage Driver Mobile Application** connects human truck operators inside a container terminal with the centralized AI-Powered Drayage Optimization Engine. Internal terminal trucks transport shipping containers between berths (quayside gantry cranes), container yards (stack blocks), rail interchanges, and gate blocks.

### Core Workflow
```
Intelligent Optimization Engine
       │ (Dispatches optimal task)
       ▼
Shared Python / FastAPI Backend
       │ (REST API / WebSocket)
       ▼
Driver Mobile App (Flutter)
       ├─ Step 1: Receives & acknowledges task
       ├─ Step 2: Follows recommended route to Pickup Zone
       ├─ Step 3: Updates status -> AT_PICKUP / IN_TRANSIT
       ├─ Step 4: Transports container to Destination Zone
       └─ Step 5: Updates status -> AT_DESTINATION / COMPLETED
       │
       ▼
Optimization Engine updates truck availability & calculates next dispatch
```

---

## 2. Project Directory Structure

```
drayage_driver_app/
├── android/                         # Native Android configuration, manifest & permissions
├── ios/                             # Native iOS configuration & privacy strings
├── lib/
│   ├── main.dart                    # Application entry point & theme initialization
│   ├── app/
│   │   ├── app.dart                 # MaterialApp root widget
│   │   ├── routes.dart              # Centralized route definitions
│   │   └── theme.dart               # High-contrast industrial terminal theme
│   ├── core/
│   │   ├── config/
│   │   │   └── app_config.dart      # Application constants, API endpoints, mock toggle
│   │   ├── errors/
│   │   │   └── app_exceptions.dart  # Exception definitions (Network, Auth, State Machine)
│   │   └── utils/
│   │       └── date_formatter.dart  # Date/time formatting utilities
│   ├── models/
│   │   ├── driver.dart              # Driver profile & duty status
│   │   ├── truck.dart               # Truck model & status enum
│   │   ├── transport_task.dart      # TransportTask model, priorities & lifecycle state transitions
│   │   └── location_update.dart     # Terminal GPS coordinate telemetry
│   ├── services/
│   │   ├── mock_data_service.dart   # Isolated mock database for offline UI testing
│   │   ├── auth_service.dart        # Driver authentication & session management
│   │   ├── task_service.dart        # Assignment retrieval & status state machine
│   │   ├── location_service.dart    # Truck GPS tracking interface
│   │   └── notification_service.dart# Operational dispatch alerts
│   ├── features/
│   │   ├── auth/
│   │   │   └── login_screen.dart    # Secure driver login & quick-demo fill
│   │   ├── dashboard/
│   │   │   └── dashboard_screen.dart# Real-time driver dashboard & mission spotlight
│   │   ├── tasks/
│   │   │   ├── assigned_tasks_screen.dart # Active transport tasks list
│   │   │   ├── task_details_screen.dart   # In-depth task specs & lifecycle progress
│   │   │   └── widgets/
│   │   │       └── task_status_dialog.dart# Validated status transition dialog
│   │   ├── navigation/
│   │   │   └── route_screen.dart    # Waypoint sequence & placeholder vector map
│   │   ├── history/
│   │   │   └── task_history_screen.dart   # Shift log of completed container missions
│   │   └── profile/
│   │       └── profile_screen.dart  # Driver identity, duty switch & API config
│   └── widgets/
│       ├── status_badge.dart        # Color-coded badges for status & priority
│       ├── info_card.dart           # Dashboard metric cards
│       ├── loading_indicator.dart   # Standardized loading state
│       └── error_message.dart       # Error recovery widget
├── test/
│   └── widget_test.dart             # Unit & service tests (state transitions & auth)
├── pubspec.yaml                     # Dependencies and project assets
├── analysis_options.yaml            # Flutter linter configuration
└── README.md
```

---

## 3. Implemented Features & Screens

1. **Driver Authentication (`/login`)**:
   - Secure login form with validation.
   - Quick-fill button for development testing (`DRV-102` / `drayage2026`).
2. **Driver Dashboard (`/dashboard`)**:
   - Truck and driver header badge (`TRK-025`, `Marcus Vance`).
   - Duty status indicator (`On Duty`, `On Break`, `Off Duty`).
   - Key metrics: Active Tasks, Done Today, Fuel Level.
   - Active Mission Spotlight Card with instant actions (`View Task`, `Update Status`).
   - Quick navigation to all terminal modules.
3. **Assigned Tasks Screen (`/tasks`)**:
   - Filter chips: All Active vs Priority/Urgent.
   - Container numbers, sizes, pickup & destination blocks.
4. **Task Details Screen (`/task-details`)**:
   - Full container specs (Container ID, Size, Cargo type).
   - Operation progress stepper displaying the 7 stages of the task lifecycle.
   - Pickup & destination zone display.
   - Special handling instructions.
5. **Task Status Lifecycle Dialog**:
   - Strictly enforces permitted state transitions:
     $$\text{ASSIGNED} \rightarrow \text{ACCEPTED} \rightarrow \text{TRAVELLING\_TO\_PICKUP} \rightarrow \text{AT\_PICKUP} \rightarrow \text{IN\_TRANSIT} \rightarrow \text{AT\_DESTINATION} \rightarrow \text{COMPLETED}$$
   - Prevents invalid jumps (e.g. jumping from Assigned directly to Completed).
6. **Route Guidance Screen (`/route`)**:
   - Clearly identified placeholder vector map layout.
   - Waypoint sequence from current position to pickup and destination.
7. **Task History Screen (`/history`)**:
   - Log of completed missions for the current shift.
8. **Driver Profile & Connectivity (`/profile`)**:
   - Driver credentials, license number, shift timetable.
   - Duty status toggle.
   - Backend API connection specifications.

---

## 4. How to Run the Application

### Prerequisites
1. **Flutter SDK**: Ensure Flutter 3.x is installed and added to your system `PATH`.
2. **Android Studio & SDK**: Configured with an Android Virtual Device (e.g. `Medium_Phone_API_36.0`).

### Execution Commands
```powershell
# Navigate to the mobile app directory
cd d:\drayage_driver_app

# Fetch dependencies
flutter pub get

# Run static code analysis
flutter analyze

# Execute automated tests
flutter test

# Launch on Android emulator or connected device
flutter run
```
