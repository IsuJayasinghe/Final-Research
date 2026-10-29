Component 1: Intelligent Vessel ETA Prediction & Dynamic Berth Allocation Framework
IT23334410

Overview
Component 1 is the core predictive and decision-support intelligence engine of the Smart Port Management System (Port of Colombo).
It bridges raw maritime telemetry with machine learning to automate berth planning, calculate accurate voyage ETAs under environmental stress, 
and execute self-healing exception management when severe weather or delays occur.

Key Features & Capabilities
1. Real-Time GIS Fleet Tracking Integration: Consumes simulated vessel telemetry (Latitude, Longitude, Speed Over Ground) to render and
   track incoming traffic relative to the Port of Colombo.
2. Intelligent Constraint Matching: Dynamically filters physical berth availability (across 49 managed berths spanning terminals like CICT,
   JCT, and ECT) based on vessel dimensions (length and draft) and temporal scheduling windows.
3. AI-Driven ETA Regression (eta_model.pkl): Utilizes a trained Random Forest Regressor to predict continuous voyage transit durations based on
   environmental drag, distance, and speed.
4. Delay & Disruption Risk Classification (delay_model.pkl): Evaluates weather anomalies (wind speed, wave height) to
   flag critical delay risks ($\ge 65\%$ threshold).
5. Self-Healing Autonomous Unbooking Engine: Automatically purges invalid reservations, frees port capacity,
   and triggers automated reallocations when schedule violations occur.
