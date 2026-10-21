"""
CSRF Protection Middleware for SkillMatch.

Provides token generation, Origin/Referer verification, and session-bound
token validation for state-changing HTTP operations (POST, PUT, PATCH, DELETE).
"""

import hmac
import secrets
from urllib.parse import urlparse
from flask import request, session, current_app, jsonify
from backend.config import Config


SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}

# Auth routes that establish sessions before a session token is set
EXEMPT_ROUTES = {
    '/api/auth/login',
    '/api/auth/register',
    '/api/health'
}


def get_or_create_csrf_token():
    """Returns or initializes the CSRF token stored in the server session."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def validate_origin():
    """
    Validates request Origin or Referer against allowed origins and host URL.
    Returns (True, None) if valid, or (False, error_message) if untrusted.
    """
    origin = request.headers.get('Origin')
    if origin:
        allowed = set(Config.CORS_ALLOWED_ORIGINS)
        allowed.add(request.host_url.rstrip('/'))
        if origin.rstrip('/') not in {a.rstrip('/') for a in allowed}:
            return False, f"Origin '{origin}' is not trusted."
        return True, None

    referer = request.headers.get('Referer')
    if referer:
        parsed_ref = urlparse(referer)
        ref_origin = f"{parsed_ref.scheme}://{parsed_ref.netloc}"
        allowed = set(Config.CORS_ALLOWED_ORIGINS)
        allowed.add(request.host_url.rstrip('/'))
        if ref_origin.rstrip('/') not in {a.rstrip('/') for a in allowed}:
            return False, f"Referer origin '{ref_origin}' is not trusted."

    return True, None


def check_csrf():
    """
    Validates CSRF tokens and origins on state-changing requests.
    Returns None if check passes, or a Flask JSON response tuple if it fails.
    """
    if request.method in SAFE_METHODS:
        return None

    if not Config.CSRF_ENABLED:
        return None

    # Check origin/referer if present
    is_valid_origin, origin_err = validate_origin()
    if not is_valid_origin:
        return jsonify({
            "success": False,
            "message": f"CSRF Check Failed: {origin_err}"
        }), 403

    # If the route is explicitly exempt from token checking (e.g. initial login/registration)
    if request.path in EXEMPT_ROUTES:
        return None

    # In automated test mode without explicit enforcement, pass through
    if current_app.config.get('TESTING') and not current_app.config.get('ENFORCE_CSRF_IN_TESTS'):
        return None

    # For authenticated users or existing sessions, token is strictly required
    server_token = session.get('_csrf_token')
    if not server_token:
        # If user is logged in but session has no token, it's an invalid session state
        if session.get('user_id'):
            return jsonify({
                "success": False,
                "message": "CSRF token missing from session. Please reload and log in again."
            }), 403
        return None

    client_token = (
        request.headers.get('X-CSRF-Token')
        or request.headers.get('X-XSRF-Token')
        or request.headers.get('X-CSRFToken')
        or (request.form.get('csrf_token') if request.form else None)
    )

    if not client_token:
        return jsonify({
            "success": False,
            "message": "CSRF token is required for this request (X-CSRF-Token header)."
        }), 403

    if not hmac.compare_digest(server_token, client_token):
        return jsonify({
            "success": False,
            "message": "Invalid CSRF token."
        }), 403

    return None
