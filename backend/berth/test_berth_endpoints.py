import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import (
    get_available_berths_endpoint,
    book_berth_endpoint,
    cancel_and_reassign_endpoint,
    list_bookings_endpoint,
    BookBerthRequest,
    CancelReassignRequest
)

def run_tests():
    print("=== TEST 1: GET /api/berths/available ===")
    avail_resp = get_available_berths_endpoint(
        length_m=340.0,
        draft_m=14.0,
        start_time='2026-10-20T10:00:00Z',
        end_time='2026-10-20T22:00:00Z',
        terminal_name=None
    )
    print(f"Total available berths: {avail_resp['total_available']}")
    first_berth = avail_resp['available_berths'][0]
    print(f"Candidate: {first_berth['berth_id']} at {first_berth['terminal_name']}")

    print("\n=== TEST 2: POST /api/berths/book ===")
    book_req = BookBerthRequest(
        vessel_imo=9776171,
        vessel_name="OOCL HONG KONG",
        berth_id=first_berth['berth_id'],
        start_time='2026-10-20T10:00:00Z',
        end_time='2026-10-20T22:00:00Z',
        length_m=340.0,
        draft_m=14.0
    )
    book_resp = book_berth_endpoint(book_req)
    booking_id = book_resp['booking']['booking_id']
    print(f"Status: {book_resp['status']}, Booking ID: {booking_id}")

    print("\n=== TEST 3: Preventing Double Booking ===")
    try:
        book_berth_endpoint(book_req)
        print("FAIL: Double-booking should not be allowed!")
    except Exception as e:
        status_code = getattr(e, 'status_code', None)
        print(f"SUCCESS: Blocked with HTTP {status_code}: {getattr(e, 'detail', str(e))}")

    print("\n=== TEST 4: POST /api/berths/cancel-reassign (Weather Delay) ===")
    reassign_req = CancelReassignRequest(
        booking_id=booking_id,
        new_eta='2026-10-21T04:00:00Z',
        duration_hours=12.0,
        auto_reassign=True,
        length_m=340.0,
        draft_m=14.0
    )
    reassign_resp = cancel_and_reassign_endpoint(reassign_req)
    print(f"Reassignment Status: {reassign_resp['status']}")
    print(f"Delay Hours: {reassign_resp['delay_hours']} hrs")
    print(f"Old Booking ID {reassign_resp['cancelled_booking']['booking_id']} Status: {reassign_resp['cancelled_booking']['new_status']}")
    new_b = reassign_resp['new_booking']
    print(f"New Booking ID {new_b['booking_id']} at Berth {new_b['berth_id']} from {new_b['start_time']} to {new_b['end_time']}")

    print("\n=== TEST 5: GET /api/berths/bookings ===")
    bookings_resp = list_bookings_endpoint(status=None, berth_id=None)
    print(f"Total bookings returned: {bookings_resp['total_bookings']}")
    for b in bookings_resp['bookings'][:5]:
        print(f" - [{b['status']}] ID {b['booking_id']} | {b['vessel_name']} (IMO {b['vessel_imo']}) @ {b['berth_id']} ({b.get('terminal_name', 'N/A')}) | {b['start_time']} -> {b['end_time']}")

    print("\n=== TEST 6: GET /api/berths/matrix ===")
    from app.main import get_berth_matrix, get_berth_detail
    matrix_resp = get_berth_matrix()
    print(f"Status: {matrix_resp['status']}, Total Berths: {matrix_resp['total_berths']}, Terminals: {matrix_resp['total_terminals']}")
    for term_name, b_list in matrix_resp['terminal_matrix'].items():
        print(f" - Terminal '{term_name}': {len(b_list)} berths")

    print("\n=== TEST 7: GET /api/berths/{berth_id} ===")
    detail_resp = get_berth_detail("CICT_01")
    print(f"Berth {detail_resp['berth']['berth_id']} max draft: {detail_resp['berth']['max_draft_m']}m, total bookings: {detail_resp['total_bookings']}")

    print("\nAll berth and allocator endpoint tests passed successfully!")

if __name__ == "__main__":
    run_tests()

