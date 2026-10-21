from flask import Blueprint, request, jsonify
from backend.database import fetch_one, fetch_all, execute_query
from backend.services.matching_service import compute_match, get_ranked_project_recommendations
from backend.auth_utils import (
    get_current_student_id,
    get_current_user_id,
    login_required,
    faculty_required,
)

project_bp = Blueprint('project', __name__)


@project_bp.route('', methods=['GET'])
def list_projects():
    student_id = get_current_student_id()
    domain_filter = request.args.get('domain', '').strip()
    search = request.args.get('search', '').strip().lower()

    # Get ranked project recommendations for this student
    projects = get_ranked_project_recommendations(student_id)

    # Apply optional domain filter
    if domain_filter and domain_filter.lower() != 'all':
        projects = [p for p in projects if domain_filter.lower() in p['domain'].lower()]

    # Apply search filter
    if search:
        projects = [
            p for p in projects
            if search in p['title'].lower() 
            or search in p['description'].lower() 
            or search in p['domain'].lower()
        ]

    # Check user application status for each project
    for p in projects:
        app = fetch_one(
            "SELECT id, status FROM applications WHERE project_id = %s AND student_id = %s",
            (p['id'], student_id)
        )
        p['user_application'] = app

    return jsonify({"success": True, "projects": projects})


@project_bp.route('/<int:project_id>', methods=['GET'])
def get_project_details(project_id):
    student_id = get_current_student_id()
    
    project = fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404

    faculty = fetch_one("SELECT name, email FROM users WHERE id = %s", (project['faculty_id'],))
    
    # Required Skills
    skills = fetch_all("""
        SELECT s.id as skill_id, s.name, s.category, ps.required_level
        FROM project_skills ps
        JOIN skills s ON ps.skill_id = s.id
        WHERE ps.project_id = %s
    """, (project_id,))

    # Interests
    interests = fetch_all("SELECT interest FROM project_interests WHERE project_id = %s", (project_id,))
    
    # Experiences
    experiences = fetch_all("SELECT experience_title FROM project_experiences WHERE project_id = %s", (project_id,))

    # Team members
    team = fetch_one("SELECT * FROM teams WHERE project_id = %s", (project_id,))
    team_members = []
    if team:
        team_members = fetch_all("""
            SELECT tm.role, u.name, u.email, s.department, s.id as student_id
            FROM team_members tm
            JOIN students s ON tm.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE tm.team_id = %s
        """, (team['id'],))

        # Attach each member's strongest skills.
        for member in team_members:
            member_skills = fetch_all("""
                SELECT sk.name, ss.proficiency_level
                FROM student_skills ss
                JOIN skills sk ON ss.skill_id = sk.id
                WHERE ss.student_id = %s
                ORDER BY ss.proficiency_level DESC
                LIMIT 3
            """, (member['student_id'],))
            member['skills'] = member_skills

    # Match breakdown for this student
    match_data = compute_match(student_id, project_id)

    # Check application status
    app = fetch_one(
        "SELECT id, status, message, applied_at FROM applications WHERE project_id = %s AND student_id = %s",
        (project_id, student_id)
    )

    # Total number of applications received for this project
    app_count = fetch_one(
        "SELECT COUNT(*) AS total FROM applications WHERE project_id = %s",
        (project_id,)
    )

    return jsonify({
        "success": True,
        "project": {
            **project,
            "faculty": faculty,
            "required_skills": skills,
            "interests": [i['interest'] for i in interests],
            "experiences": [e['experience_title'] for e in experiences],
            "team": team,
            "team_members": team_members,
            "match": match_data,
            "application": app,
            "application_count": app_count['total'] if app_count else 0
        }
    })


@project_bp.route('/<int:project_id>/apply', methods=['POST'])
@login_required
def apply_to_project(project_id):
    student_id = get_current_student_id()
    data = request.get_json() or {}
    message = data.get('message', 'Excited to contribute to this project!')

    project = fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404

    existing = fetch_one(
        "SELECT id, status FROM applications WHERE project_id = %s AND student_id = %s",
        (project_id, student_id)
    )
    if existing:
        return jsonify({
            "success": False, 
            "message": f"You have already applied for this project. Current status: {existing['status']}"
        }), 400

    match_res = compute_match(student_id, project_id)
    score = match_res['final_score'] if match_res else 0.0

    app_id = execute_query("""
        INSERT INTO applications (project_id, student_id, status, message, match_score)
        VALUES (%s, %s, 'Pending', %s, %s)
    """, (project_id, student_id, message, score))

    # Notify student
    stu = fetch_one("SELECT user_id FROM students WHERE id = %s", (student_id,))
    if stu:
        execute_query("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, 'info', 'applications.html')
        """, (stu['user_id'], 'Application Submitted', f'Your application for {project["title"]} has been submitted for review.'))

    return jsonify({
        "success": True, 
        "message": "Application submitted successfully! Your compatibility score is " + str(score) + "%.",
        "application_id": app_id,
        "match_score": score
    })


@project_bp.route('', methods=['POST'])
@faculty_required
def create_project():
    """Allows Faculty/Admin to create a new project listing."""
    data = request.get_json() or {}
    user_id = get_current_user_id()

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    domain = data.get('domain', 'General').strip() or 'General'
    availability = data.get('required_availability', 'Part-time')
    skills = data.get('skills', [])  # List of {name, required_level}

    if not title or not description:
        return jsonify({"success": False, "message": "Title and description are required."}), 400

    if availability not in ('Full-time', 'Part-time'):
        return jsonify({
            "success": False,
            "message": "Availability must be 'Full-time' or 'Part-time'."
        }), 400

    try:
        team_size = int(data.get('team_size', 4) or 4)
    except (TypeError, ValueError):
        team_size = 4
    if not 1 <= team_size <= 20:
        return jsonify({"success": False, "message": "Team size must be between 1 and 20."}), 400

    proj_id = execute_query("""
        INSERT INTO projects (faculty_id, title, description, domain, required_availability, team_size, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'Open')
    """, (user_id, title, description, domain, availability, team_size))

    # Add required skills
    for sk in skills:
        sk_name = (sk.get('name') or '').strip()
        if not sk_name:
            continue
        try:
            lvl = int(sk.get('required_level', 3))
        except (TypeError, ValueError):
            lvl = 3
        lvl = max(1, min(5, lvl))

        # Check or create master skill
        master = fetch_one("SELECT id FROM skills WHERE LOWER(name) = %s", (sk_name.lower(),))
        if not master:
            m_id = execute_query("INSERT INTO skills (name, category) VALUES (%s, %s)", (sk_name, domain))
        else:
            m_id = master['id']
        execute_query("""
            INSERT INTO project_skills (project_id, skill_id, required_level)
            VALUES (%s, %s, %s)
        """, (proj_id, m_id, lvl))

    return jsonify({"success": True, "message": "Project created successfully!", "project_id": proj_id}), 201
