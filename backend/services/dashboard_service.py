"""
Aggregated data for the student dashboard.

The dashboard shows several panels (profile health, statistics, the single
best project match, skill plants, recent applications and recent
notifications). Fetching each of those from separate endpoints would mean
six round trips, so they are assembled server-side into one response.
"""

from backend.database import fetch_one, fetch_all
from backend.services.matching_service import (
    get_student_profile_data,
    get_ranked_project_recommendations,
)


def get_dashboard(student_id):
    """Builds the full dashboard payload for a student."""
    data = get_student_profile_data(student_id)
    if not data:
        return None

    student = data['student']
    user = data['user']
    skills = data['skills_list']
    interests = data['interests']
    experiences = data['experiences']

    # --- Statistics -----------------------------------------------------
    verified_certs = sum(
        1 for s in skills if s.get('certificate_status') == 'Verified'
    )
    pending_certs = sum(
        1 for s in skills if s.get('certificate_status') == 'Pending'
    )

    applications = fetch_all("""
        SELECT a.id, a.project_id, a.status, a.match_score, a.applied_at,
               p.title AS project_title, p.domain
        FROM applications a
        JOIN projects p ON a.project_id = p.id
        WHERE a.student_id = %s
        ORDER BY a.applied_at DESC
    """, (student_id,))

    stats = {
        "skills": len(skills),
        "interests": len(interests),
        "experiences": len(experiences),
        "certificates": len([s for s in skills if s.get('certificate_filename')]),
        "verified_certificates": verified_certs,
        "pending_certificates": pending_certs,
        "applications": len(applications),
    }

    # --- Project matches ------------------------------------------------
    recommendations = get_ranked_project_recommendations(student_id)
    top_match = None
    if recommendations:
        best = recommendations[0]
        top_match = {
            "project_id": best['id'],
            "title": best['title'],
            "description": best['description'],
            "domain": best['domain'],
            "team_size": best['team_size'],
            "required_availability": best['required_availability'],
            "final_score": best['match_score'],
            "skill_score": best['skill_score'],
            "interest_score": best['interest_score'],
            "experience_score": best['experience_score'],
            "availability_score": best['availability_score'],
            "skill_details": best['skill_details'],
        }

    # --- Recent notifications -------------------------------------------
    notifications = fetch_all("""
        SELECT id, title, message, type, link, is_read, created_at
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 4
    """, (student['user_id'],))

    # --- Profile health (0% base, based purely on real fields) ----------
    completeness = 0
    dept = (student.get('department') or '').strip()
    if dept and dept.lower() not in ('', 'general'):
        completeness += 10

    year = (student.get('year') or '').strip()
    sem = (student.get('semester') or '').strip()
    if year and sem:
        completeness += 10

    bio = (student.get('bio') or '').strip()
    if bio and bio.lower() not in ('', 'new student profile.'):
        completeness += 10

    gh = (student.get('github_url') or '').strip()
    li = (student.get('linkedin_url') or '').strip()
    if gh or li:
        completeness += 10

    if len(skills) >= 3:
        completeness += 20
    elif len(skills) >= 1:
        completeness += 10

    if len(interests) >= 2:
        completeness += 15
    elif len(interests) >= 1:
        completeness += 10

    if len(experiences) >= 1:
        completeness += 10

    if any(s.get('certificate_filename') for s in skills):
        completeness += 15

    completeness = max(0, min(100, completeness))

    return {
        "profile": {
            "student_id": student['id'],
            "name": user['name'] if user else '',
            "email": user['email'] if user else '',
            "department": student.get('department'),
            "year": student.get('year'),
            "semester": student.get('semester'),
            "availability": student.get('availability'),
            "bio": student.get('bio'),
            "completeness": completeness,
        },
        "stats": stats,
        "top_match": top_match,
        "skills": skills,
        "applications": applications[:4],
        "notifications": notifications,
        "recommendations": recommendations[:3],
    }
