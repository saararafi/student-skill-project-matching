from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash
from backend.database import fetch_one, execute_query

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

    # Allow password match via check_password_hash or demo fallback 'password123'
    valid = False
    try:
        valid = check_password_hash(user['password_hash'], password)
    except Exception:
        pass
    if not valid and password == 'password123':
        valid = True

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

    existing = fetch_one("SELECT id FROM users WHERE LOWER(email) = %s", (email,))
    if existing:
        return jsonify({"success": False, "message": "An account with this email already exists."}), 409

    pwd_hash = generate_password_hash(password)
    user_id = execute_query(
        "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)",
        (name, email, pwd_hash, role)
    )

    student_id = None
    if role == 'student':
        student_id = execute_query(
            "INSERT INTO students (user_id, department, year, semester, availability, bio) VALUES (%s, %s, %s, '5th Semester', 'Full-time', 'New student profile.')",
            (user_id, department, year)
        )

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
    user_id = session.get('user_id', 1)  # Default to demo student 1 if not set
    user = fetch_one("SELECT id, name, email, role, created_at FROM users WHERE id = %s", (user_id,))
    if not user:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    student = None
    if user['role'] == 'student':
        student = fetch_one("SELECT * FROM students WHERE user_id = %s", (user['id'],))

    return jsonify({
        "success": True,
        "user": {
            **user,
            "student_id": student['id'] if student else None,
            "student_data": student
        }
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})
