"""
Student Skill and Project Matching System
Main Runner Script
"""

import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "=" * 65)
    print("  STUDENT SKILL AND PROJECT MATCHING SYSTEM")
    print("  Web Application running at: http://127.0.0.1:" + str(port))
    print("  Press Ctrl+C to terminate.")
    print("=" * 65 + "\n")
    app.run(host='127.0.0.1', port=port, debug=True)
