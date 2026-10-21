import os
import sys

# Ensure root directory is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from backend.config import Config
from backend.database import init_db

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
    app = Flask(__name__, static_folder=FRONTEND_DIR)
    app.config.from_object(Config)

    # Sessions: signed with SECRET_KEY, kept for a week.
    app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
    app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE
    app.config['SESSION_COOKIE_SECURE'] = Config.SESSION_COOKIE_SECURE

    # Enable Cross-Origin Resource Sharing
    CORS(app, supports_credentials=True)

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

    # Direct certificate serving route
    @app.route('/api/certificates/<filename>', methods=['GET'])
    def get_certificate(filename):
        return send_from_directory(Config.UPLOAD_FOLDER, filename)

    # Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "system": "Student Skill and Project Matching System",
            "version": "1.0.0"
        })

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
    print(f"\n=======================================================")
    print(f"  STUDENT SKILL AND PROJECT MATCHING SYSTEM")
    print(f"  Server starting at: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host='127.0.0.1', port=port, debug=True)
