from flask import Blueprint, request, jsonify
from backend.database import fetch_one, fetch_all, execute_query, db_transaction, adapt_sql
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

    if role == 'admin':
        # Admin can view all applications system-wide
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
    elif role == 'faculty':
        # Faculty sees applications strictly to their own projects
        applications = fetch_all("""
            SELECT a.id, a.project_id, a.student_id, a.status, a.message, a.match_score, a.applied_at,
                   p.title as project_title, p.domain,
                   u.name as student_name, u.email as student_email, s.department, s.year
            FROM applications a
            JOIN projects p ON a.project_id = p.id
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE p.faculty_id = %s
            ORDER BY a.applied_at DESC
        """, (user_id,))
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
    user_id = get_current_user_id()
    role = get_current_role()
    data = request.get_json() or {}
    new_status = data.get('status') # 'Accepted' or 'Rejected'

    if new_status not in ('Accepted', 'Rejected', 'Pending'):
        return jsonify({"success": False, "message": "Invalid status."}), 400

    app = fetch_one("""
        SELECT a.*, p.faculty_id
        FROM applications a
        JOIN projects p ON a.project_id = p.id
        WHERE a.id = %s
    """, (app_id,))
    if not app:
        return jsonify({"success": False, "message": "Application not found."}), 404

    # Enforce authorization: only project owner or administrator can modify application status
    if role != 'admin' and app['faculty_id'] != user_id:
        return jsonify({
            "success": False,
            "message": "You can only review applications for your own projects."
        }), 403

    with db_transaction() as (cur, engine):
        cur.execute(
            adapt_sql("UPDATE applications SET status = %s, reviewed_at = CURRENT_TIMESTAMP WHERE id = %s", engine),
            (new_status, app_id)
        )
        # If accepted, add student to team
        if new_status == 'Accepted':
            cur.execute(
                adapt_sql("SELECT id FROM teams WHERE project_id = %s", engine),
                (app['project_id'],)
            )
            team = cur.fetchone()
            if not team:
                # Create team if none exists
                cur.execute(
                    adapt_sql("INSERT INTO teams (project_id, name, leader_id) VALUES (%s, %s, %s)", engine),
                    (app['project_id'], "Project Team", app['student_id'])
                )
                team_id = cur.lastrowid
                if not team_id and engine == 'postgres':
                    cur.execute("SELECT lastval() AS id")
                    r = cur.fetchone()
                    team_id = r['id'] if r else None
            else:
                team_id = team['id'] if isinstance(team, dict) or hasattr(team, '__getitem__') else team[0]

            # Check if already a member
            cur.execute(
                adapt_sql("SELECT id FROM team_members WHERE team_id = %s AND student_id = %s", engine),
                (team_id, app['student_id'])
            )
            member = cur.fetchone()
            if not member:
                cur.execute(
                    adapt_sql("INSERT INTO team_members (team_id, student_id, role) VALUES (%s, %s, 'Team Member')", engine),
                    (team_id, app['student_id'])
                )

        # Notify student
        cur.execute(
            adapt_sql("SELECT user_id FROM students WHERE id = %s", engine),
            (app['student_id'],)
        )
        stu = cur.fetchone()
        cur.execute(
            adapt_sql("SELECT title FROM projects WHERE id = %s", engine),
            (app['project_id'],)
        )
        proj = cur.fetchone()
        if stu and proj:
            stu_user_id = stu['user_id'] if isinstance(stu, dict) or hasattr(stu, '__getitem__') else stu[0]
            proj_title = proj['title'] if isinstance(proj, dict) or hasattr(proj, '__getitem__') else proj[0]
            msg = f"Your application for {proj_title} has been {new_status.lower()}."
            t = 'success' if new_status == 'Accepted' else 'warning'
            cur.execute(
                adapt_sql("""
                    INSERT INTO notifications (user_id, title, message, type, link)
                    VALUES (%s, %s, %s, %s, 'applications.html')
                """, engine),
                (stu_user_id, f"Application {new_status}", msg, t)
            )

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

    proj = fetch_one("SELECT title FROM projects WHERE id = %s", (app['project_id'],))

    with db_transaction() as (cur, engine):
        cur.execute(
            adapt_sql("DELETE FROM applications WHERE id = %s", engine),
            (app_id,)
        )
        if proj:
            cur.execute(
                adapt_sql("""
                    INSERT INTO notifications (user_id, title, message, type, link)
                    VALUES (%s, %s, %s, 'info', 'applications.html')
                """, engine),
                (
                    get_current_user_id(),
                    'Application Withdrawn',
                    f"Your application for {proj['title']} was withdrawn."
                )
            )

    return jsonify({
        "success": True,
        "message": "Application withdrawn."
    })
