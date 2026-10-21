from flask import Blueprint, jsonify
from backend.database import fetch_all, execute_query
from backend.auth_utils import get_current_user_id, login_required

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('', methods=['GET'])
def get_notifications():
    user_id = get_current_user_id()
    notifications = fetch_all("""
        SELECT * FROM notifications 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 50
    """, (user_id,))
    return jsonify({"success": True, "notifications": notifications})


@notification_bp.route('/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_read(notif_id):
    user_id = get_current_user_id()
    execute_query("UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s", (notif_id, user_id))
    return jsonify({"success": True, "message": "Marked as read."})


@notification_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    user_id = get_current_user_id()
    execute_query("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (user_id,))
    return jsonify({"success": True, "message": "All notifications marked as read."})
