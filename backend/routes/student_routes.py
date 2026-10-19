import os
import time
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, session, send_from_directory
from backend.config import Config
from backend.database import fetch_one, fetch_all, execute_query
from backend.services.matching_service import get_student_profile_data

student_bp = Blueprint('student', __name__)

def get_current_student_id():
    """Helper to get logged-in student id, defaulting to demo student 1 if not set."""
    user_id = session.get('user_id', 1)
    student = fetch_one("SELECT id FROM students WHERE user_id = %s", (user_id,))
    return student['id'] if student else 1


@student_bp.route('/profile', methods=['GET'])
def get_profile():
    student_id = request.args.get('student_id', type=int) or get_current_student_id()
    data = get_student_profile_data(student_id)
    if not data:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    # Calculate profile completeness
    completeness = 40  # base
    if data['student'].get('bio'): completeness += 10
    if len(data['skills_list']) >= 4: completeness += 20
    elif len(data['skills_list']) >= 2: completeness += 10
    if len(data['interests']) >= 2: completeness += 10
    if len(data['experiences']) >= 2: completeness += 10
    # Any certificates uploaded
    certs_uploaded = sum(1 for s in data['skills_list'] if s.get('certificate_filename'))
    if certs_uploaded > 0: completeness += 10
    completeness = min(completeness, 100)

    return jsonify({
        "success": True,
        "profile": {
            "student_id": data['student']['id'],
            "name": data['user']['name'],
            "email": data['user']['email'],
            "department": data['student']['department'],
            "year": data['student']['year'],
            "semester": data['student']['semester'],
            "availability": data['student']['availability'],
            "bio": data['student']['bio'],
            "github_url": data['student']['github_url'],
            "linkedin_url": data['student']['linkedin_url'],
            "completeness": completeness,
            "skills": data['skills_list'],
            "interests": data['interests'],
            "experiences": data['experiences']
        }
    })


@student_bp.route('/profile', methods=['PUT'])
def update_profile():
    student_id = get_current_student_id()
    data = request.get_json() or {}

    name = data.get('name')
    department = data.get('department')
    year = data.get('year')
    semester = data.get('semester')
    availability = data.get('availability')
    bio = data.get('bio')
    github_url = data.get('github_url')
    linkedin_url = data.get('linkedin_url')

    student = fetch_one("SELECT * FROM students WHERE id = %s", (student_id,))
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    # Update User name if provided
    if name:
        execute_query("UPDATE users SET name = %s WHERE id = %s", (name, student['user_id']))

    # Update Student fields
    execute_query("""
        UPDATE students 
        SET department = COALESCE(%s, department),
            year = COALESCE(%s, year),
            semester = COALESCE(%s, semester),
            availability = COALESCE(%s, availability),
            bio = COALESCE(%s, bio),
            github_url = COALESCE(%s, github_url),
            linkedin_url = COALESCE(%s, linkedin_url)
        WHERE id = %s
    """, (department, year, semester, availability, bio, github_url, linkedin_url, student_id))

    return jsonify({"success": True, "message": "Profile updated successfully!"})


@student_bp.route('/skills', methods=['GET'])
def list_skills():
    student_id = request.args.get('student_id', type=int) or get_current_student_id()
    skills = fetch_all("""
        SELECT s.id as skill_id, s.name, s.category, ss.proficiency_level,
               ss.certificate_filename, ss.certificate_original_name,
               ss.certificate_status, ss.uploaded_at
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.id
        WHERE ss.student_id = %s
        ORDER BY ss.proficiency_level DESC
    """, (student_id,))
    
    # Also fetch all master skills available in the system
    all_master_skills = fetch_all("SELECT * FROM skills ORDER BY name ASC")
    
    return jsonify({
        "success": True,
        "student_skills": skills,
        "master_skills": all_master_skills
    })


@student_bp.route('/skills', methods=['POST'])
def add_or_update_skill():
    student_id = get_current_student_id()
    data = request.get_json() or {}
    
    skill_name = data.get('skill_name', '').strip()
    proficiency = data.get('proficiency_level', 3)
    try:
        proficiency = int(proficiency)
        proficiency = max(1, min(5, proficiency))
    except ValueError:
        proficiency = 3

    if not skill_name:
        return jsonify({"success": False, "message": "Skill name is required."}), 400

    # Find or create skill in master table
    master_skill = fetch_one("SELECT id FROM skills WHERE LOWER(name) = %s", (skill_name.lower(),))
    if not master_skill:
        skill_id = execute_query("INSERT INTO skills (name, category) VALUES (%s, 'General')", (skill_name,))
    else:
        skill_id = master_skill['id']

    # Insert or update student_skill
    existing = fetch_one("SELECT id FROM student_skills WHERE student_id = %s AND skill_id = %s", (student_id, skill_id))
    if existing:
        execute_query("UPDATE student_skills SET proficiency_level = %s WHERE id = %s", (proficiency, existing['id']))
    else:
        execute_query("INSERT INTO student_skills (student_id, skill_id, proficiency_level, certificate_status) VALUES (%s, %s, %s, 'None')", (student_id, skill_id, proficiency))

    return jsonify({"success": True, "message": f"Skill '{skill_name}' updated successfully."})


@student_bp.route('/skills/<int:skill_id>', methods=['DELETE'])
def delete_skill(skill_id):
    student_id = get_current_student_id()
    execute_query("DELETE FROM student_skills WHERE student_id = %s AND skill_id = %s", (student_id, skill_id))
    return jsonify({"success": True, "message": "Skill removed from profile."})


@student_bp.route('/upload-certificate', methods=['POST'])
def upload_certificate():
    """
    Handles certificate file uploads to verify student skills.
    Allowed formats: PDF, PNG, JPG, JPEG.
    """
    student_id = get_current_student_id()
    skill_id = request.form.get('skill_id', type=int)
    
    if not skill_id:
        # Check if skill_name was provided instead
        skill_name = request.form.get('skill_name', '').strip()
        if skill_name:
            sk = fetch_one("SELECT id FROM skills WHERE LOWER(name) = %s", (skill_name.lower(),))
            if sk:
                skill_id = sk['id']

    if not skill_id:
        return jsonify({"success": False, "message": "Skill ID or name is required."}), 400

    if 'certificate' not in request.files:
        return jsonify({"success": False, "message": "No certificate file provided."}), 400

    file = request.files['certificate']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400

    # Validate file extension
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in Config.ALLOWED_EXTENSIONS:
        return jsonify({
            "success": False, 
            "message": f"Invalid file format '.{ext}'. Allowed types are PDF, PNG, JPG, JPEG."
        }), 400

    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Generate unique stored filename
    original_filename = secure_filename(file.filename)
    timestamp = int(time.time())
    stored_filename = f"cert_stu{student_id}_sk{skill_id}_{timestamp}.{ext}"
    dest_path = os.path.join(Config.UPLOAD_FOLDER, stored_filename)

    file.save(dest_path)

    # Check if student already has this skill in student_skills; if not, add it
    existing = fetch_one("SELECT id FROM student_skills WHERE student_id = %s AND skill_id = %s", (student_id, skill_id))
    if existing:
        execute_query("""
            UPDATE student_skills 
            SET certificate_filename = %s,
                certificate_original_name = %s,
                certificate_status = 'Pending',
                uploaded_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (stored_filename, original_filename, existing['id']))
    else:
        execute_query("""
            INSERT INTO student_skills 
            (student_id, skill_id, proficiency_level, certificate_filename, certificate_original_name, certificate_status, uploaded_at)
            VALUES (%s, %s, 4, %s, %s, 'Pending', CURRENT_TIMESTAMP)
        """, (student_id, skill_id, stored_filename, original_filename))

    # Add notification for student
    user = fetch_one("SELECT user_id FROM students WHERE id = %s", (student_id,))
    if user:
        skill_row = fetch_one("SELECT name FROM skills WHERE id = %s", (skill_id,))
        s_name = skill_row['name'] if skill_row else 'Skill'
        execute_query("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, 'info', 'profile.html')
        """, (user['user_id'], 'Certificate Uploaded', f'Your certificate for {s_name} was received and queued for verification.'))

    return jsonify({
        "success": True,
        "message": "Certificate uploaded successfully! Verification is pending.",
        "certificate_filename": stored_filename,
        "certificate_original_name": original_filename,
        "certificate_status": "Pending",
        "preview_url": f"/api/certificates/{stored_filename}"
    })


@student_bp.route('/verify-certificate', methods=['POST'])
def verify_certificate():
    """Allows Faculty/Admin to approve or reject a student certificate."""
    data = request.get_json() or {}
    student_id = data.get('student_id')
    skill_id = data.get('skill_id')
    status = data.get('status', 'Verified')  # 'Verified' or 'Rejected'

    if not student_id or not skill_id:
        return jsonify({"success": False, "message": "student_id and skill_id are required."}), 400

    execute_query("""
        UPDATE student_skills
        SET certificate_status = %s
        WHERE student_id = %s AND skill_id = %s
    """, (status, student_id, skill_id))

    # Notify student
    stu = fetch_one("SELECT user_id FROM students WHERE id = %s", (student_id,))
    sk = fetch_one("SELECT name FROM skills WHERE id = %s", (skill_id,))
    if stu and sk:
        execute_query("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, %s, 'profile.html')
        """, (
            stu['user_id'], 
            f'Certificate {status}', 
            f'Your certificate for {sk["name"]} has been {status.lower()} by faculty.',
            'success' if status == 'Verified' else 'warning'
        ))

    return jsonify({"success": True, "message": f"Certificate has been {status}."})


@student_bp.route('/certificates/<filename>', methods=['GET'])
def view_certificate(filename):
    """Serves the uploaded certificate for browser preview/download."""
    safe_name = secure_filename(filename)
    return send_from_directory(Config.UPLOAD_FOLDER, safe_name)
