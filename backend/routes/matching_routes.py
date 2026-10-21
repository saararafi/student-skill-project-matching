
from flask import Blueprint, jsonify, request

from backend.database import fetch_all, fetch_one, execute_query
from backend.auth_utils import get_current_student_id
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
    student_id, error = student_login_required()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    target_student_id = data.get("student_id")
    target_name = data.get("student_name")

    project = fetch_one("SELECT title FROM projects WHERE id = %s", (project_id,))
    p_title = project["title"] if project else "Project"

    target_user_id = None
    if target_student_id:
        st = fetch_one("SELECT user_id FROM students WHERE id = %s", (target_student_id,))
        if st:
            target_user_id = st.get("user_id")

    if target_user_id:
        execute_query(
            "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, %s)",
            (target_user_id, "Team Invitation 🌿", f"You have been invited to join the team for {p_title}!", "invite")
        )

    return jsonify({
        "success": True,
        "message": f"Invitation sent to {target_name or 'teammate'}!"
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
