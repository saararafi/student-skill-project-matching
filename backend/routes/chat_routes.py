"""
AI Chatbot API routes.

Provides interactive AI Academic Advisor capabilities to students and faculty.
"""

from flask import Blueprint, jsonify, request
from backend.auth_utils import get_current_user_id, login_required
from backend.services.chatbot_service import generate_chat_response, get_student_chat_context, get_faculty_chat_context
from backend.database import fetch_one

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("", methods=["POST"])
@chat_bp.route("/message", methods=["POST"])
@login_required
def chat_message():
    """Send a message to the AI Botanical Advisor and receive personalized advice."""
    user_id = get_current_user_id()
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []

    if not message:
        return jsonify({
            "success": False,
            "message": "A non-empty message is required."
        }), 400

    reply, suggestions, context_data = generate_chat_response(user_id, message, history)

    return jsonify({
        "success": True,
        "reply": reply,
        "suggestions": suggestions,
        "context": context_data
    })


@chat_bp.route("/status", methods=["GET"])
@login_required
def chat_status():
    """Return greeting status, user role, and initial suggestion chips for the chat widget."""
    user_id = get_current_user_id()
    user = fetch_one("SELECT id, name, role FROM users WHERE id = %s", (user_id,))
    if not user:
        return jsonify({"success": False, "message": "User not found."}), 404

    role = (user.get("role") or "").strip().lower()
    name = user.get("name", "Friend")

    if role == "student":
        student_ctx = get_student_chat_context(user_id)
        completeness = student_ctx.get("completeness", 0) if student_ctx else 0
        recs = student_ctx.get("recommendations", []) if student_ctx else []
        top_match = recs[0]["title"] if recs else None

        greeting = (
            f"Good day, **{name}**! ❧\n\n"
            f"I am your **SkillMatch Botanical AI Advisor**. I am here to guide your academic growth, "
            f"explain matching compatibility, and help you find ideal project teammates.\n\n"
            f"Your profile is currently at **{completeness}% completeness**."
            + (f" Your highest match right now is **{top_match}** ({round(recs[0]['match_score'])}%)." if top_match else "")
        )
        suggestions = [
            "🌿 Top Project Matches",
            "📊 My Skill Gaps",
            "📈 Profile Completeness",
            "📜 Certificate Help"
        ]
    else:
        faculty_ctx = get_faculty_chat_context(user_id)
        stats = faculty_ctx.get("stats", {}) if faculty_ctx else {}
        greeting = (
            f"Good day, **{name}**! ❧\n\n"
            f"I am your **Faculty AI Assistant**. You currently have **{stats.get('projects', 0)} open projects**, "
            f"**{stats.get('pending_applications', 0)} pending applications**, and "
            f"**{stats.get('pending_certificates', 0)} certificates awaiting verification**."
        )
        suggestions = [
            "Review Applications",
            "Verify Certificates",
            "Publish New Project",
            "My Guided Projects"
        ]

    return jsonify({
        "success": True,
        "online": True,
        "user_name": name,
        "role": role,
        "greeting": greeting,
        "suggestions": suggestions
    })
