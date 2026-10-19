"""
Bridge script to expose berth allocation functions at the Backend root level.
"""
from app.berth_allocator import (
    get_available_berths,
    book_berth,
    cancel_and_reassign_berth,
    get_all_bookings,
    ensure_berth_bookings_table
)

__all__ = [
    "get_available_berths",
    "book_berth",
    "cancel_and_reassign_berth",
    "get_all_bookings",
    "ensure_berth_bookings_table"
]
