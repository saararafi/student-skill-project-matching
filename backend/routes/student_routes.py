import os
import time
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, send_from_directory
from backend.config import Config
from backend.database import fetch_one, fetch_all, execute_query
from backend.services.matching_service import get_student_profile_data
from backend.auth_utils import (
    is_logged_in,
    get_current_student_id,
    login_required,
    faculty_required,
    is_faculty,
    is_admin,
    authorize_certificate_access,
)

student_bp = Blueprint('student', __name__)


@student_bp.before_request
def require_signed_in_user():
    """
    The student endpoints hold personal data, so they need a signed-in user.

    Returning 401 (rather than 404) lets the browser tell the difference
    between "not signed in" and "no such record", so a page can send the
    visitor to the sign-in screen instead of showing an error.

    Faculty are allowed through as well: verifying a student's certificate
    lives on this blueprint but is a guide's action.
    """
    if not is_logged_in():
        return jsonify({
            "success": False,
            "message": "Please log in to continue."
        }), 401



@student_bp.route('/profile', methods=['GET'])
def get_profile():
    cur_student_id = get_current_student_id()
    requested_id = request.args.get('student_id', type=int)

    # Prevent IDOR: students can only access their own profile; faculty/admin can inspect students
    if requested_id and requested_id != cur_student_id:
        if not (is_faculty() or is_admin()):
            return jsonify({
                "success": False,
                "message": "Unauthorized access to another student's profile."
            }), 403
        student_id = requested_id
    else:
        student_id = cur_student_id

    data = get_student_profile_data(student_id)
    if not data:
        return jsonify({"success": False, "message": "Student profile not found."}), 404

    # Calculate profile completeness purely based on actual completed fields (0% base)
    completeness = 0
    dept = (data['student'].get('department') or '').strip()
    if dept and dept.lower() not in ('', 'general'):
        completeness += 10

    year = (data['student'].get('year') or '').strip()
    sem = (data['student'].get('semester') or '').strip()
    if year and sem:
        completeness += 10

    bio = (data['student'].get('bio') or '').strip()
    if bio and bio.lower() not in ('', 'new student profile.'):
        completeness += 10

    gh = (data['student'].get('github_url') or '').strip()
    li = (data['student'].get('linkedin_url') or '').strip()
    if gh or li:
        completeness += 10

    num_skills = len(data.get('skills_list') or [])
    if num_skills >= 3:
        completeness += 20
    elif num_skills >= 1:
        completeness += 10

    num_interests = len(data.get('interests') or [])
    if num_interests >= 2:
        completeness += 15
    elif num_interests >= 1:
        completeness += 10

    if len(data.get('experiences') or []) >= 1:
        completeness += 10

    certs_uploaded = sum(1 for s in (data.get('skills_list') or []) if s.get('certificate_filename'))
    if certs_uploaded > 0:
        completeness += 15

    completeness = max(0, min(100, completeness))

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
@login_required
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
    cur_student_id = get_current_student_id()
    requested_id = request.args.get('student_id', type=int)

    # Prevent IDOR on student skills
    if requested_id and requested_id != cur_student_id:
        if not (is_faculty() or is_admin()):
            return jsonify({
                "success": False,
                "message": "Unauthorized access to another student's skills."
            }), 403
        student_id = requested_id
    else:
        student_id = cur_student_id

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
@login_required
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
@login_required
def delete_skill(skill_id):
    student_id = get_current_student_id()
    execute_query("DELETE FROM student_skills WHERE student_id = %s AND skill_id = %s", (student_id, skill_id))
    return jsonify({"success": True, "message": "Skill removed from profile."})


@student_bp.route('/upload-certificate', methods=['POST'])
@login_required
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

    # Validate file signatures / magic bytes to prevent disguised or malicious executable uploads
    header = file.read(16)
    file.seek(0)
    is_valid_magic = False
    if ext == 'pdf' and header.startswith(b'%PDF'):
        is_valid_magic = True
    elif ext == 'png' and header.startswith(b'\x89PNG\r\n\x1a\n'):
        is_valid_magic = True
    elif ext in ('jpg', 'jpeg') and header.startswith(b'\xff\xd8\xff'):
        is_valid_magic = True

    if not is_valid_magic:
        return jsonify({
            "success": False,
            "message": f"File content does not match the valid signature for a {ext.upper()} file."
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
@faculty_required
def verify_certificate():
    """Allows Faculty/Admin to approve or reject a student certificate."""
    data = request.get_json() or {}
    student_id = data.get('student_id')
    skill_id = data.get('skill_id')
    status = data.get('status', 'Verified')  # 'Verified' or 'Rejected'

    if not student_id or not skill_id:
        return jsonify({"success": False, "message": "student_id and skill_id are required."}), 400

    if status not in ('Verified', 'Rejected', 'Pending', 'None'):
        return jsonify({"success": False, "message": "Invalid certificate status."}), 400

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


@student_bp.route('/settings', methods=['GET'])
def get_settings():
    """Returns the account details and preferences for the student."""
    student_id = get_current_student_id()
    student = fetch_one("SELECT * FROM students WHERE id = %s", (student_id,))
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    user = fetch_one(
        "SELECT name, email FROM users WHERE id = %s",
        (student['user_id'],)
    )

    settings = {
        "name": user['name'] if user else '',
        "email": user['email'] if user else '',
        "department": student.get('department'),
        "year": student.get('year'),
        "semester": student.get('semester'),
        "availability": student.get('availability'),
        "email_notifications": student.get('email_notifications', 1),
        "match_alerts": student.get('match_alerts', 1),
        "weekly_digest": student.get('weekly_digest', 0),
        "profile_visibility": student.get('profile_visibility', 'team'),
        "prioritise_skills": student.get('prioritise_skills', 1),
        "consider_interests": student.get('consider_interests', 1),
        "consider_experience": student.get('consider_experience', 1),
        "consider_availability": student.get('consider_availability', 1),
        "application_alerts": student.get('application_alerts', 1),
        "team_alerts": student.get('team_alerts', 1),
        "gap_alerts": student.get('gap_alerts', 1),
        "weekly_hours": student.get('weekly_hours', 20),
    }
    return jsonify({"success": True, "settings": settings})


@student_bp.route('/settings', methods=['PUT'])
@login_required
def update_settings():
    """
    Saves the student's settings.

    This covers both the account details shown at the top of the settings
    page and the matching/notification preferences below it, so the whole
    page is persisted with a single request.
    """
    student_id = get_current_student_id()
    data = request.get_json() or {}

    student = fetch_one("SELECT * FROM students WHERE id = %s", (student_id,))
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    def as_bool(value, default):
        if value is None:
            return default
        if isinstance(value, bool):
            return 1 if value else 0
        return 1 if str(value).lower() in ('1', 'true', 'on', 'yes') else 0

    # --- Account details ----------------------------------------------
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    department = (data.get('department') or '').strip()
    year = (data.get('year') or '').strip()
    semester = (data.get('semester') or '').strip()
    availability = (data.get('availability') or '').strip()

    if email:
        # The address must stay unique.
        existing = fetch_one(
            "SELECT id FROM users WHERE LOWER(email) = %s AND id != %s",
            (email, student['user_id'],)
        )
        if existing:
            return jsonify({
                "success": False,
                "message": "That email address is already in use."
            }), 409

    if availability and availability not in ('Full-time', 'Part-time'):
        return jsonify({
            "success": False,
            "message": "Availability must be 'Full-time' or 'Part-time'."
        }), 400

    if name or email:
        execute_query("""
            UPDATE users
            SET name = COALESCE(NULLIF(%s, ''), name),
                email = COALESCE(NULLIF(%s, ''), email)
            WHERE id = %s
        """, (name, email, student['user_id']))

    execute_query("""
        UPDATE students
        SET department = COALESCE(NULLIF(%s, ''), department),
            year = COALESCE(NULLIF(%s, ''), year),
            semester = COALESCE(NULLIF(%s, ''), semester),
            availability = COALESCE(NULLIF(%s, ''), availability)
        WHERE id = %s
    """, (department, year, semester, availability, student_id))

    # --- Preferences ---------------------------------------------------
    email_notifications = as_bool(data.get('email_notifications'), 1)
    match_alerts = as_bool(data.get('match_alerts'), 1)
    weekly_digest = as_bool(data.get('weekly_digest'), 0)
    prioritise_skills = as_bool(data.get('prioritise_skills'), 1)
    consider_interests = as_bool(data.get('consider_interests'), 1)
    consider_experience = as_bool(data.get('consider_experience'), 1)
    consider_availability = as_bool(data.get('consider_availability'), 1)
    application_alerts = as_bool(data.get('application_alerts'), 1)
    team_alerts = as_bool(data.get('team_alerts'), 1)
    gap_alerts = as_bool(data.get('gap_alerts'), 1)

    try:
        weekly_hours = int(data.get('weekly_hours', student.get('weekly_hours', 20)))
    except (TypeError, ValueError):
        weekly_hours = student.get('weekly_hours', 20)
    weekly_hours = max(0, min(40, weekly_hours))

    visibility = data.get('profile_visibility', student.get('profile_visibility', 'team'))
    if visibility not in ('public', 'team', 'private'):
        visibility = 'team'

    execute_query("""
        UPDATE students
        SET email_notifications = %s,
            match_alerts = %s,
            weekly_digest = %s,
            profile_visibility = %s,
            prioritise_skills = %s,
            consider_interests = %s,
            consider_experience = %s,
            consider_availability = %s,
            application_alerts = %s,
            team_alerts = %s,
            gap_alerts = %s,
            weekly_hours = %s
        WHERE id = %s
    """, (
        email_notifications, match_alerts, weekly_digest, visibility,
        prioritise_skills, consider_interests, consider_experience,
        consider_availability, application_alerts, team_alerts, gap_alerts,
        weekly_hours, student_id
    ))

    saved = fetch_one("SELECT * FROM students WHERE id = %s", (student_id,))
    user = fetch_one("SELECT name, email FROM users WHERE id = %s", (student['user_id'],))

    return jsonify({
        "success": True,
        "message": "Settings saved successfully!",
        "settings": {
            "name": user['name'] if user else '',
            "email": user['email'] if user else '',
            "department": saved.get('department'),
            "year": saved.get('year'),
            "semester": saved.get('semester'),
            "availability": saved.get('availability'),
            "email_notifications": email_notifications,
            "match_alerts": match_alerts,
            "weekly_digest": weekly_digest,
            "profile_visibility": visibility,
            "prioritise_skills": prioritise_skills,
            "consider_interests": consider_interests,
            "consider_experience": consider_experience,
            "consider_availability": consider_availability,
            "application_alerts": application_alerts,
            "team_alerts": team_alerts,
            "gap_alerts": gap_alerts,
            "weekly_hours": weekly_hours,
        }
    })


@student_bp.route('/reset-settings', methods=['POST'])
@login_required
def reset_settings():
    """Resets student matching and notification preferences to defaults."""
    student_id = get_current_student_id()
    execute_query("""
        UPDATE students
        SET prioritise_skills = 1,
            consider_interests = 1,
            consider_experience = 1,
            consider_availability = 1,
            weekly_hours = 20,
            match_alerts = 1,
            application_alerts = 1,
            team_alerts = 1,
            gap_alerts = 1,
            email_notifications = 1,
            weekly_digest = 0
        WHERE id = %s
    """, (student_id,))
    return jsonify({"success": True, "message": "Preferences reset to default values."})


@student_bp.route('/experiences', methods=['GET'])
def list_experiences():
    """Returns the student's previous work entries."""
    student_id = get_current_student_id()
    rows = fetch_all(
        "SELECT id, experience_title FROM student_experiences WHERE student_id = %s ORDER BY id",
        (student_id,)
    )
    return jsonify({
        "success": True,
        "experiences": [{'id': r['id'], 'title': r['experience_title']} for r in rows]
    })


@student_bp.route('/experiences', methods=['POST'])
@login_required
def add_experience():
    """Adds a previous work entry to the student's profile."""
    student_id = get_current_student_id()
    data = request.get_json() or {}

    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({"success": False, "message": "A title is required."}), 400
    if len(title) > 150:
        return jsonify({"success": False, "message": "Title must be 150 characters or fewer."}), 400

    # Avoid storing the same entry twice.
    existing = fetch_one(
        "SELECT id FROM student_experiences WHERE student_id = %s AND LOWER(experience_title) = LOWER(%s)",
        (student_id, title)
    )
    if existing:
        return jsonify({
            "success": False,
            "message": "That experience is already on your profile."
        }), 400

    new_id = execute_query(
        "INSERT INTO student_experiences (student_id, experience_title) VALUES (%s, %s)",
        (student_id, title)
    )

    return jsonify({
        "success": True,
        "message": "Experience added!",
        "experience": {"id": new_id, "title": title}
    }), 201


@student_bp.route('/experiences/<int:experience_id>', methods=['DELETE'])
@login_required
def delete_experience(experience_id):
    """Removes a previous work entry."""
    student_id = get_current_student_id()
    execute_query(
        "DELETE FROM student_experiences WHERE id = %s AND student_id = %s",
        (experience_id, student_id)
    )
    return jsonify({"success": True, "message": "Experience removed."})


@student_bp.route('/interests', methods=['GET'])
def list_interests():
    """Returns the student's selected interest areas."""
    student_id = get_current_student_id()
    rows = fetch_all(
        "SELECT interest FROM student_interests WHERE student_id = %s ORDER BY interest",
        (student_id,)
    )
    return jsonify({
        "success": True,
        "interests": [r['interest'] for r in rows]
    })


@student_bp.route('/interests', methods=['PUT'])
@login_required
def update_interests():
    """
    Replaces the student's interest areas.

    Interests feed directly into the interest compatibility factor of the
    matching algorithm, so this genuinely changes the computed scores.
    """
    student_id = get_current_student_id()
    data = request.get_json() or {}

    raw = data.get('interests', [])
    if not isinstance(raw, list):
        return jsonify({"success": False, "message": "interests must be a list."}), 400

    # Normalise, trim and drop duplicates while preserving order.
    interests = []
    for item in raw:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if value and value.lower() not in [i.lower() for i in interests]:
            interests.append(value[:100])

    if len(interests) > 20:
        return jsonify({"success": False, "message": "You can select at most 20 interests."}), 400

    execute_query("DELETE FROM student_interests WHERE student_id = %s", (student_id,))
    for interest in interests:
        execute_query(
            "INSERT INTO student_interests (student_id, interest) VALUES (%s, %s)",
            (student_id, interest)
        )

    return jsonify({
        "success": True,
        "message": "Interests updated successfully!",
        "interests": interests
    })


@student_bp.route('/interests', methods=['POST'])
@login_required
def add_interest():
    """Adds a single interest or a batch of interests to the student profile."""
    student_id = get_current_student_id()
    data = request.get_json() or {}
    interest = (data.get('interest') or '').strip()

    if not interest:
        raw_list = data.get('interests', [])
        if isinstance(raw_list, list) and raw_list:
            added = []
            for item in raw_list:
                if isinstance(item, str) and item.strip():
                    val = item.strip()[:100]
                    existing = fetch_one(
                        "SELECT id FROM student_interests WHERE student_id = %s AND LOWER(interest) = LOWER(%s)",
                        (student_id, val)
                    )
                    if not existing:
                        execute_query(
                            "INSERT INTO student_interests (student_id, interest) VALUES (%s, %s)",
                            (student_id, val)
                        )
                        added.append(val)
            return jsonify({"success": True, "message": f"{len(added)} interest(s) added successfully!"}), 201
        return jsonify({"success": False, "message": "Interest is required."}), 400

    existing = fetch_one(
        "SELECT id FROM student_interests WHERE student_id = %s AND LOWER(interest) = LOWER(%s)",
        (student_id, interest)
    )
    if existing:
        return jsonify({"success": True, "message": "Interest already added."}), 200

    execute_query(
        "INSERT INTO student_interests (student_id, interest) VALUES (%s, %s)",
        (student_id, interest[:100])
    )
    return jsonify({"success": True, "message": f"Interest '{interest}' added successfully!"}), 201


@student_bp.route('/interests/<string:interest_name>', methods=['DELETE'])
@login_required
def delete_interest(interest_name):
    """Removes a specific interest from the student profile."""
    student_id = get_current_student_id()
    execute_query(
        "DELETE FROM student_interests WHERE student_id = %s AND LOWER(interest) = LOWER(%s)",
        (student_id, interest_name.strip())
    )
    return jsonify({"success": True, "message": f"Interest '{interest_name}' removed."})


@student_bp.route('/certificates/<filename>', methods=['GET'])
def view_certificate(filename):
    """Serves the uploaded certificate for browser preview/download with authorization enforcement."""
    is_authorized, result = authorize_certificate_access(filename)
    if not is_authorized:
        response_tuple = result
        return response_tuple
    clean_filename = result
    return send_from_directory(Config.UPLOAD_FOLDER, clean_filename)
