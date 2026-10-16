"""
STUDENT SKILL AND PROJECT MATCHING SYSTEM — Flask application.

DAY 1 MILESTONE: serve the frontend pages from templates/ and prove
the full pipeline works:  Flask  →  MySQL  →  JSON  →  browser.

How a request flows through this file:
  1. Browser asks for e.g. /projects
  2. Flask matches it to a route below
  3. The route either renders an HTML page from templates/
     or queries MySQL through db.py and returns JSON

Run with:  python app.py   then open  http://127.0.0.1:5000
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

import db

load_dotenv()  # read .env into os.environ

app = Flask(__name__)

# Secret key is needed once we turn on login sessions (Day 2).
# It signs the session cookie so it cannot be tampered with.
app.secret_key = os.environ.get(
    "SECRET_KEY", "dev-only-fallback-change-me"
)


# =====================================================================
# PAGE ROUTES — each renders one HTML file from templates/
# =====================================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@app.route("/profile")
def profile_page():
    return render_template("profile.html")


@app.route("/projects")
def projects_page():
    return render_template("projects.html")


@app.route("/team")
def team_page():
    return render_template("team.html")


@app.route("/gaps")
def gaps_page():
    return render_template("gaps.html")


# =====================================================================
# API ROUTES — each returns JSON (data), not HTML (pages)
# =====================================================================

@app.route("/api/health")
def api_health():
    """
    Health check: can we reach MySQL?
    Visit /api/health in your browser after starting the app.
    """
    try:
        conn = db.connect()
        conn.close()
        return jsonify({"status": "ok", "database": "connected"})
    except Exception as error:
        return jsonify(
            {"status": "error", "database": str(error)}
        ), 500


@app.route("/api/skills")
def api_skills():
    """All skills in the catalogue, with their categories."""
    rows = db.query(
        "SELECT skill_id, skill_name, category FROM skills ORDER BY skill_name"
    )
    return jsonify(rows)


@app.route("/api/projects")
def api_projects():
    """
    All open projects, each with its required skills and levels.

    The join mirrors your ER design:
      projects → project_skills → skills

    Grouping in Python keeps the SQL simple and readable.
    """
    rows = db.query(
        """
        SELECT p.project_id, p.title, p.description, p.domain,
               p.team_size, p.status,
               s.skill_name, ps.required_proficiency
        FROM projects p
        JOIN project_skills ps ON ps.project_id = p.project_id
        JOIN skills s ON s.skill_id = ps.skill_id
        WHERE p.status = 'OPEN'
        ORDER BY p.title
        """
    )

    # Restructure the flat rows into one object per project
    projects = {}
    for row in rows:
        pid = row["project_id"]
        if pid not in projects:
            projects[pid] = {
                "project_id": pid,
                "title": row["title"],
                "description": row["description"],
                "domain": row["domain"],
                "team_size": row["team_size"],
                "required_skills": {},
            }
        projects[pid]["required_skills"][row["skill_name"]] = row[
            "required_proficiency"
        ]

    return jsonify(list(projects.values()))


if __name__ == "__main__":
    # debug=True auto-reloads on code changes — for LOCAL development only
    app.run(debug=True)
