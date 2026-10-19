import sqlite3
from pathlib import Path
import pandas as pd

def init_database():
    # Resolve backend and root paths
    backend_dir = Path(__file__).resolve().parent
    db_path = backend_dir / "smart_port.db"
    root_dir = backend_dir.parent
    berth_csv_path = root_dir / "berth_characteristics.csv"
    vessel_csv_path = root_dir / "vessel_historical_data.csv"

    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables
    print("Creating tables...")
    cursor.execute("DROP TABLE IF EXISTS berth_characteristics;")
    cursor.execute("""
    CREATE TABLE berth_characteristics (
        instance_id TEXT PRIMARY KEY,
        terminal_name TEXT,
        berth_id TEXT,
        max_length_m REAL,
        max_draft_m REAL,
        crane_count INTEGER,
        crane_handling_rate_teu_hr INTEGER
    );
    """)

    cursor.execute("DROP TABLE IF EXISTS berth_bookings;")
    cursor.execute("""
    CREATE TABLE berth_bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vessel_imo INTEGER,
        vessel_name TEXT,
        berth_id TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT DEFAULT 'BOOKED',
        FOREIGN KEY (berth_id) REFERENCES berth_characteristics(berth_id)
    );
    """)

    cursor.execute("DROP TABLE IF EXISTS vessel_historical_data;")
    cursor.execute("""
    CREATE TABLE vessel_historical_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mmsi INTEGER,
        imo_number INTEGER,
        vessel_name TEXT,
        vessel_type TEXT,
        base_datetime TEXT,
        latitude REAL,
        longitude REAL,
        sog REAL,
        cog REAL,
        distance_to_port_nmi REAL,
        draft_m REAL,
        wind_speed_knots REAL,
        wave_height_m REAL,
        actual_remaining_hours INTEGER
    );
    """)
    conn.commit()

    # Load and seed berth characteristics
    print(f"Reading {berth_csv_path}...")
    df_berth = pd.read_csv(berth_csv_path)

    # Map CSV column names to table schema
    column_mapping = {
        'Instance ID': 'instance_id',
        'Terminal Name': 'terminal_name',
        'Berth ID': 'berth_id',
        'Max Length (m)': 'max_length_m',
        'Max Draft (m)': 'max_draft_m',
        'Crane Count': 'crane_count',
        'Crane Handling Rate (TEU/hr)': 'crane_handling_rate_teu_hr'
    }
    df_berth = df_berth.rename(columns=column_mapping)
    df_berth = df_berth[list(column_mapping.values())]

    print(f"Inserting {len(df_berth)} records into berth_characteristics...")
    df_berth.to_sql('berth_characteristics', conn, if_exists='append', index=False)

    # Load and seed vessel historical data
    print(f"Reading {vessel_csv_path}...")
    df_vessel = pd.read_csv(vessel_csv_path)

    vessel_columns = [
        'mmsi', 'imo_number', 'vessel_name', 'vessel_type', 'base_datetime',
        'latitude', 'longitude', 'sog', 'cog', 'distance_to_port_nmi',
        'draft_m', 'wind_speed_knots', 'wave_height_m', 'actual_remaining_hours'
    ]
    df_vessel = df_vessel[vessel_columns]

    print(f"Inserting {len(df_vessel)} records into vessel_historical_data...")
    df_vessel.to_sql('vessel_historical_data', conn, if_exists='append', index=False)

    # Seed initial sample berth bookings for visualization
    sample_bookings = [
        (9321483, 'EMMA MAERSK', 'JCT_01', '2026-10-19T08:00:00Z', '2026-10-19T20:00:00Z', 'BOOKED'),
        (9839179, 'CMA CGM JACQUES SAADE', 'CICT_01', '2026-10-19T10:00:00Z', '2026-10-20T02:00:00Z', 'BOOKED'),
        (8420804, 'BERGE STAHL', 'SAGT_01', '2026-10-18T12:00:00Z', '2026-10-19T06:00:00Z', 'COMPLETED')
    ]
    cursor.executemany("""
    INSERT INTO berth_bookings (vessel_imo, vessel_name, berth_id, start_time, end_time, status)
    VALUES (?, ?, ?, ?, ?, ?);
    """, sample_bookings)
    conn.commit()

    # Verification counts
    cursor.execute("SELECT COUNT(*) FROM berth_characteristics;")
    berth_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vessel_historical_data;")
    vessel_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM berth_bookings;")
    booking_count = cursor.fetchone()[0]

    print(f"Database initialized successfully!")
    print(f" - berth_characteristics: {berth_count} rows")
    print(f" - vessel_historical_data: {vessel_count} rows")
    print(f" - berth_bookings: {booking_count} rows")

    conn.close()

if __name__ == "__main__":
    init_database()
