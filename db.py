"""
STUDENT SKILL AND PROJECT MATCHING SYSTEM — database helper.

Every function that talks to MySQL goes through this file, so the
rest of the app never deals with connection details directly.

Security note: we ALWAYS use parameterized queries (%s placeholders),
never Python string formatting with user input — that is how SQL
injection attacks happen.
"""

import mysql.connector

from config import db_config


def connect():
    """Opens and returns a fresh MySQL connection."""
    return mysql.connector.connect(**db_config)


def query(sql, params=()):
    """
    Runs a SELECT and returns a list of dicts, one per row.

    Example:
        rows = db.query(
            "SELECT * FROM projects WHERE status = %s", ("OPEN",)
        )
    """
    conn = connect()
    try:
        cursor = conn.cursor(dictionary=True)  # rows come back as dicts
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def execute(sql, params=()):
    """
    Runs an INSERT/UPDATE/DELETE and commits it.
    Returns the number of rows affected.
    """
    conn = connect()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()  # without commit, the change is lost on disconnect
        return cursor.rowcount
    finally:
        conn.close()
