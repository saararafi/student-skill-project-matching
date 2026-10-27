"""
Faculty API routes.

Handles faculty dashboard data, application reviews,
and student certificate verification.
"""

from flask import Blueprint, jsonify, request

from backend.database import fetch_one, fetch_all, execute_query
from backend.auth_utils import get_current_user_id, get_current_user, faculty_required
from backend.services.faculty_service import get_faculty_overview


faculty_bp = Blueprint("faculty", __name__)


# --------------------------------------------------
# FACULTY DASHBOARD
# --------------------------------------------------

@faculty_bp.route("/overview", methods=["GET"])
@faculty_required
def faculty_overview():
    """Return dashboard statistics and pending certificates."""

    user_id = get_current_user_id()
    overview = get_faculty_overview(user_id)

    if not overview:
        return jsonify({
            "success": False,
            "message": "Faculty account not found."
        }), 404

    return jsonify({
        "success": True,
        **overview
    })


# --------------------------------------------------
# FACULTY APPLICATIONS
# --------------------------------------------------

@faculty_bp.route("/applications", methods=["GET"])
@faculty_required
def faculty_applications():
    """Return applications for projects owned by this faculty member (or all if admin)."""

    user_id = get_current_user_id()
    user = get_current_user()
    is_admin = user and str(user.get("role", "")).lower() == "admin"

    if is_admin:
        applications = fetch_all("""
            SELECT
                a.id,
                a.project_id,
                a.student_id,
                a.status,
                a.message,
                a.match_score,
                a.applied_at,
                p.title AS project_title,
                p.domain,
                u.name AS student_name,
                u.email AS student_email,
                s.department,
                s.year
            FROM applications a
            JOIN projects p ON a.project_id = p.id
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            ORDER BY
                CASE WHEN a.status = 'Pending' THEN 0 ELSE 1 END,
                a.applied_at DESC
        """)
    else:
        applications = fetch_all("""
            SELECT
                a.id,
                a.project_id,
                a.student_id,
                a.status,
                a.message,
                a.match_score,
                a.applied_at,
                p.title AS project_title,
                p.domain,
                u.name AS student_name,
                u.email AS student_email,
                s.department,
                s.year
            FROM applications a
            JOIN projects p ON a.project_id = p.id
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE p.faculty_id = %s
            ORDER BY
                CASE WHEN a.status = 'Pending' THEN 0 ELSE 1 END,
                a.applied_at DESC
        """, (user_id,))

    return jsonify({
        "success": True,
        "applications": applications
    })


@faculty_bp.route("/applications/<int:app_id>/status", methods=["PUT"])
@faculty_required
def update_application_status(app_id):
    """Allow faculty to review applications for their own projects (or any project if admin)."""

    user_id = get_current_user_id()
    user = get_current_user()
    is_admin = user and str(user.get("role", "")).lower() == "admin"

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in ("Accepted", "Rejected", "Pending"):
        return jsonify({
            "success": False,
            "message": "Invalid application status."
        }), 400

    if is_admin:
        application = fetch_one("""
            SELECT
                a.id,
                a.project_id,
                a.student_id,
                a.status,
                p.title AS project_title
            FROM applications a
            JOIN projects p ON a.project_id = p.id
            WHERE a.id = %s
        """, (app_id,))
    else:
        application = fetch_one("""
            SELECT
                a.id,
                a.project_id,
                a.student_id,
                a.status,
                p.title AS project_title
            FROM applications a
            JOIN projects p ON a.project_id = p.id
            WHERE a.id = %s
              AND p.faculty_id = %s
        """, (app_id, user_id))

    if not application:
        return jsonify({
            "success": False,
            "message": "Application not found or you do not own this project."
        }), 404

    execute_query("""
        UPDATE applications
        SET status = %s,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (new_status, app_id))

    # Add accepted students to the project team.
    if new_status == "Accepted":
        team = fetch_one(
            "SELECT id FROM teams WHERE project_id = %s",
            (application["project_id"],)
        )

        if team:
            team_id = team["id"]
        else:
            team_id = execute_query("""
                INSERT INTO teams (project_id, name, leader_id)
                VALUES (%s, %s, %s)
            """, (
                application["project_id"],
                "Project Team",
                application["student_id"]
            ))

            # Some database helpers may return None after an INSERT.
            # Retrieve the team ID again if necessary.
            if not team_id:
                team = fetch_one(
                    "SELECT id FROM teams WHERE project_id = %s",
                    (application["project_id"],)
                )
                team_id = team["id"] if team else None

        if team_id:
            member = fetch_one("""
                SELECT id
                FROM team_members
                WHERE team_id = %s AND student_id = %s
            """, (team_id, application["student_id"]))

            if not member:
                execute_query("""
                    INSERT INTO team_members (team_id, student_id, role)
                    VALUES (%s, %s, %s)
                """, (
                    team_id,
                    application["student_id"],
                    "Team Member"
                ))

    # Notify the student about the decision.
    student = fetch_one(
        "SELECT user_id FROM students WHERE id = %s",
        (application["student_id"],)
    )

    if student:
        notification_type = (
            "success" if new_status == "Accepted"
            else "warning" if new_status == "Rejected"
            else "info"
        )

        execute_query("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            student["user_id"],
            f"Application {new_status}",
            f"Your application for {application['project_title']} "
            f"has been marked as {new_status.lower()}.",
            notification_type,
            "applications.html"
        ))

    return jsonify({
        "success": True,
        "message": f"Application marked as {new_status}."
    })


# --------------------------------------------------
# FACULTY PROJECT DETAIL & ANALYTICS
# --------------------------------------------------

@faculty_bp.route("/projects/<int:project_id>", methods=["GET"])
@faculty_required
def get_faculty_project_detail(project_id):
    """Return comprehensive project analytics, process stage, team members and applicants for faculty."""
    user_id = get_current_user_id()
    user = get_current_user()
    is_admin = user and str(user.get("role", "")).lower() == "admin"

    if is_admin:
        project = fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    else:
        project = fetch_one("SELECT * FROM projects WHERE id = %s AND faculty_id = %s", (project_id, user_id))

    if not project:
        return jsonify({"success": False, "message": "Project not found or unauthorized."}), 404

    # Required skills
    skills = fetch_all("""
        SELECT s.id, s.name, s.category, ps.required_level
        FROM project_skills ps
        JOIN skills s ON ps.skill_id = s.id
        WHERE ps.project_id = %s
    """, (project_id,))

    # Team and members
    team = fetch_one("SELECT * FROM teams WHERE project_id = %s", (project_id,))
    team_members = []
    if team:
        team_members = fetch_all("""
            SELECT tm.id as member_id, tm.role, tm.joined_at,
                   s.id as student_id, s.department, s.year,
                   u.name as student_name, u.email as student_email
            FROM team_members tm
            JOIN students s ON tm.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE tm.team_id = %s
            ORDER BY tm.joined_at ASC
        """, (team['id'],))

        for m in team_members:
            m_skills = fetch_all("""
                SELECT sk.name, ss.proficiency_level
                FROM student_skills ss
                JOIN skills sk ON ss.skill_id = sk.id
                WHERE ss.student_id = %s
                ORDER BY ss.proficiency_level DESC
                LIMIT 4
            """, (m['student_id'],))
            m['skills'] = m_skills

    # Applications
    applications = fetch_all("""
        SELECT a.id, a.status, a.message, a.match_score, a.applied_at, a.reviewed_at,
               s.id as student_id, s.department, s.year,
               u.name as student_name, u.email as student_email
        FROM applications a
        JOIN students s ON a.student_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE a.project_id = %s
        ORDER BY
            CASE WHEN a.status = 'Pending' THEN 0 WHEN a.status = 'Accepted' THEN 1 ELSE 2 END,
            a.applied_at DESC
    """, (project_id,))

    team_size = int(project.get('team_size') or 4)
    member_count = len(team_members)
    open_spots = max(0, team_size - member_count)
    pending_apps = sum(1 for a in applications if a['status'] == 'Pending')
    accepted_apps = sum(1 for a in applications if a['status'] == 'Accepted')
    rejected_apps = sum(1 for a in applications if a['status'] == 'Rejected')

    fill_pct = round((member_count / team_size) * 100) if team_size > 0 else 0

    # Determine process stage (1 to 4)
    # Stage 1: Published
    # Stage 2: Applications In Review
    # Stage 3: Team Bed Formed
    # Stage 4: In Bloom & Active
    current_stage = 1
    if len(applications) > 0:
        current_stage = 2
    if member_count > 0:
        current_stage = 3
    if member_count >= team_size or project.get('status') == 'Completed':
        current_stage = 4

    return jsonify({
        "success": True,
        "project": project,
        "team": team,
        "team_members": team_members,
        "applications": applications,
        "required_skills": skills,
        "stats": {
            "team_size": team_size,
            "member_count": member_count,
            "open_spots": open_spots,
            "total_applications": len(applications),
            "pending_applications": pending_apps,
            "accepted_applications": accepted_apps,
            "rejected_applications": rejected_apps,
            "fill_percentage": fill_pct,
            "current_stage": current_stage
        }
    })


# --------------------------------------------------
# CERTIFICATE VERIFICATION
# --------------------------------------------------

@faculty_bp.route("/certificates", methods=["GET"])
@faculty_required
def list_pending_certificates():
    """List pending certificates from students who applied to faculty projects."""

    user_id = get_current_user_id()
    overview = get_faculty_overview(user_id)

    if not overview:
        return jsonify({
            "success": False,
            "message": "Faculty account not found."
        }), 404

    return jsonify({
        "success": True,
        "certificates": overview["pending_certificates"]
    })


@faculty_bp.route(
    "/certificates/<int:student_id>/<int:skill_id>",
    methods=["PUT"]
)
@faculty_required
def update_certificate_status(student_id, skill_id):
    """Verify or reject a certificate belonging to an eligible applicant."""

    user_id = get_current_user_id()
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in ("Verified", "Rejected"):
        return jsonify({
            "success": False,
            "message": "Status must be Verified or Rejected."
        }), 400

    user = get_current_user()
    is_admin = user and str(user.get("role", "")).lower() == "admin"

    # Confirm that the student applied to one of this faculty member's projects (unless admin).
    if not is_admin:
        eligible_student = fetch_one("""
            SELECT s.id
            FROM students s
            WHERE s.id = %s
              AND EXISTS (
                  SELECT 1
                  FROM applications a
                  JOIN projects p ON p.id = a.project_id
                  WHERE a.student_id = s.id
                    AND p.faculty_id = %s
              )
        """, (student_id, user_id))

        if not eligible_student:
            return jsonify({
                "success": False,
                "message": "This student is not an applicant to your projects."
            }), 403

    # Confirm that the requested skill record exists.
    certificate = fetch_one("""
        SELECT id, certificate_status, certificate_filename
        FROM student_skills
        WHERE student_id = %s
          AND skill_id = %s
    """, (student_id, skill_id))

    if not certificate:
        return jsonify({
            "success": False,
            "message": "Certificate or skill record not found."
        }), 404

    # Update the certificate status.
    execute_query("""
        UPDATE student_skills
        SET certificate_status = %s
        WHERE student_id = %s
          AND skill_id = %s
    """, (new_status, student_id, skill_id))

    # Notify the student.
    student = fetch_one(
        "SELECT user_id FROM students WHERE id = %s",
        (student_id,)
    )

    skill = fetch_one(
        "SELECT name FROM skills WHERE id = %s",
        (skill_id,)
    )

    if student and skill:
        execute_query("""
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            student["user_id"],
            f"Certificate {new_status}",
            f"Your certificate for {skill['name']} has been "
            f"{new_status.lower()}.",
            "success" if new_status == "Verified" else "warning",
            "profile.html"
        ))

    return jsonify({
        "success": True,
        "message": f"Certificate {new_status.lower()} successfully."
    })