from flask import Blueprint, request, jsonify, session
from backend.database import fetch_one, fetch_all
from backend.services.matching_service import (
    get_ranked_project_recommendations,
    get_project_skill_gaps,
    get_teammate_recommendations_for_project
)

matching_bp = Blueprint('matching', __name__)

def get_current_student_id():
    user_id = session.get('user_id', 1)
    student = fetch_one("SELECT id FROM students WHERE user_id = %s", (user_id,))
    return student['id'] if student else 1


@matching_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    student_id = get_current_student_id()
    recommendations = get_ranked_project_recommendations(student_id)
    return jsonify({
        "success": True,
        "count": len(recommendations),
        "recommendations": recommendations
    })


@matching_bp.route('/projects/<int:project_id>/gaps', methods=['GET'])
def get_gaps(project_id):
    gaps_data = get_project_skill_gaps(project_id)
    if not gaps_data:
        return jsonify({"success": False, "message": "Project not found."}), 404
    return jsonify({"success": True, "data": gaps_data})


@matching_bp.route('/projects/<int:project_id>/teammates', methods=['GET'])
def get_teammates(project_id):
    teammates = get_teammate_recommendations_for_project(project_id)
    return jsonify({"success": True, "count": len(teammates), "teammates": teammates})


@matching_bp.route('/all-gaps', methods=['GET'])
def get_all_gaps():
    projects = fetch_all("SELECT id, title, domain FROM projects")
    results = []
    for p in projects:
        gap_info = get_project_skill_gaps(p['id'])
        if gap_info:
            results.append({
                "project_id": p['id'],
                "project_title": p['title'],
                "domain": p['domain'],
                "gaps": gap_info['gaps'],
                "skill_breakdown": gap_info['skill_breakdown'],
                "team_members_count": len(gap_info['team_members'])
            })
    return jsonify({"success": True, "projects_gaps": results})
