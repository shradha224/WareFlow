"""
db.py
-----
Thin wrapper around PyMySQL giving the rest of the backend a simple
`get_db_cursor()` context manager. Every route/job file uses this instead of
opening raw connections, so pooling/transaction behaviour lives in one place.

Used by: every file in routes/, background_jobs.py
"""

import pymysql
import pymysql.cursors
from contextlib import contextmanager
from config import Config


def get_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def get_db_cursor(commit: bool = False):
    """
    Usage:
        with get_db_cursor(commit=True) as cur:
            cur.execute("INSERT ...")

    Automatically commits on success (if commit=True) and rolls back +
    re-raises on any exception so callers never leave a dangling transaction.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
