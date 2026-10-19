import argparse
import sqlite3
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

def find_csv_file(filename: str, search_dirs: list) -> Optional[Path]:
    for d in search_dirs:
        p = d / filename
        if p.exists():
            return p
    return None

def init_database(force_reset: bool = False, export_csv: bool = False):
    """
    Initializes and verifies the Smart Port Component 1 SQLite Database (smart_port.db).
    Maintains normalized schemas for:
      1. berth_characteristics (physical dimensions, draft, crane capacity)
      2. berth_bookings (live booking states, schedule windows, status)
      3. vessel_historical_data (AIS telemetry, hydrodynamic & weather variables)
    """
    backend_dir = Path(__file__).resolve().parent
    db_path = backend_dir / "smart_port.db"
    root_dir = backend_dir.parent

    search_dirs = [backend_dir, root_dir, backend_dir.parent, Path.cwd()]

    berth_csv_path = find_csv_file("berth_characteristics.csv", search_dirs)
    vessel_csv_path = find_csv_file("vessel_historical_data.csv", search_dirs)

    print(f"Connecting to database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing table counts if not forcing reset
    existing_tables = [r[0] for r in cursor.execute("SELECT tbl_name FROM sqlite_master WHERE type='table'").fetchall()]
    has_existing_data = ("berth_characteristics" in existing_tables and 
                         "vessel_historical_data" in existing_tables and 
                         not force_reset)

    if has_existing_data:
        cursor.execute("SELECT COUNT(*) FROM berth_characteristics;")
        b_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vessel_historical_data;")
        v_cnt = cursor.fetchone()[0]
        if b_cnt > 0 and v_cnt > 0:
            print(f"Database already populated: {b_cnt} berths, {v_cnt} vessel telemetry records.")
            print("Ensuring tables, schema constraints, and performance indexes...")
    else:
        print("Initializing database tables from source schemas...")
        cursor.execute("DROP TABLE IF EXISTS berth_characteristics;")
        cursor.execute("DROP TABLE IF EXISTS vessel_historical_data;")

    # 1. Berth characteristics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS berth_characteristics (
        instance_id TEXT PRIMARY KEY,
        terminal_name TEXT NOT NULL,
        berth_id TEXT NOT NULL UNIQUE,
        max_length_m REAL NOT NULL,
        max_draft_m REAL NOT NULL,
        crane_count INTEGER NOT NULL,
        crane_handling_rate_teu_hr INTEGER NOT NULL
    );
    """)

    # 2. Berth bookings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS berth_bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vessel_imo INTEGER NOT NULL,
        vessel_name TEXT NOT NULL,
        berth_id TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        status TEXT DEFAULT 'BOOKED',
        FOREIGN KEY (berth_id) REFERENCES berth_characteristics(berth_id)
    );
    """)

    # 3. Vessel historical data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vessel_historical_data (
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

    # Performance and query optimization indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_berth_bookings_time ON berth_bookings(berth_id, start_time, end_time, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_berth_bookings_vessel ON berth_bookings(vessel_imo, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vessel_historical_imo ON vessel_historical_data(imo_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_berth_characteristics_limits ON berth_characteristics(max_length_m, max_draft_m);")
    conn.commit()

    # Seed data if tables were newly created or empty
    cursor.execute("SELECT COUNT(*) FROM berth_characteristics;")
    berth_count = cursor.fetchone()[0]

    if berth_count == 0 and berth_csv_path:
        print(f"Reading berth data from {berth_csv_path}...")
        df_berth = pd.read_csv(berth_csv_path)
        col_map = {
            'Instance ID': 'instance_id',
            'Terminal Name': 'terminal_name',
            'Berth ID': 'berth_id',
            'Max Length (m)': 'max_length_m',
            'Max Draft (m)': 'max_draft_m',
            'Crane Count': 'crane_count',
            'Crane Handling Rate (TEU/hr)': 'crane_handling_rate_teu_hr'
        }
        df_berth = df_berth.rename(columns=col_map)
        target_cols = [c for c in col_map.values() if c in df_berth.columns]
        df_berth[target_cols].to_sql('berth_characteristics', conn, if_exists='append', index=False)
        print(f"Inserted {len(df_berth)} records into berth_characteristics.")

    cursor.execute("SELECT COUNT(*) FROM vessel_historical_data;")
    vessel_count = cursor.fetchone()[0]

    if vessel_count == 0 and vessel_csv_path:
        print(f"Reading vessel telemetry data from {vessel_csv_path}...")
        df_vessel = pd.read_csv(vessel_csv_path)
        vessel_columns = [
            'mmsi', 'imo_number', 'vessel_name', 'vessel_type', 'base_datetime',
            'latitude', 'longitude', 'sog', 'cog', 'distance_to_port_nmi',
            'draft_m', 'wind_speed_knots', 'wave_height_m', 'actual_remaining_hours'
        ]
        available_cols = [c for c in vessel_columns if c in df_vessel.columns]
        df_vessel[available_cols].to_sql('vessel_historical_data', conn, if_exists='append', index=False)
        print(f"Inserted {len(df_vessel)} records into vessel_historical_data.")

    # Ensure baseline sample bookings exist
    cursor.execute("SELECT COUNT(*) FROM berth_bookings;")
    booking_count = cursor.fetchone()[0]
    if booking_count == 0:
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

    # Final verification counts
    cursor.execute("SELECT COUNT(*) FROM berth_characteristics;")
    berth_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vessel_historical_data;")
    vessel_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM berth_bookings;")
    booking_count = cursor.fetchone()[0]

    print(f"\n[OK] Database initialized and verified successfully at: {db_path}")
    print(f" - berth_characteristics: {berth_count} rows")
    print(f" - vessel_historical_data: {vessel_count} rows")
    print(f" - berth_bookings:        {booking_count} rows")

    # Export to CSV if requested
    if export_csv:
        csv_vessel = backend_dir / "vessel_historical_data.csv"
        csv_berth = backend_dir / "berth_characteristics.csv"
        pd.read_sql("SELECT * FROM vessel_historical_data", conn).to_csv(csv_vessel, index=False)
        pd.read_sql("SELECT * FROM berth_characteristics", conn).to_csv(csv_berth, index=False)
        print(f"Exported CSVs to {backend_dir}")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Port Database Initializer")
    parser.add_argument("--force-reset", action="store_true", help="Force wipe and reseed tables")
    parser.add_argument("--export-csv", action="store_true", help="Export SQLite tables to CSV")
    args = parser.parse_args()
    init_database(force_reset=args.force_reset, export_csv=args.export_csv)

