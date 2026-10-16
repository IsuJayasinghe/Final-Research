"""Yard operations for Yard Block 01: allocation, accept/override, departure, search and summaries.

The in-memory YardState (zone_engine.py) decides slots; every change is written to
common.containers / yard.yard_allocations so the block can be rebuilt after a restart.
Each zone of the block is one row of yard.yard_zones (a "section" with a range of bays).
"""
import threading
import time
from datetime import datetime

from db import ACTIVE_STATUSES, get_db_connection
from predictors import model_metrics
from zone_engine import BLOCK_NAME, ROWS_PER_BAY, SECTION_ZONE, ZONES, YardState, recommend_zone

sim_config = model_metrics['reshuffling_simulation']
yard_lock = threading.Lock()                      # one change to the yard at a time
ZONE_ALERT_PCT = 85                               # FR08 capacity warning threshold


class YardError(Exception):
    """A request that cannot be carried out (unknown container, full zone, ...)."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def load_yard():
    """Build Yard Block 01 from yard.yard_zones and put active allocations back in their slots."""
    layout = model_metrics['block']['layout']
    saved = []
    conn = get_db_connection()
    if conn:
        try:
            with conn, conn.cursor() as cur:
                cur.execute("""SELECT yard_zone_id, first_bay, bay_count, rows_per_bay FROM yard.yard_zones
                               WHERE first_bay IS NOT NULL ORDER BY first_bay""")
                rows = cur.fetchall()
                if rows:
                    layout = {section: {'first_bay': first, 'bays': bays, 'rows': rows_ or ROWS_PER_BAY}
                              for section, first, bays, rows_ in rows}
                cur.execute("""SELECT a.container_id, c.container_type, a.yard_zone_id, a.stack_number,
                                      EXTRACT(EPOCH FROM a.predicted_departure) / 3600
                               FROM yard.yard_allocations a
                               JOIN common.containers c ON c.container_id = a.container_id
                               WHERE a.allocation_status IN %s AND a.stack_number IS NOT NULL
                               ORDER BY a.stack_number, a.tier""", (ACTIVE_STATUSES,))
                saved = cur.fetchall()
        except Exception as db_error:
            print(f"Could not load yard from database: {db_error}")
        finally:
            conn.close()
    state = YardState(layout, sim_config['tier_height'],
                      rule=sim_config['ai_rule']['rule'], margin_h=sim_config['ai_rule']['margin_hours'])
    for container_id, ctype, section, stack_number, dep_h in saved:
        if section in state.section_stacks:
            state.place_exact(container_id, ctype, float(dep_h or 0), section, stack_number)
    print(f" {BLOCK_NAME} loaded: {len(state.location)} containers in {len(state.stacks)} stacks "
          f"({state.bay_count} bays)")
    return state


yard = load_yard()


def _connect():
    conn = get_db_connection()
    if conn is None:
        raise YardError('Database is not available', 503)
    return conn


def _update_zone_occupancy(cur):
    cur.execute("""UPDATE yard.yard_zones z SET current_occupancy =
                       (SELECT COUNT(*) FROM yard.yard_allocations a
                        WHERE a.yard_zone_id = z.yard_zone_id AND a.allocation_status IN %s)""",
                (ACTIVE_STATUSES,))


def _save_position(cur, container_id):
    """Write a container's current section / stack / tier / slot to its active allocation."""
    section, stack_number, tier = yard.position(container_id)
    slot = yard.slot_id(yard.location[container_id], tier)
    cur.execute("""UPDATE yard.yard_allocations SET yard_zone_id = %s, stack_number = %s, tier = %s, slot_id = %s
                   WHERE container_id = %s AND allocation_status IN %s""",
                (section, stack_number, tier, slot, container_id, ACTIVE_STATUSES))
    return slot


def _relocate(cur, moved_ids):
    """Re-place containers that were lifted off a stack (reshuffles) and save their new slots."""
    relocated = []
    now_h = time.time() / 3600
    for cid in moved_ids:
        dep_h = yard.predicted_departure_h[cid]
        remaining_days = max(0.0, (dep_h - now_h) / 24)
        slot = yard.place(cid, yard.container_type[cid], remaining_days, dep_h)
        if slot:
            relocated.append({'container_id': cid, 'new_slot': _save_position(cur, cid)})
    return relocated


def allocate(container, dwell_days, model_used):
    """Recommend a zone and reserve a slot for an arriving container (FR01-FR06)."""
    container_id = (container.get('container_id') or '').strip().upper()
    if not container_id:
        raise YardError('container_id is required')
    container_type = (container.get('container_type') or 'DRY').upper()
    rec = recommend_zone(container_type, dwell_days)

    with yard_lock:
        conn = _connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO common.containers
                           (container_id, container_size, container_type, shipping_line, weight_category, cargo_type)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (container_id) DO UPDATE SET
                           container_type = EXCLUDED.container_type,
                           container_size = COALESCE(EXCLUDED.container_size, common.containers.container_size),
                           shipping_line = COALESCE(EXCLUDED.shipping_line, common.containers.shipping_line),
                           weight_category = COALESCE(EXCLUDED.weight_category, common.containers.weight_category),
                           cargo_type = COALESCE(EXCLUDED.cargo_type, common.containers.cargo_type)""",
                    (container_id, container.get('container_size'), container_type, container.get('shipping_line'),
                     container.get('weight_category'), container.get('cargo_type')))

                # A new recommendation replaces any earlier active one for this container
                relocated = []
                if container_id in yard.location:
                    relocated = yard.retrieve(container_id)
                cur.execute("""UPDATE yard.yard_allocations SET allocation_status = 'CANCELLED', released_at = NOW()
                               WHERE container_id = %s AND allocation_status IN %s""",
                            (container_id, ACTIVE_STATUSES))

                predicted_departure_h = time.time() / 3600 + dwell_days * 24
                slot = yard.place(container_id, container_type, dwell_days, predicted_departure_h)
                if slot is None:
                    raise YardError('Yard is full - no slot available', 409)
                section, stack_number, tier = yard.position(container_id)
                cur.execute(
                    """INSERT INTO yard.yard_allocations
                           (container_id, yard_zone_id, recommended_yard_zone_id, stack_number, tier, slot_id,
                            predicted_dwell_days, predicted_departure, dwell_class, recommended_zone,
                            recommendation_reason, model_used, allocation_status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, NOW() + make_interval(secs => %s), %s, %s, %s, %s, 'RECOMMENDED')
                       RETURNING yard_allocation_id""",
                    (container_id, section, section, stack_number, tier, slot, round(dwell_days, 2), dwell_days * 86400,
                     rec['dwell_class'], rec['zone'], rec['reason'], model_used))
                allocation_id = cur.fetchone()[0]
                cur.execute("""INSERT INTO yard.dwell_predictions (container_id, prediction_date, predicted_dwell_days, model_name)
                               VALUES (%s, CURRENT_DATE, %s, %s)""", (container_id, round(dwell_days, 2), model_used))
                relocated = _relocate(cur, relocated)
                _update_zone_occupancy(cur)
        except Exception:
            # keep memory and database consistent: rebuild the yard from what was committed
            _reload()
            raise
        finally:
            conn.close()

    return {'allocation_id': allocation_id, 'container_id': container_id, 'container_type': container_type,
            'predicted_dwell_days': round(dwell_days, 2), 'model_used': model_used,
            'dwell_class': rec['dwell_class'], 'compatibility': rec['compatibility'],
            'recommended_zone': rec['zone'], 'block': BLOCK_NAME, 'section': section, 'slot': slot,
            'reason': rec['reason'],
            'allocation_status': 'RECOMMENDED', 'relocated': relocated,
            'zone_occupancy': yard.zone_occupancy()[rec['zone']]}


def _get_active_allocation(cur, allocation_id):
    cur.execute("""SELECT container_id, allocation_status FROM yard.yard_allocations WHERE yard_allocation_id = %s""",
                (allocation_id,))
    row = cur.fetchone()
    if row is None:
        raise YardError(f'Allocation {allocation_id} not found', 404)
    if row[1] not in ACTIVE_STATUSES:
        raise YardError(f'Allocation {allocation_id} is {row[1]} and can no longer be changed', 409)
    return row[0]


def accept(allocation_id):
    """FR07: yard manager accepts the AI recommendation."""
    with yard_lock:
        conn = _connect()
        try:
            with conn, conn.cursor() as cur:
                container_id = _get_active_allocation(cur, allocation_id)
                cur.execute("""UPDATE yard.yard_allocations SET allocation_status = 'ACCEPTED', decided_at = NOW()
                               WHERE yard_allocation_id = %s RETURNING slot_id, yard_zone_id""", (allocation_id,))
                slot, section = cur.fetchone()
        finally:
            conn.close()
    return {'allocation_id': allocation_id, 'container_id': container_id, 'allocation_status': 'ACCEPTED',
            'zone': SECTION_ZONE.get(section), 'section': section, 'slot': slot}


def override(allocation_id, target, reason):
    """FR07: yard manager moves the container to another zone of the block instead."""
    section = target if target in SECTION_ZONE else (ZONES[target]['section'] if target in ZONES else None)
    if section is None:
        raise YardError(f"Unknown zone '{target}'. Use one of: {', '.join(ZONES)}")
    if not reason:
        raise YardError('An override reason is required')

    with yard_lock:
        conn = _connect()
        try:
            with conn, conn.cursor() as cur:
                container_id = _get_active_allocation(cur, allocation_id)
                if container_id not in yard.location:
                    raise YardError(f'{container_id} is not in the yard', 409)
                ctype = yard.container_type[container_id]
                dep_h = yard.predicted_departure_h[container_id]
                above = yard.retrieve(container_id)
                slot = yard.place_at(container_id, ctype, dep_h, section)
                if slot is None:
                    raise YardError(f'{target} is full', 409)
                section, stack_number, tier = yard.position(container_id)
                cur.execute("""UPDATE yard.yard_allocations SET allocation_status = 'OVERRIDDEN', decided_at = NOW(),
                                      override_reason = %s, yard_zone_id = %s, stack_number = %s, tier = %s, slot_id = %s
                               WHERE yard_allocation_id = %s""",
                            (reason, section, stack_number, tier, slot, allocation_id))
                relocated = _relocate(cur, above)
                _update_zone_occupancy(cur)
        except Exception:
            _reload()
            raise
        finally:
            conn.close()
    return {'allocation_id': allocation_id, 'container_id': container_id, 'allocation_status': 'OVERRIDDEN',
            'zone': SECTION_ZONE[section], 'section': section, 'slot': slot, 'override_reason': reason,
            'relocated': relocated, 'reshuffles': len(relocated)}


def depart(container_id):
    """Container leaves the yard: free its slot and relocate any containers stacked on top."""
    container_id = container_id.upper()
    with yard_lock:
        if container_id not in yard.location:
            raise YardError(f'{container_id} is not in the yard', 404)
        conn = _connect()
        try:
            with conn, conn.cursor() as cur:
                slot = yard.slot_id(yard.location[container_id], yard.position(container_id)[2])
                above = yard.retrieve(container_id)
                cur.execute("""UPDATE yard.yard_allocations SET allocation_status = 'RELEASED', released_at = NOW()
                               WHERE container_id = %s AND allocation_status IN %s""",
                            (container_id, ACTIVE_STATUSES))
                relocated = _relocate(cur, above)
                _update_zone_occupancy(cur)
        except Exception:
            _reload()
            raise
        finally:
            conn.close()
    return {'container_id': container_id, 'allocation_status': 'RELEASED', 'freed_slot': slot,
            'reshuffles': len(relocated), 'relocated': relocated}


def _reload():
    global yard
    fresh = load_yard()
    yard.__dict__.update(fresh.__dict__)


# QUERIES FOR THE SCREENS

CONTAINER_COLUMNS = """a.yard_allocation_id, a.container_id, c.container_type, c.container_size, c.cargo_type,
    c.shipping_line, a.recommended_zone, a.yard_zone_id, a.slot_id, a.predicted_dwell_days, a.dwell_class,
    a.allocated_at, a.predicted_departure, a.released_at, a.allocation_status, a.override_reason,
    a.recommendation_reason, a.model_used"""


def _container_row(row):
    (allocation_id, cid, ctype, size, cargo, line, rec_zone, section, slot, dwell, dwell_class,
     allocated_at, predicted_departure, released_at, status, override_reason, reason, model_used) = row
    active = status in ACTIVE_STATUSES
    overstaying = bool(active and predicted_departure and predicted_departure < datetime.now())
    return {'allocation_id': allocation_id, 'container_id': cid, 'container_type': ctype, 'container_size': size,
            'cargo_type': cargo, 'shipping_line': line, 'recommended_zone': rec_zone,
            'zone': SECTION_ZONE.get(section), 'section': section, 'slot': slot,
            'predicted_dwell_days': float(dwell) if dwell is not None else None, 'dwell_class': dwell_class,
            'arrival': allocated_at.isoformat() if allocated_at else None,
            'predicted_departure': predicted_departure.isoformat() if predicted_departure else None,
            'released_at': released_at.isoformat() if released_at else None,
            'allocation_status': status, 'status': 'Overstaying' if overstaying else ('Active' if active else 'Released'),
            'override_reason': override_reason, 'reason': reason, 'model_used': model_used}


def search_containers(search=None, container_type=None, zone=None, status=None, page=1, limit=20):
    """FR09: search by container ID, filter by type, zone and status (active / overstaying / released)."""
    where, params = ["a.allocation_status <> 'CANCELLED'"], []
    if search:
        where.append('(a.container_id ILIKE %s OR a.slot_id ILIKE %s)')
        params += [f'%{search}%', f'%{search}%']
    if container_type:
        where.append('UPPER(c.container_type) = %s')
        params.append(container_type.upper())
    if zone:
        where.append('a.yard_zone_id = %s')
        params.append(ZONES[zone]['section'] if zone in ZONES else zone)
    status = (status or '').lower()
    if status == 'active':
        where.append('a.allocation_status IN %s')
        params.append(ACTIVE_STATUSES)
    elif status == 'overstaying':
        where.append('a.allocation_status IN %s AND a.predicted_departure < NOW()')
        params.append(ACTIVE_STATUSES)
    elif status == 'released':
        where.append("a.allocation_status = 'RELEASED'")

    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            base = f"""FROM yard.yard_allocations a JOIN common.containers c ON c.container_id = a.container_id
                       WHERE {' AND '.join(where)}"""
            cur.execute('SELECT COUNT(*) ' + base, params)
            total = cur.fetchone()[0]
            cur.execute(f'SELECT {CONTAINER_COLUMNS} {base} ORDER BY a.allocated_at DESC LIMIT %s OFFSET %s',
                        params + [limit, (page - 1) * limit])
            rows = [_container_row(r) for r in cur.fetchall()]
            cur.execute("""SELECT COUNT(*) FILTER (WHERE allocation_status IN %s),
                                  COUNT(*) FILTER (WHERE allocation_status IN %s AND predicted_departure < NOW())
                           FROM yard.yard_allocations""", (ACTIVE_STATUSES, ACTIVE_STATUSES))
            active, overstaying = cur.fetchone()
    finally:
        conn.close()
    return {'total': total, 'page': page, 'limit': limit, 'containers': rows,
            'counts': {'active': active, 'overstaying': overstaying}}


def get_container(container_id):
    """Current (or last) allocation of one container - also used by the drayage component."""
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(f"""SELECT {CONTAINER_COLUMNS} FROM yard.yard_allocations a
                            JOIN common.containers c ON c.container_id = a.container_id
                            WHERE a.container_id = %s AND a.allocation_status <> 'CANCELLED'
                            ORDER BY a.allocated_at DESC LIMIT 1""", (container_id.upper(),))
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        raise YardError(f'{container_id} not found', 404)
    return _container_row(row)


def yard_zones():
    """Yard Map: Yard Block 01 with occupancy per zone and the height of every stack (bay x row)."""
    zones = yard.zone_occupancy()
    sections = []
    for section, idx in yard.section_stacks.items():
        spec = yard.layout[section]
        heights = [len(yard.stacks[i]) for i in idx]          # bay by bay, rows 1..n within a bay
        capacity = len(idx) * yard.tier_height
        used = sum(heights)
        sections.append({'section': section, 'zone': SECTION_ZONE.get(section), 'first_bay': spec['first_bay'],
                         'bays': spec['bays'], 'rows': spec['rows'], 'tier_height': yard.tier_height,
                         'capacity': capacity, 'used': used,
                         'utilization_pct': round(used / capacity * 100, 1) if capacity else 0.0,
                         'stack_heights': heights})
    total_capacity = sum(z['capacity'] for z in zones.values())
    total_used = sum(z['used'] for z in zones.values())
    return {'block': {'name': BLOCK_NAME, 'bays': yard.bay_count, 'rows': max(sp['rows'] for sp in yard.layout.values()),
                      'tier_height': yard.tier_height, 'stacks': len(yard.stacks)},
            'zones': [{'zone': name, 'section': ZONES[name]['section'], 'description': ZONES[name]['description'], **info}
                      for name, info in zones.items()],
            'sections': sections,
            'total': {'used': total_used, 'capacity': total_capacity,
                      'utilization_pct': round(total_used / total_capacity * 100, 1) if total_capacity else 0.0}}


def zone_alerts():
    """FR08 (current state): zones at or above the 85% threshold right now."""
    return [{'type': 'zone_capacity', 'zone': name, 'utilization_pct': info['utilization_pct'],
             'message': f"{name} zone is {info['utilization_pct']}% full"}
            for name, info in yard.zone_occupancy().items() if info['utilization_pct'] >= ZONE_ALERT_PCT]


def dashboard_summary():
    conn = _connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute("""SELECT
                    COUNT(*) FILTER (WHERE allocation_status IN %s),
                    COUNT(*) FILTER (WHERE allocated_at::date = CURRENT_DATE AND allocation_status <> 'CANCELLED'),
                    COUNT(*) FILTER (WHERE released_at::date = CURRENT_DATE AND allocation_status = 'RELEASED'),
                    COUNT(*) FILTER (WHERE allocation_status IN %s AND predicted_departure::date = CURRENT_DATE),
                    COUNT(*) FILTER (WHERE allocation_status IN %s AND predicted_departure < NOW())
                FROM yard.yard_allocations""", (ACTIVE_STATUSES, ACTIVE_STATUSES, ACTIVE_STATUSES))
            in_yard, arrived_today, departed_today, due_today, overstaying = cur.fetchone()
            cur.execute(f"""SELECT {CONTAINER_COLUMNS} FROM yard.yard_allocations a
                            JOIN common.containers c ON c.container_id = a.container_id
                            WHERE a.allocation_status <> 'CANCELLED'
                            ORDER BY a.allocated_at DESC LIMIT 10""")
            recent = [_container_row(r) for r in cur.fetchall()]
    finally:
        conn.close()
    zones = yard_zones()
    return {'total_containers': in_yard, 'yard_occupancy_pct': zones['total']['utilization_pct'],
            'arrived_today': arrived_today, 'departed_today': departed_today,
            'expected_departures_today': due_today, 'overstaying': overstaying,
            'zone_occupancy': zones['zones'], 'recent_allocations': recent, 'alerts': zone_alerts()}
