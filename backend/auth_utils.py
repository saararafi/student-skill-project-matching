
from functools import wraps

from flask import session, jsonify
from backend.database import fetch_one


# =========================================================
# CURRENT USER HELPERS
# =========================================================

def get_current_user_id():
    """Return the logged-in user's ID, or None."""
    return session.get("user_id")


def get_current_user():
    """Return the logged-in user's database record."""
    user_id = get_current_user_id()

    if user_id is None:
        return None

    user = fetch_one(
        """
        SELECT id, name, email, role
        FROM users
        WHERE id = %s
        """,
        (user_id,)
    )

    if not user:
        session.clear()
        return None

    return user

def get_current_role():
    """Return the logged-in user's role, or None if not logged in."""
    user = get_current_user()
    if not user:
        return None
    return str(user.get("role", "")).strip().lower()

def get_current_student_id():
    """Return the student profile ID for the logged-in student."""
    user = get_current_user()

    if not user or user.get("role") != "student":
        return None

    student = fetch_one(
        "SELECT id FROM students WHERE user_id = %s",
        (user["id"],)
    )

    if not student:
        return None

    return student["id"]


def is_logged_in():
    """Check that the session belongs to an existing user."""
    return get_current_user() is not None


def is_student():
    """Check whether the current user has a student profile."""
    return get_current_student_id() is not None


def is_faculty():
    """Check whether the current user is faculty or an admin."""
    user = get_current_user()

    if not user:
        return False

    role = str(user.get("role", "")).strip().lower()
    return role in ("faculty", "admin")


def is_admin():
    """Check whether the current user is an administrator."""
    user = get_current_user()

    if not user:
        return False

    return str(user.get("role", "")).strip().lower() == "admin"


# =========================================================
# AUTHENTICATION DECORATORS
# =========================================================

def login_required(view_function):
    """Allow access only to authenticated users."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not is_logged_in():
            return jsonify({
                "success": False,
                "message": "Please log in to continue."
            }), 401

        return view_function(*args, **kwargs)

    return wrapped_view


def student_required(view_function):
    """Allow access only to authenticated students."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not is_student():
            return jsonify({
                "success": False,
                "message": "Please log in with a valid student account."
            }), 401

        return view_function(*args, **kwargs)

    return wrapped_view


def faculty_required(view_function):
    """Allow access only to faculty members or administrators."""

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not is_faculty():
            return jsonify({
                "success": False,
                "message": "Faculty access is required."
            }), 403

        return view_function(*args, **kwargs)

    return wrapped_view
