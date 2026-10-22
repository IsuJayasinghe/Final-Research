from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

def get_db_path() -> Path:
    current_file = Path(__file__).resolve()
    # Check Backend/smart_port.db
    backend_dir = current_file.parent.parent
    db_path = backend_dir / "smart_port.db"
    if db_path.exists():
        return db_path
    # Fallback to local
    return Path("smart_port.db").resolve()

def ensure_berth_bookings_table(conn: sqlite3.Connection) -> None:
    """Ensures the berth_bookings table exists in SQLite database."""
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS berth_bookings (
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_berth_bookings_time ON berth_bookings(berth_id, start_time, end_time, status);")
    conn.commit()

def parse_iso_datetime(dt_val: Any) -> datetime:
    """Parse various datetime string formats into UTC-aware datetime."""
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val.astimezone(timezone.utc)

    s = str(dt_val).strip()
    # Replace trailing Z with UTC offset
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    # Try standard formats
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M"
    ]:
        try:
            parsed = datetime.strptime(s, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(s)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception as e:
        raise ValueError(f"Unable to parse timestamp '{dt_val}': {str(e)}")

def format_iso(dt: datetime) -> str:
    """Return uniform ISO-8601 UTC string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def check_time_window_conflict(
    conn: sqlite3.Connection,
    berth_id: str,
    start_dt: datetime,
    end_dt: datetime,
    exclude_booking_id: Optional[int] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks if there is an active booking on the given berth that overlaps with [start_dt, end_dt].
    Two windows [S1, E1] and [S2, E2] overlap if: S1 < E2 and E1 > S2.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT booking_id, vessel_imo, vessel_name, berth_id, start_time, end_time, status
        FROM berth_bookings
        WHERE berth_id = ? AND status = 'BOOKED'
    """, (berth_id,))
    rows = cursor.fetchall()

    for r in rows:
        b_id = r[0]
        if exclude_booking_id is not None and b_id == exclude_booking_id:
            continue
        try:
            b_start = parse_iso_datetime(r[4])
            b_end = parse_iso_datetime(r[5])
        except Exception:
            continue

        # Overlap condition: start_dt < b_end and end_dt > b_start
        if start_dt < b_end and end_dt > b_start:
            conflict_info = {
                "booking_id": b_id,
                "vessel_imo": r[1],
                "vessel_name": r[2],
                "berth_id": r[3],
                "start_time": r[4],
                "end_time": r[5]
            }
            return True, conflict_info

    return False, None

def check_vessel_time_window_conflict(
    conn: sqlite3.Connection,
    vessel_imo: int,
    start_dt: datetime,
    end_dt: datetime,
    exclude_booking_id: Optional[int] = None
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks if a vessel (by IMO number) already has an active 'BOOKED' reservation
    whose time window overlaps with [start_dt, end_dt].
    Strict standard overlap logic: (New_Start < Existing_End) AND (New_End > Existing_Start).
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT booking_id, vessel_imo, vessel_name, berth_id, start_time, end_time, status
        FROM berth_bookings
        WHERE vessel_imo = ? AND status = 'BOOKED'
    """, (vessel_imo,))
    rows = cursor.fetchall()

    for r in rows:
        b_id = r[0]
        if exclude_booking_id is not None and b_id == exclude_booking_id:
            continue
        try:
            b_start = parse_iso_datetime(r[4])
            b_end = parse_iso_datetime(r[5])
        except Exception:
            continue

        # Standard time overlap: (New_Start < Existing_End) AND (New_End > Existing_Start)
        if start_dt < b_end and end_dt > b_start:
            conflict_info = {
                "booking_id": b_id,
                "vessel_imo": r[1],
                "vessel_name": r[2],
                "berth_id": r[3],
                "start_time": r[4],
                "end_time": r[5]
            }
            return True, conflict_info

    return False, None

def get_available_berths(
    length_m: float,
    draft_m: float,
    start_time: str,
    end_time: str,
    terminal_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filters all berths that:
    1. Match vessel physical attributes (ship length <= max_length_m and ship draft <= max_draft_m).
    2. Have no conflicting 'BOOKED' records during the requested time window [start_time, end_time].
    """
    start_dt = parse_iso_datetime(start_time)
    end_dt = parse_iso_datetime(end_time)

    if end_dt <= start_dt:
        raise ValueError(f"end_time ({end_time}) must be strictly after start_time ({start_time}).")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_berth_bookings_table(conn)
    cursor = conn.cursor()

    # Query berths satisfying length and draft constraints
    query = """
        SELECT instance_id, terminal_name, berth_id, max_length_m, max_draft_m, crane_count, crane_handling_rate_teu_hr
        FROM berth_characteristics
        WHERE max_length_m >= ? AND max_draft_m >= ?
    """
    params: List[Any] = [length_m, draft_m]

    if terminal_name:
        query += " AND terminal_name LIKE ?"
        params.append(f"%{terminal_name}%")

    query += " ORDER BY crane_handling_rate_teu_hr DESC, max_draft_m ASC"
    cursor.execute(query, params)
    physically_compatible_berths = [dict(row) for row in cursor.fetchall()]

    available_berths = []
    for berth in physically_compatible_berths:
        has_conflict, _ = check_time_window_conflict(
            conn=conn,
            berth_id=berth["berth_id"],
            start_dt=start_dt,
            end_dt=end_dt
        )
        if not has_conflict:
            berth_copy = dict(berth)
            berth_copy["length_clearance_m"] = round(berth["max_length_m"] - length_m, 2)
            berth_copy["draft_clearance_m"] = round(berth["max_draft_m"] - draft_m, 2)
            berth_copy["requested_start"] = format_iso(start_dt)
            berth_copy["requested_end"] = format_iso(end_dt)
            available_berths.append(berth_copy)

    conn.close()
    return available_berths

def book_berth(
    vessel_imo: int,
    vessel_name: str,
    berth_id: str,
    start_time: str,
    end_time: str,
    length_m: Optional[float] = None,
    draft_m: Optional[float] = None
) -> Dict[str, Any]:
    """
    Books a qualified berth for a vessel for a specific time window.
    Validates physical constraints and ensures no double-booking collision.
    """
    start_dt = parse_iso_datetime(start_time)
    end_dt = parse_iso_datetime(end_time)

    if end_dt <= start_dt:
        raise ValueError(f"end_time ({end_time}) must be after start_time ({start_time}).")

    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_berth_bookings_table(conn)
    cursor = conn.cursor()

    # 1. Check if berth exists
    cursor.execute("""
        SELECT instance_id, terminal_name, berth_id, max_length_m, max_draft_m, crane_count, crane_handling_rate_teu_hr
        FROM berth_characteristics
        WHERE berth_id = ?
    """, (berth_id,))
    berth_row = cursor.fetchone()

    if not berth_row:
        conn.close()
        raise ValueError(f"Berth '{berth_id}' does not exist in port database.")

    berth = dict(berth_row)

    # 2. Check physical compatibility if dimensions provided
    if length_m is not None and length_m > berth["max_length_m"]:
        conn.close()
        raise ValueError(
            f"Vessel length ({length_m}m) exceeds berth {berth_id} max length ({berth['max_length_m']}m)."
        )
    if draft_m is not None and draft_m > berth["max_draft_m"]:
        conn.close()
        raise ValueError(
            f"Vessel draft ({draft_m}m) exceeds berth {berth_id} max draft ({berth['max_draft_m']}m)."
        )

    # 3. Check duplicate-booking / time-overlap for the same vessel (identified by IMO Number)
    has_vessel_conflict, v_conflict = check_vessel_time_window_conflict(
        conn=conn,
        vessel_imo=vessel_imo,
        start_dt=start_dt,
        end_dt=end_dt
    )
    if has_vessel_conflict:
        conn.close()
        raise ValueError(
            f"Validation Error: Vessel '{vessel_name}' (IMO {vessel_imo}) already has an active conflicting berth reservation at berth {v_conflict['berth_id']} from {v_conflict['start_time']} to {v_conflict['end_time']} during this time window."
        )

    # 4. Check time-window availability on the requested berth (prevent double-booking the berth)
    has_conflict, conflict_info = check_time_window_conflict(
        conn=conn,
        berth_id=berth_id,
        start_dt=start_dt,
        end_dt=end_dt
    )
    if has_conflict:
        conn.close()
        raise ValueError(
            f"Double-booking conflict: Berth {berth_id} is already occupied by "
            f"vessel '{conflict_info['vessel_name']}' (IMO {conflict_info['vessel_imo']}) "
            f"from {conflict_info['start_time']} to {conflict_info['end_time']}."
        )

    # 4. Insert booking
    start_iso = format_iso(start_dt)
    end_iso = format_iso(end_dt)
    cursor.execute("""
        INSERT INTO berth_bookings (vessel_imo, vessel_name, berth_id, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, 'BOOKED')
    """, (vessel_imo, vessel_name, berth_id, start_iso, end_iso))
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()

    duration_hours = (end_dt - start_dt).total_seconds() / 3600.0

    return {
        "booking_id": booking_id,
        "vessel_imo": vessel_imo,
        "vessel_name": vessel_name,
        "berth_id": berth_id,
        "terminal_name": berth["terminal_name"],
        "start_time": start_iso,
        "end_time": end_iso,
        "duration_hours": round(duration_hours, 2),
        "status": "BOOKED",
        "berth_details": berth
    }

def cancel_and_reassign_berth(
    booking_id: Optional[int] = None,
    vessel_imo: Optional[int] = None,
    new_eta: str = None,
    duration_hours: Optional[float] = None,
    auto_reassign: bool = True,
    length_m: Optional[float] = 300.0,
    draft_m: Optional[float] = 12.0
) -> Dict[str, Any]:
    """
    Handles vessel schedule delays (e.g., due to weather/speed degradation).
    If a vessel's ETA drifts:
    1. Updates existing booking status to 'CANCELLED_AND_REASSIGNED'.
    2. Frees up the berth.
    3. Finds the next available compatible berth for the new time window.
    4. Automatically creates a reassigned booking if auto_reassign is True.
    """
    if not new_eta:
        raise ValueError("new_eta is required for dynamic reassignment.")

    new_start_dt = parse_iso_datetime(new_eta)
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_berth_bookings_table(conn)
    cursor = conn.cursor()

    # 1. Find existing active booking
    if booking_id is not None:
        cursor.execute("SELECT * FROM berth_bookings WHERE booking_id = ? AND status = 'BOOKED'", (booking_id,))
    elif vessel_imo is not None:
        cursor.execute(
            "SELECT * FROM berth_bookings WHERE vessel_imo = ? AND status = 'BOOKED' ORDER BY booking_id DESC LIMIT 1",
            (vessel_imo,)
        )
    else:
        conn.close()
        raise ValueError("Either booking_id or vessel_imo must be supplied to identify the booking to reassign.")

    existing_row = cursor.fetchone()
    if not existing_row:
        conn.close()
        raise ValueError("No active 'BOOKED' reservation found for the specified vessel/booking ID.")

    existing = dict(existing_row)
    old_booking_id = existing["booking_id"]
    old_berth_id = existing["berth_id"]
    old_start_dt = parse_iso_datetime(existing["start_time"])
    old_end_dt = parse_iso_datetime(existing["end_time"])

    # Determine duration of stay
    if duration_hours is None or duration_hours <= 0:
        duration_hours = max(2.0, (old_end_dt - old_start_dt).total_seconds() / 3600.0)

    new_end_dt = new_start_dt + timedelta(hours=duration_hours)
    delay_delta_hours = (new_start_dt - old_start_dt).total_seconds() / 3600.0

    # 2. Cancel and mark old booking
    cursor.execute("""
        UPDATE berth_bookings
        SET status = 'CANCELLED_AND_REASSIGNED'
        WHERE booking_id = ?
    """, (old_booking_id,))
    conn.commit()

    # 3. Query physically and temporally available berths for the new window
    # Try using known length and draft or reasonable defaults
    v_length = length_m if length_m is not None else 300.0
    v_draft = draft_m if draft_m is not None else 12.0

    available_candidates = get_available_berths(
        length_m=v_length,
        draft_m=v_draft,
        start_time=format_iso(new_start_dt),
        end_time=format_iso(new_end_dt)
    )

    reassigned_booking = None
    if auto_reassign and available_candidates:
        # Prioritize keeping the original berth if available, otherwise take the best candidate
        chosen_berth = None
        for candidate in available_candidates:
            if candidate["berth_id"] == old_berth_id:
                chosen_berth = candidate
                break
        if chosen_berth is None:
            chosen_berth = available_candidates[0]

        # Create new booking
        new_start_iso = format_iso(new_start_dt)
        new_end_iso = format_iso(new_end_dt)
        cursor.execute("""
            INSERT INTO berth_bookings (vessel_imo, vessel_name, berth_id, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, 'BOOKED')
        """, (existing["vessel_imo"], existing["vessel_name"], chosen_berth["berth_id"], new_start_iso, new_end_iso))
        new_booking_id = cursor.lastrowid
        conn.commit()

        reassigned_booking = {
            "booking_id": new_booking_id,
            "vessel_imo": existing["vessel_imo"],
            "vessel_name": existing["vessel_name"],
            "berth_id": chosen_berth["berth_id"],
            "terminal_name": chosen_berth["terminal_name"],
            "start_time": new_start_iso,
            "end_time": new_end_iso,
            "duration_hours": round(duration_hours, 2),
            "status": "BOOKED",
            "berth_details": chosen_berth
        }

    conn.close()

    return {
        "status": "success",
        "action": "CANCEL_AND_REASSIGN",
        "delay_hours": round(delay_delta_hours, 2),
        "cancelled_booking": {
            "booking_id": old_booking_id,
            "vessel_imo": existing["vessel_imo"],
            "vessel_name": existing["vessel_name"],
            "old_berth_id": old_berth_id,
            "old_start_time": existing["start_time"],
            "old_end_time": existing["end_time"],
            "new_status": "CANCELLED_AND_REASSIGNED"
        },
        "reassigned": reassigned_booking is not None,
        "new_booking": reassigned_booking,
        "available_alternatives_count": len(available_candidates),
        "available_alternatives": available_candidates[:5]
    }

def get_all_bookings(
    status: Optional[str] = None,
    berth_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Returns list of all berth bookings, joined with berth terminal information."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_berth_bookings_table(conn)
    cursor = conn.cursor()

    query = """
        SELECT b.booking_id, b.vessel_imo, b.vessel_name, b.berth_id,
               b.start_time, b.end_time, b.status,
               c.terminal_name, c.max_length_m, c.max_draft_m, c.crane_count, c.crane_handling_rate_teu_hr
        FROM berth_bookings b
        LEFT JOIN berth_characteristics c ON b.berth_id = c.berth_id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND b.status = ?"
        params.append(status.upper())
    if berth_id:
        query += " AND b.berth_id = ?"
        params.append(berth_id)

    query += " ORDER BY b.start_time ASC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def release_berth_booking(
    booking_id: Optional[int] = None,
    berth_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Releases an active booking record in berth_bookings, setting status to 'RELEASED'.
    Frees up the berth immediately and updates port matrix occupancy.
    """
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_berth_bookings_table(conn)
    cursor = conn.cursor()

    if booking_id is not None:
        cursor.execute("SELECT * FROM berth_bookings WHERE booking_id = ?", (booking_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Booking ID #{booking_id} not found in database.")
        booking = dict(row)
        cursor.execute("UPDATE berth_bookings SET status = 'RELEASED' WHERE booking_id = ?", (booking_id,))
    elif berth_id is not None:
        cursor.execute(
            "SELECT * FROM berth_bookings WHERE berth_id = ? AND status = 'BOOKED' ORDER BY booking_id DESC",
            (berth_id,)
        )
        active_bookings = [dict(r) for r in cursor.fetchall()]
        if not active_bookings:
            conn.close()
            raise ValueError(f"No active 'BOOKED' reservation found for berth '{berth_id}'.")
        booking = active_bookings[0]
        cursor.execute("UPDATE berth_bookings SET status = 'RELEASED' WHERE berth_id = ? AND status = 'BOOKED'", (berth_id,))
    else:
        conn.close()
        raise ValueError("Either booking_id or berth_id must be provided to release a berth.")

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Berth {booking['berth_id']} successfully released from booking #{booking['booking_id']} ('{booking['vessel_name']}').",
        "released_booking": {
            **booking,
            "status": "RELEASED"
        }
    }
