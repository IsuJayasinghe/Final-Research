"""Load demo containers into Yard Block 01 in the local database (for the dashboard demo).

Uses real containers from the Colombo Port data (ID, type, size, shipping line, cargo).
Each container arrives at a time in the last few days, gets its dwell time from the
per-container model and is allocated by the zone engine - exactly like a real arrival.
Most recommendations are accepted, a few overridden, and containers leave in time order
when their (actual) stay is over - so the block ends up about half full, with real reshuffles.

Run from backend/yard (stop the API first, start it again afterwards). Takes under a minute:
    python scripts/load_demo_data.py --reset

--reset removes ALL containers and allocations from the yard tables first.
"""
import argparse
import heapq
import os
import random
import sys
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yard_service  # noqa: E402
from db import get_db_connection  # noqa: E402
from predictors import predict_container_dwell  # noqa: E402

COLOMBO_CSV = os.environ.get('COLOMBO_CSV', r'C:\Users\CYBORG 15\Downloads\container_yard_data.csv')


class SharedConnection:
    """One database connection for the whole load (opening one per call made loading very slow).
    Each `with conn:` block is still its own transaction; close() keeps the connection open."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn.__enter__()

    def __exit__(self, *exc):
        return self.conn.__exit__(*exc)

    def cursor(self):
        return self.conn.cursor()

    def close(self):
        pass


_shared = SharedConnection(get_db_connection())
yard_service.get_db_connection = lambda: _shared
get_db_connection = yard_service.get_db_connection  # noqa: F811
OVERRIDE_REASONS = ['Customs inspection expected', 'Shipping line requested a different zone',
                    'Block under maintenance', 'Container held for documentation']


def reset():
    conn = get_db_connection()
    with conn, conn.cursor() as cur:
        cur.execute('DELETE FROM yard.dwell_predictions WHERE container_id IS NOT NULL')
        cur.execute('DELETE FROM yard.yard_allocations')
        cur.execute('DELETE FROM common.containers c WHERE NOT EXISTS '
                    '(SELECT 1 FROM yard.yard_allocations a WHERE a.container_id = c.container_id)')
        yard_service._update_zone_occupancy(cur)
    conn.close()
    yard_service._reload()
    print('Yard tables cleared')


def backdate(container_id, arrival, dwell_days, released_at=None):
    conn = get_db_connection()
    with conn, conn.cursor() as cur:
        cur.execute("""UPDATE yard.yard_allocations
                       SET allocated_at = %s, predicted_departure = %s,
                           decided_at = CASE WHEN decided_at IS NULL THEN NULL ELSE %s END,
                           released_at = COALESCE(%s, released_at)
                       WHERE container_id = %s AND allocation_status <> 'CANCELLED'""",
                    (arrival, arrival + timedelta(days=dwell_days), arrival + timedelta(minutes=5),
                     released_at, container_id))
    conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--count', type=int, default=1250, help='number of containers to load')
    parser.add_argument('--days', type=int, default=7, help='spread arrivals over the last N days')
    parser.add_argument('--reset', action='store_true', help='clear the yard tables first')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    if args.reset:
        reset()

    colombo = pd.read_csv(COLOMBO_CSV)
    if args.count <= len(colombo):
        colombo = colombo.sample(n=args.count, random_state=args.seed)
    else:
        # more containers than the file has: same type/line/cargo mix, new container numbers
        colombo = colombo.sample(n=args.count, replace=True, random_state=args.seed).reset_index(drop=True)
        used = set()
        for i, owner in enumerate(colombo['Container_ID'].str[:4]):
            number = f"{owner}{rng.randrange(10**6, 10**7)}"
            while number in used:
                number = f"{owner}{rng.randrange(10**6, 10**7)}"
            used.add(number)
            colombo.loc[i, 'Container_ID'] = number
    now = datetime.now()
    arrivals = sorted(now - timedelta(hours=rng.uniform(0.5, args.days * 24)) for _ in range(args.count))

    stats = {'allocated': 0, 'accepted': 0, 'overridden': 0, 'departed': 0, 'reshuffles': 0, 'yard_full': 0}
    leaving = []                                     # heap of (leave time, container, arrival, predicted dwell)

    def depart_until(moment):
        """Containers whose (actual) stay ended before `moment` leave the yard - in time order."""
        while leaving and leaving[0][0] <= moment:
            left_at, container_id, arrival, dwell = heapq.heappop(leaving)
            result = yard_service.depart(container_id)
            stats['departed'] += 1
            stats['reshuffles'] += result['reshuffles']
            backdate(container_id, arrival, dwell, released_at=left_at)

    for (_, row), arrival in zip(colombo.iterrows(), arrivals):
        depart_until(arrival)
        cargo = row['Cargo_Type']
        container = {
            'container_id': row['Container_ID'], 'container_type': row['Container_Type'],
            'container_size': row['Container_Size'], 'shipping_line': row['Shipping_Line'],
            'weight_category': row['Weight_Category'], 'cargo_type': cargo,
            # status known at discharge (shares similar to the Kaggle data)
            'customs_cleared': int(rng.random() < 0.43),
            'quarantine_flag': int(rng.random() < (0.6 if any(w in cargo for w in ('Perishable', 'Frozen', 'Fruit', 'Tea')) else 0.12)),
            'customs_red_lane': int(rng.random() < 0.03),
        }
        dwell = predict_container_dwell(container, arrival)
        try:
            result = yard_service.allocate(container, dwell, 'XGBoost per-container')
        except yard_service.YardError:
            stats['yard_full'] += 1
            continue
        stats['allocated'] += 1

        decision = rng.random()
        occupancy = yard_service.yard.zone_occupancy()
        targets = [z for z in ('Fast-Access', 'Medium-Access', 'Long-Term')
                   if z != result['recommended_zone'] and occupancy[z]['utilization_pct'] < 80]
        if decision < 0.08 and targets and row['Container_Type'] not in ('REEFER', 'HAZMAT'):
            yard_service.override(result['allocation_id'], rng.choice(targets), rng.choice(OVERRIDE_REASONS))
            stats['overridden'] += 1
        elif decision < 0.90:
            yard_service.accept(result['allocation_id'])
            stats['accepted'] += 1
        backdate(container['container_id'], arrival, dwell)

        # actual stay differs from the prediction; some containers stay on past it (overstaying)
        actual = dwell * rng.lognormvariate(0, 0.45)
        if rng.random() < 0.9:
            heapq.heappush(leaving, (arrival + timedelta(days=actual), container['container_id'], arrival, dwell))

    depart_until(now)
    print(f"Loaded demo data: {stats}")
    print(f"Containers now in the yard: {len(yard_service.yard.location)}")
    print('Restart the API so it loads the new yard state.')


if __name__ == '__main__':
    main()
