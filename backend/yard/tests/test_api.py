"""API tests. Run from backend/yard:  python -m pytest tests -q

Needs the local PostgreSQL database (DB_PASSWORD in .env). Test containers use IDs starting
with ZZTEST and are deleted before and after the tests.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yard_service  # noqa: E402
from app import app  # noqa: E402
from db import get_db_connection  # noqa: E402


def cleanup():
    conn = get_db_connection()
    with conn, conn.cursor() as cur:
        cur.execute("DELETE FROM yard.dwell_predictions WHERE container_id LIKE 'ZZTEST%'")
        cur.execute("DELETE FROM yard.yard_allocations WHERE container_id LIKE 'ZZTEST%'")
        cur.execute("DELETE FROM common.containers WHERE container_id LIKE 'ZZTEST%'")
        yard_service._update_zone_occupancy(cur)
    conn.close()
    yard_service._reload()


@pytest.fixture(scope='module')
def client():
    if get_db_connection() is None:
        pytest.skip('PostgreSQL is not available')
    cleanup()
    yield app.test_client()
    cleanup()


def arrive(client, **container):
    response = client.post('/api/containers/arrival', json=container)
    return response.status_code, response.get_json()


def test_health(client):
    data = client.get('/api/health').get_json()
    assert data['status'] == 'healthy' and data['database'] == 'connected'


def test_arrival_uses_per_container_model(client):
    code, data = arrive(client, container_id='ZZTEST00001', container_type='DRY',
                        shipping_line='Maersk', customs_cleared=1, quarantine_flag=0)
    assert code == 200
    assert data['model_used'] == 'XGBoost per-container'
    assert 0 < data['predicted_dwell_days'] < 30
    assert data['slot'] and data['allocation_id']


@pytest.mark.parametrize('cid, ctype, dwell, zone, dwell_class', [
    ('ZZTEST00002', 'REEFER', 4, 'Reefer', 'Medium-stay'),
    ('ZZTEST00003', 'hazmat', 2, 'Hazardous', 'Short-stay'),
    ('ZZTEST00004', 'DRY', 3, 'Medium-Access', 'Medium-stay'),      # exactly 3 days = medium (proposal)
    ('ZZTEST00005', 'DRY', 10, 'Long-Term', 'Long-stay'),
    ('ZZTEST00006', 'OVERSIZED', 1, 'Fast-Access', 'Short-stay'),
])
def test_zone_rules(client, cid, ctype, dwell, zone, dwell_class):
    code, data = arrive(client, container_id=cid, container_type=ctype, dwell_days=dwell)
    assert code == 200
    assert data['recommended_zone'] == zone and data['dwell_class'] == dwell_class


def test_missing_container_id(client):
    code, data = arrive(client, container_type='DRY', dwell_days=2)
    assert code == 400 and data['status'] == 'error'


def test_accept(client):
    _, data = arrive(client, container_id='ZZTEST00010', container_type='DRY', dwell_days=2)
    accepted = client.post(f"/api/allocations/{data['allocation_id']}/accept").get_json()
    assert accepted['allocation_status'] == 'ACCEPTED' and accepted['slot'] == data['slot']


def test_override(client):
    _, data = arrive(client, container_id='ZZTEST00011', container_type='DRY', dwell_days=2)
    url = f"/api/allocations/{data['allocation_id']}/override"
    assert client.post(url, json={'zone': 'Long-Term'}).status_code == 400          # reason required
    assert client.post(url, json={'zone': 'Nowhere', 'reason': 'x'}).status_code == 400
    moved = client.post(url, json={'zone': 'Medium-Access', 'reason': 'Customs hold expected'}).get_json()
    assert moved['allocation_status'] == 'OVERRIDDEN' and moved['section'] == 'YB01_MEDIUM'
    assert moved['slot'].startswith('B01-')


def test_reallocation_cancels_previous(client):
    _, first = arrive(client, container_id='ZZTEST00012', container_type='DRY', dwell_days=2)
    _, second = arrive(client, container_id='ZZTEST00012', container_type='DRY', dwell_days=5)
    assert second['recommended_zone'] == 'Medium-Access'
    stale = client.post(f"/api/allocations/{first['allocation_id']}/accept")
    assert stale.status_code == 409                                                  # old one is CANCELLED


def test_placed_container_cannot_arrive_again(client):
    _, data = arrive(client, container_id='ZZTEST00014', container_type='DRY', dwell_days=2)
    client.post(f"/api/allocations/{data['allocation_id']}/accept")
    code, again = arrive(client, container_id='ZZTEST00014', container_type='DRY', dwell_days=2)
    assert code == 409 and data['slot'] in again['message']                          # still in the yard
    client.post('/api/containers/ZZTEST00014/depart')
    code, back = arrive(client, container_id='ZZTEST00014', container_type='DRY', dwell_days=2)
    assert code == 200 and back['allocation_status'] == 'RECOMMENDED'                # a later visit is fine


def test_depart(client):
    _, data = arrive(client, container_id='ZZTEST00013', container_type='DRY', dwell_days=2)
    left = client.post('/api/containers/ZZTEST00013/depart').get_json()
    assert left['allocation_status'] == 'RELEASED' and left['freed_slot'] == data['slot']
    assert client.post('/api/containers/ZZTEST00013/depart').status_code == 404
    assert client.get('/api/containers/ZZTEST00013').get_json()['container']['status'] == 'Released'


def test_search_and_filters(client):
    data = client.get('/api/containers?search=ZZTEST&type=REEFER').get_json()
    assert data['total'] == 1 and data['containers'][0]['container_id'] == 'ZZTEST00002'
    released = client.get('/api/containers?search=ZZTEST&status=released').get_json()
    assert {c['container_id'] for c in released['containers']} == {'ZZTEST00013', 'ZZTEST00014'}
    reefer = client.get('/api/containers?search=ZZTEST&zone=Reefer').get_json()
    assert {c['container_id'] for c in reefer['containers']} == {'ZZTEST00002'}


def test_container_not_found(client):
    assert client.get('/api/containers/NOSUCH00000').status_code == 404


def test_yard_reloads_after_restart(client):
    before = dict(yard_service.yard.location)
    yard_service._reload()
    assert {k for k in yard_service.yard.location if k.startswith('ZZTEST')} == \
           {k for k in before if k.startswith('ZZTEST')}


def test_yard_zones_and_dashboard(client):
    zones = client.get('/api/yard/zones').get_json()
    assert zones['block']['name'] == 'Yard Block 01'
    assert len(zones['zones']) == 5 and len(zones['sections']) == 5        # one block, five zones
    assert zones['total']['capacity'] == zones['block']['stacks'] * zones['block']['tier_height']
    summary = client.get('/api/dashboard/summary').get_json()
    for key in ['total_containers', 'yard_occupancy_pct', 'overstaying', 'zone_occupancy', 'recent_allocations']:
        assert key in summary


def test_forecasts_and_alerts(client):
    dwell = client.get('/api/predict-dwell?days=7').get_json()
    assert len(dwell['prophet_predictions']) == 7 and dwell['model_comparison']['recommended'] == 'Prophet'
    occupancy = client.get('/api/occupancy?days=5&capacity=800').get_json()
    assert len(occupancy['predictions']) == 5 and occupancy['alerts']               # small capacity -> alert
    assert 'alerts' in client.get('/api/alerts').get_json()


def test_reports(client):
    assert client.get('/api/reshuffling-stats').get_json()['simulation_results']['reshuffle_reduction_pct'] > 25
    assert 'dwell_time' in client.get('/api/models/metrics').get_json()['metrics']
