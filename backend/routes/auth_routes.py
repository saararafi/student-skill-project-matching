import re
from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from backend.database import fetch_one, execute_query, db_transaction, adapt_sql
from backend.auth_utils import get_current_user_id, login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    user = fetch_one("SELECT * FROM users WHERE LOWER(email) = %s", (email,))
    if not user:
        return jsonify({"success": False, "message": "No account found with this email."}), 404

    # Verify the password against the stored hash.
    try:
        valid = check_password_hash(user['password_hash'], password)
    except Exception:
        valid = False

    if not valid:
        return jsonify({"success": False, "message": "Invalid password."}), 401

    session['user_id'] = user['id']
    session['role'] = user['role']

    # Fetch student record if student
    student = None
    if user['role'] == 'student':
        student = fetch_one("SELECT * FROM students WHERE user_id = %s", (user['id'],))

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['name']}!",
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "role": user['role'],
            "student_id": student['id'] if student else None
        }
    })


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    role = data.get('role', 'student').strip().lower()
    department = data.get('department', 'Computer Science Engineering').strip()
    year = data.get('year', '3rd Year').strip()

    if not name or not email or not password:
        return jsonify({"success": False, "message": "Name, email and password are required."}), 400

    if len(password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters long."}), 400

    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({"success": False, "message": "Please provide a valid email address."}), 400

    if role not in ('student', 'faculty'):
        role = 'student'

    existing = fetch_one("SELECT id FROM users WHERE LOWER(email) = %s", (email,))
    if existing:
        return jsonify({"success": False, "message": "An account with this email already exists."}), 409

    pwd_hash = generate_password_hash(password)
    with db_transaction() as (cur, engine):
        cur.execute(
            adapt_sql("INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)", engine),
            (name, email, pwd_hash, role)
        )
        user_id = cur.lastrowid
        if not user_id and engine == 'postgres':
            cur.execute("SELECT lastval() AS id")
            row = cur.fetchone()
            user_id = row['id'] if row else None

        student_id = None
        if role == 'student':
            sem = (data.get('semester') or '').strip()
            avail = (data.get('availability') or 'Part-time').strip() or 'Part-time'
            cur.execute(
                adapt_sql(
                    "INSERT INTO students (user_id, department, year, semester, availability, bio, weekly_hours) "
                    "VALUES (%s, %s, %s, %s, %s, '', 0)",
                    engine
                ),
                (user_id, department, year, sem, avail)
            )
            student_id = cur.lastrowid
            if not student_id and engine == 'postgres':
                cur.execute("SELECT lastval() AS id")
                row = cur.fetchone()
                student_id = row['id'] if row else None

    session['user_id'] = user_id
    session['role'] = role

    return jsonify({
        "success": True,
        "message": "Registration successful!",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "role": role,
            "student_id": student_id
        }
    }), 201

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')

    # Require a genuine login
    if not user_id:
        return jsonify({
            "success": False,
            "message": "Please log in first."
        }), 401

    user = fetch_one(
        "SELECT id, name, email, role, created_at FROM users WHERE id = %s",
        (user_id,)
    )

    if not user:
        session.clear()
        return jsonify({
            "success": False,
            "message": "Account not found. Please log in again."
        }), 401

    student = None

    if user['role'] == 'student':
        student = fetch_one(
            "SELECT * FROM students WHERE user_id = %s",
            (user['id'],)
        )

    return jsonify({
        "success": True,
        "user": {
            **user,
            "student_id": student['id'] if student else None,
            "student_data": student
        }
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    resp = jsonify({"success": True, "message": "Logged out successfully."})
    resp.delete_cookie('csrf_token')
    return resp


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    user_id = get_current_user_id()
    data = request.get_json() or {}
    current_pwd = data.get('current_password', '')
    new_pwd = data.get('new_password', '')
    confirm_pwd = data.get('confirm_password', '')

    if not current_pwd or not new_pwd:
        return jsonify({"success": False, "message": "Current and new password are required."}), 400

    if len(new_pwd) < 8:
        return jsonify({"success": False, "message": "New password must be at least 8 characters long."}), 400

    if confirm_pwd and new_pwd != confirm_pwd:
        return jsonify({"success": False, "message": "New passwords do not match."}), 400

    user = fetch_one("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    if not user or not check_password_hash(user['password_hash'], current_pwd):
        return jsonify({"success": False, "message": "Incorrect current password."}), 400

    new_hash = generate_password_hash(new_pwd)
    execute_query("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
    return jsonify({"success": True, "message": "Password changed successfully."})
