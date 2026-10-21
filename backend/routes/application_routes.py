from flask import Blueprint, request, jsonify
from backend.database import fetch_one, fetch_all, execute_query
from backend.auth_utils import (
    get_current_student_id,
    get_current_user_id,
    get_current_role,
    login_required,
    faculty_required,
)

application_bp = Blueprint('application', __name__)


@application_bp.route('', methods=['GET'])
@login_required
def list_applications():
    user_id = get_current_user_id()
    role = get_current_role()

    if role in ('faculty', 'admin'):
        # Faculty sees applications to their projects
        applications = fetch_all("""
            SELECT a.id, a.project_id, a.student_id, a.status, a.message, a.match_score, a.applied_at,
                   p.title as project_title, p.domain,
                   u.name as student_name, u.email as student_email, s.department, s.year
            FROM applications a
            JOIN projects p ON a.project_id = p.id
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            ORDER BY a.applied_at DESC
        """)
    else:
        # Student sees their own applications
        student_id = get_current_student_id()
        applications = fetch_all("""
            SELECT a.id, a.project_id, a.student_id, a.status, a.message, a.match_score, a.applied_at,
                   p.title as project_title, p.domain, p.team_size
            FROM applications a
            JOIN projects p ON a.project_id = p.id
            WHERE a.student_id = %s
            ORDER BY a.applied_at DESC
        """, (student_id,))

    return jsonify({"success": True, "applications": applications})


@application_bp.route('/<int:app_id>/status', methods=['PUT'])
@faculty_required
def update_status(app_id):
    data = request.get_json() or {}
    new_status = data.get('status') # 'Accepted' or 'Rejected'

    if new_status not in ('Accepted', 'Rejected', 'Pending'):
        return jsonify({"success": False, "message": "Invalid status."}), 400

    app = fetch_one("SELECT * FROM applications WHERE id = %s", (app_id,))
    if not app:
        return jsonify({"success": False, "message": "Application not found."}), 404

    execute_query(
        "UPDATE applications SET status = %s, reviewed_at = CURRENT_TIMESTAMP WHERE id = %s",
        (new_status, app_id)
    )
    # If accepted, add student to team
    if new_status == 'Accepted':
        team = fetch_one("SELECT id FROM teams WHERE project_id = %s", (app['project_id'],))
        if not team:
            # Create team if none exists
            team_id = execute_query(
                "INSERT INTO teams (project_id, name, leader_id) VALUES (%s, %s, %s)",
                (app['project_id'], "Project Team", app['student_id'])
            )
        else:
            team_id = team['id']

        # Check if already a member
        member = fetch_one(
            "SELECT id FROM team_members WHERE team_id = %s AND student_id = %s",
            (team_id, app['student_id'])
        )
        if not member:
            execute_query(
                "INSERT INTO team_members (team_id, student_id, role) VALUES (%s, %s, 'Team Member')",
                (team_id, app['student_id'])
            )

    # Notify student
    stu = fetch_one("SELECT user_id FROM students WHERE id = %s", (app['student_id'],))
    proj = fetch_one("SELECT title FROM projects WHERE id = %s", (app['project_id'],))
    if stu and proj:
        msg = f"Your application for {proj['title']} has been {new_status.lower()}."
        t = 'success' if new_status == 'Accepted' else 'warning'
        execute_query("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, %s, 'applications.html')
        """, (stu['user_id'], f"Application {new_status}", msg, t))

    return jsonify({"success": True, "message": f"Application marked as {new_status}."})


@application_bp.route('/<int:app_id>/withdraw', methods=['POST'])
@login_required
def withdraw_application(app_id):
    """Lets a student withdraw their own application."""
    student_id = get_current_student_id()

    app = fetch_one(
        "SELECT * FROM applications WHERE id = %s",
        (app_id,)
    )
    if not app:
        return jsonify({"success": False, "message": "Application not found."}), 404

    if app['student_id'] != student_id:
        return jsonify({
            "success": False,
            "message": "You can only withdraw your own applications."
        }), 403

    if app['status'] == 'Accepted':
        return jsonify({
            "success": False,
            "message": "This application was already accepted. Contact the project guide."
        }), 400

    execute_query(
        "DELETE FROM applications WHERE id = %s",
        (app_id,)
    )

    proj = fetch_one("SELECT title FROM projects WHERE id = %s", (app['project_id'],))
    if proj:
        execute_query("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, 'info', 'applications.html')
        """, (
            get_current_user_id(),
            'Application Withdrawn',
            f"Your application for {proj['title']} was withdrawn."
        ))

    return jsonify({
        "success": True,
        "message": "Application withdrawn."
    })
