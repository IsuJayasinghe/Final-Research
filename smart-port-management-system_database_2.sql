SELECT
    'Truck Details' AS dataset,
    COUNT(*) AS row_count
FROM staging.truck_details

UNION ALL

SELECT
    'Container Yard Data',
    COUNT(*)
FROM staging.container_yard_data

UNION ALL

SELECT
    'Berth Characteristics',
    COUNT(*)
FROM staging.berth_characteristics

UNION ALL

SELECT
    'Vessel Historical Data',
    COUNT(*)
FROM staging.vessel_historical_data;