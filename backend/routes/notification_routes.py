from flask import Blueprint, jsonify, session
from backend.database import fetch_all, execute_query

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('', methods=['GET'])
def get_notifications():
    user_id = session.get('user_id', 1)
    notifications = fetch_all("""
        SELECT * FROM notifications 
        WHERE user_id = %s 
        ORDER BY created_at DESC 
        LIMIT 50
    """, (user_id,))
    return jsonify({"success": True, "notifications": notifications})


@notification_bp.route('/<int:notif_id>/read', methods=['POST'])
def mark_read(notif_id):
    user_id = session.get('user_id', 1)
    execute_query("UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s", (notif_id, user_id))
    return jsonify({"success": True, "message": "Marked as read."})


@notification_bp.route('/read-all', methods=['POST'])
def mark_all_read():
    user_id = session.get('user_id', 1)
    execute_query("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (user_id,))
    return jsonify({"success": True, "message": "All notifications marked as read."})
