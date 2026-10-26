import os
import sys

# Ensure root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from backend.config import Config
from backend.database import init_db
from backend.rate_limiter import clear_all_rate_limits
from backend.csrf import check_csrf, get_or_create_csrf_token
from backend.auth_utils import authorize_certificate_access

# Import route blueprints
from backend.routes.auth_routes import auth_bp
from backend.routes.student_routes import student_bp
from backend.routes.project_routes import project_bp
from backend.routes.matching_routes import matching_bp
from backend.routes.application_routes import application_bp
from backend.routes.notification_routes import notification_bp
from backend.routes.faculty_routes import faculty_bp

FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

def create_app():
    clear_all_rate_limits()
    app = Flask(__name__, static_folder=FRONTEND_DIR)
    app.config.from_object(Config)

    # Sessions: signed with SECRET_KEY, kept for a week.
    app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
    app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE
    app.config['SESSION_COOKIE_SECURE'] = Config.SESSION_COOKIE_SECURE

    # Enable Cross-Origin Resource Sharing with explicit trusted origins
    CORS(app, origins=Config.CORS_ALLOWED_ORIGINS, supports_credentials=True)

    # Configure ProxyFix for deployment behind trusted proxies (e.g. Render)
    trusted_proxies = int(os.environ.get('TRUSTED_PROXIES', '1' if Config.IS_PRODUCTION else '0'))
    if trusted_proxies > 0:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=trusted_proxies,
            x_proto=trusted_proxies,
            x_host=trusted_proxies,
            x_port=trusted_proxies,
            x_prefix=trusted_proxies
        )

    # CSRF Protection Hook on state-changing requests
    @app.before_request
    def enforce_csrf():
        csrf_err = check_csrf()
        if csrf_err is not None:
            return csrf_err

    # Initialize Database on startup
    with app.app_context():
        init_db()

    # Register API blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(project_bp, url_prefix='/api/projects')
    app.register_blueprint(matching_bp, url_prefix='/api/matching')
    app.register_blueprint(application_bp, url_prefix='/api/applications')
    app.register_blueprint(notification_bp, url_prefix='/api/notifications')
    app.register_blueprint(faculty_bp, url_prefix='/api/faculty')

    # Endpoint to retrieve fresh CSRF token
    @app.route('/api/auth/csrf-token', methods=['GET'])
    def get_csrf_token_endpoint():
        token = get_or_create_csrf_token()
        return jsonify({"success": True, "csrf_token": token})

    # Secured certificate serving route with IDOR & authorization enforcement
    @app.route('/api/certificates/<filename>', methods=['GET'])
    def get_certificate(filename):
        is_authorized, result = authorize_certificate_access(filename)
        if not is_authorized:
            response_tuple = result
            return response_tuple
        clean_filename = result
        return send_from_directory(Config.UPLOAD_FOLDER, clean_filename)

    # Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "system": "Student Skill and Project Matching System",
            "version": "1.0.0"
        })

    @app.after_request
    def set_headers_and_csrf(response):
        """
        Sets freshness headers, sets readable CSRF cookie for client JS,
        and secures browser caching behavior.
        """
        # Expose CSRF token in a cookie readable by client JavaScript
        token = get_or_create_csrf_token()
        response.set_cookie(
            'csrf_token',
            token,
            secure=Config.SESSION_COOKIE_SECURE,
            httponly=False,
            samesite=Config.SESSION_COOKIE_SAMESITE,
            path='/'
        )

        # Security hardening headers (Issue 1)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' http://127.0.0.1:5000 http://localhost:5000 ws://127.0.0.1:5000 ws://localhost:5000; "
            "frame-ancestors 'none';"
        )

        if response.mimetype == 'text/html':
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        elif response.mimetype in ('text/css', 'application/javascript', 'text/javascript'):
            response.headers['Cache-Control'] = 'public, max-age=3600'
        return response

    # Frontend serving routes
    @app.route('/', methods=['GET'])
    def serve_index():
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.errorhandler(404)
    def handle_not_found(err):
        """Return a JSON 404 for API clients instead of the SPA landing page."""
        if request.path.startswith('/api/'):
            return jsonify({
                "success": False,
                "message": f"API endpoint not found: {request.path}"
            }), 404
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/<path:filename>', methods=['GET'])
    def serve_frontend_file(filename):
        # Never let the SPA fallback mask a mistyped API route.
        if filename == 'api' or filename.startswith('api/'):
            return jsonify({
                "success": False,
                "message": f"API endpoint not found: /{filename}"
            }), 404

        # Resolve safely inside FRONTEND_DIR (blocks path traversal).
        file_path = os.path.normpath(os.path.join(FRONTEND_DIR, filename))
        if os.path.commonpath([os.path.abspath(file_path), FRONTEND_DIR]) == FRONTEND_DIR \
                and os.path.isfile(file_path):
            return send_from_directory(FRONTEND_DIR, filename)

        # Default to index.html if not found
        return send_from_directory(FRONTEND_DIR, 'index.html')

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print(f"\n=======================================================")
    print(f"  STUDENT SKILL AND PROJECT MATCHING SYSTEM")
    print(f"  Server starting at: http://127.0.0.1:{port}")
    print(f"  Debug mode: {'ON' if debug else 'OFF'}")
    print(f"=======================================================\n")
    app.run(host='127.0.0.1', port=port, debug=debug)
