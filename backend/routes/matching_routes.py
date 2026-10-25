
from flask import Blueprint, jsonify, request

from backend.database import fetch_all, fetch_one, execute_query
from backend.auth_utils import get_current_student_id, get_current_user_id, is_faculty, is_admin
from backend.services.matching_service import (
    get_ranked_project_recommendations,
    get_project_skill_gaps,
    get_teammate_recommendations_for_project
)
from backend.services.dashboard_service import get_dashboard


matching_bp = Blueprint("matching", __name__)


def student_login_required():
    """Return the student ID or an authentication error response."""
    student_id = get_current_student_id()

    if student_id is None:
        return None, (
            jsonify({
                "success": False,
                "message": "Please log in with a student account."
            }),
            401
        )

    return student_id, None


@matching_bp.route("/recommendations", methods=["GET"])
def get_recommendations():
    student_id, error = student_login_required()

    if error:
        return error

    recommendations = get_ranked_project_recommendations(student_id)

    return jsonify({
        "success": True,
        "count": len(recommendations),
        "recommendations": recommendations
    }), 200


@matching_bp.route("/dashboard", methods=["GET"])
def get_dashboard_data():
    student_id, error = student_login_required()

    if error:
        return error

    dashboard = get_dashboard(student_id)

    if not dashboard:
        return jsonify({
            "success": False,
            "message": "Dashboard data not found."
        }), 404

    return jsonify({
        "success": True,
        "dashboard": dashboard
    }), 200


@matching_bp.route("/projects/<int:project_id>/gaps", methods=["GET"])
def get_gaps(project_id):
    student_id, error = student_login_required()

    if error:
        return error

    gaps_data = get_project_skill_gaps(project_id)

    if gaps_data is None:
        return jsonify({
            "success": False,
            "message": "Skill-gap data not found."
        }), 404

    return jsonify({
        "success": True,
        "project_id": project_id,
        "gaps": gaps_data
    }), 200


@matching_bp.route(
    "/projects/<int:project_id>/teammates",
    methods=["GET"]
)
def get_teammates(project_id):
    student_id, error = student_login_required()

    if error:
        return error

    teammates = get_teammate_recommendations_for_project(project_id)

    if teammates is None:
        return jsonify({
            "success": False,
            "message": "Teammate recommendations not found."
        }), 404

    return jsonify({
        "success": True,
        "project_id": project_id,
        "teammates": teammates
    }), 200


@matching_bp.route("/projects/<int:project_id>/invite", methods=["POST"])
def invite_teammate(project_id):
    student_id = get_current_student_id()
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({
            "success": False,
            "message": "Please log in to send team invitations."
        }), 401

    project = fetch_one("SELECT id, title, faculty_id, status FROM projects WHERE id = %s", (project_id,))
    if not project:
        return jsonify({"success": False, "message": "Project not found."}), 404

    if project.get("status") and str(project["status"]).lower() != "open":
        return jsonify({"success": False, "message": "Cannot invite teammates to a closed project."}), 400

    data = request.get_json(silent=True) or {}
    target_student_id = data.get("student_id")

    if not target_student_id:
        return jsonify({"success": False, "message": "Target student ID is required."}), 400

    target_student = fetch_one("""
        SELECT s.id, s.user_id, s.profile_visibility, u.name
        FROM students s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = %s
    """, (target_student_id,))

    if not target_student:
        return jsonify({"success": False, "message": "Target student not found."}), 404

    if target_student.get("profile_visibility") == "private":
        return jsonify({
            "success": False,
            "message": "This student has a private profile and cannot receive team invitations."
        }), 403

    already_in_team = fetch_one("""
        SELECT 1 FROM team_members tm
        JOIN teams t ON tm.team_id = t.id
        WHERE t.project_id = %s AND tm.student_id = %s
    """, (project_id, target_student_id))
    already_accepted = fetch_one("""
        SELECT 1 FROM applications
        WHERE project_id = %s AND student_id = %s AND status = 'Accepted'
    """, (project_id, target_student_id))

    if already_in_team or already_accepted:
        return jsonify({
            "success": False,
            "message": f"{target_student['name']} is already on the team for this project."
        }), 400

    execute_query(
        "INSERT INTO notifications (user_id, title, message, type, link) VALUES (%s, %s, %s, %s, %s)",
        (
            target_student["user_id"],
            "Team Invitation 🌿",
            f"You have been invited to join the team for {project['title']}!",
            "invite",
            "applications.html"
        )
    )

    return jsonify({
        "success": True,
        "message": f"Invitation sent to {target_student['name']}!"
    }), 200


@matching_bp.route("/all-gaps", methods=["GET"])
def get_all_gaps():
    student_id, error = student_login_required()

    if error:
        return error

    projects = fetch_all(
        "SELECT id, title, domain FROM projects"
    )

    if projects is None:
        return jsonify({
            "success": False,
            "message": "Unable to retrieve projects."
        }), 500

    results = []

    for project in projects:
        gaps_data = get_project_skill_gaps(project["id"])

        results.append({
            "project_id": project["id"],
            "title": project["title"],
            "domain": project["domain"],
            "gaps": gaps_data
        })

    return jsonify({
        "success": True,
        "count": len(results),
        "projects": results
    }), 200
