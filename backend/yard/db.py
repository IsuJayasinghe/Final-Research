"""Database settings and connection for the yard component.

Settings are read from environment variables or a local .env file (see .env.example).
Local database for now (smart_port_db); set DB_NAME=smart_port_management for the shared one.
Tables: common.containers + yard.* (database/schema/01, 02, 05 and 08).
"""
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'smart_port_db'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', ''),
}

# Allocation statuses that still occupy a slot in the yard
ACTIVE_STATUSES = ('RECOMMENDED', 'ACCEPTED', 'OVERRIDDEN')


def get_db_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None
