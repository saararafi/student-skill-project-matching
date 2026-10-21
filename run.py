"""
Student Skill and Project Matching System
Main Runner Script.

Works both as a local development server:

    python run.py

and as a production entry point on WSGI servers (Gunicorn, Waitress, Render):

    gunicorn -w 4 -b 0.0.0.0:5000 "backend.app:app"

For development with hot-reload and debugging, explicitly set FLASK_DEBUG=1:

    $env:FLASK_DEBUG="1"; python run.py
"""

import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Debug mode is explicitly OFF by default for security
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print("\n" + "=" * 65)
    print("  STUDENT SKILL AND PROJECT MATCHING SYSTEM")
    print(f"  Web Application running at: http://127.0.0.1:{port}")
    print(f"  Debug mode: {'ON (Development only)' if debug else 'OFF (Secure default)'}")
    print("  Press Ctrl+C to terminate.")
    print("=" * 65 + "\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
