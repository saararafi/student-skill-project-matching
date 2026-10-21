import sys
import os

# Ensure project root is in sys.path so algorithm imports succeed
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from algorithm.matching import calculate_skill_match
from algorithm.interest_matching import calculate_interest_match
from algorithm.experience_matching import calculate_experience_match
from algorithm.availability_matching import calculate_availability_match
from algorithm.weighted_matching import calculate_weighted_match
from algorithm.project_recommendation import recommend_projects
from algorithm.skill_gap import detect_skill_gaps
from algorithm.teammate_recommendation import recommend_teammates

from backend.database import fetch_one, fetch_all


def get_student_profile_data(student_id):
    """Retrieves all skill, interest, experience, and availability data for a student."""
    student = fetch_one("SELECT * FROM students WHERE id = %s", (student_id,))
    if not student:
        return None

    user = fetch_one("SELECT name, email, role FROM users WHERE id = %s", (student['user_id'],))
    
    # Skills with certificates
    skills_rows = fetch_all("""
        SELECT s.id as skill_id, s.name, s.category, ss.proficiency_level, 
               ss.certificate_filename, ss.certificate_original_name, 
               ss.certificate_status, ss.uploaded_at
        FROM student_skills ss
        JOIN skills s ON ss.skill_id = s.id
        WHERE ss.student_id = %s
    """, (student_id,))

    skills_dict = {row['name']: row['proficiency_level'] for row in skills_rows}
    skills_meta = {row['name']: row for row in skills_rows}

    # Interests
    interest_rows = fetch_all("SELECT interest FROM student_interests WHERE student_id = %s", (student_id,))
    interests = [r['interest'] for r in interest_rows]

    # Experiences
    exp_rows = fetch_all("SELECT experience_title FROM student_experiences WHERE student_id = %s", (student_id,))
    experiences = [r['experience_title'] for r in exp_rows]

    return {
        "student": student,
        "user": user,
        "skills_dict": skills_dict,
        "skills_meta": skills_meta,
        "skills_list": skills_rows,
        "interests": interests,
        "experiences": experiences,
        "availability": student.get('availability', 'Part-time'),
        "preferences": get_matching_preferences(student)
    }


# Default weights for the four compatibility factors.
DEFAULT_WEIGHTS = {
    "skill": 0.50,
    "interest": 0.20,
    "experience": 0.20,
    "availability": 0.10
}


def get_matching_preferences(student):
    """
    Returns the factor weights for a student.

    A student can switch individual factors off in their settings. Disabled
    factors are dropped and the remaining weights are renormalised so the
    total always stays at 1.0.
    """
    preferences = {
        "prioritise_skills": bool(student.get('prioritise_skills', 1)),
        "consider_interests": bool(student.get('consider_interests', 1)),
        "consider_experience": bool(student.get('consider_experience', 1)),
        "consider_availability": bool(student.get('consider_availability', 1)),
    }

    weights = {
        "skill": DEFAULT_WEIGHTS["skill"] if preferences["prioritise_skills"] else 0,
        "interest": DEFAULT_WEIGHTS["interest"] if preferences["consider_interests"] else 0,
        "experience": DEFAULT_WEIGHTS["experience"] if preferences["consider_experience"] else 0,
        "availability": DEFAULT_WEIGHTS["availability"] if preferences["consider_availability"] else 0,
    }

    # If every factor is switched off, fall back to the standard weights.
    if sum(weights.values()) <= 0:
        weights = dict(DEFAULT_WEIGHTS)

    return {"weights": weights, "enabled": preferences}


def get_project_profile_data(project_id):
    """Retrieves project requirements including skills, interests, experience, and availability."""
    project = fetch_one("SELECT * FROM projects WHERE id = %s", (project_id,))
    if not project:
        return None

    # Required skills
    skill_rows = fetch_all("""
        SELECT s.id as skill_id, s.name, s.category, ps.required_level
        FROM project_skills ps
        JOIN skills s ON ps.skill_id = s.id
        WHERE ps.project_id = %s
    """, (project_id,))
    
    required_skills = {row['name']: row['required_level'] for row in skill_rows}

    # Interests
    interest_rows = fetch_all("SELECT interest FROM project_interests WHERE project_id = %s", (project_id,))
    project_interests = [r['interest'] for r in interest_rows]

    # Experiences
    exp_rows = fetch_all("SELECT experience_title FROM project_experiences WHERE project_id = %s", (project_id,))
    project_experiences = [r['experience_title'] for r in exp_rows]

    return {
        "project": project,
        "required_skills": required_skills,
        "skill_rows": skill_rows,
        "interests": project_interests,
        "experiences": project_experiences,
        "required_availability": project.get('required_availability', 'Part-time')
    }


def compute_match(student_id, project_id):
    """Computes the full weighted compatibility breakdown between a student and a project."""
    student_data = get_student_profile_data(student_id)
    project_data = get_project_profile_data(project_id)

    if not student_data or not project_data:
        return None

    # 1. Skill Match
    skill_score, skill_scores_breakdown = calculate_skill_match(
        student_data['skills_dict'],
        project_data['required_skills']
    )

    # 2. Interest Match
    interest_score = calculate_interest_match(
        student_data['interests'],
        project_data['interests']
    )

    # 3. Experience Match
    experience_score = calculate_experience_match(
        student_data['experiences'],
        project_data['experiences']
    )

    # 4. Availability Match
    availability_score = calculate_availability_match(
        student_data['availability'],
        project_data['required_availability']
    )

    # 5. Final Weighted Match (using the student's chosen factors, renormalized for active project categories)
    weights = dict(student_data.get('preferences', {}).get('weights') or DEFAULT_WEIGHTS)

    # Check if project defines each category
    has_skills = bool(project_data.get('required_skills'))
    has_interests = bool(project_data.get('interests'))
    has_experiences = bool(project_data.get('experiences'))
    has_availability = bool(project_data.get('required_availability'))

    # If project lacks specific categories, drop that category so the student isn't penalized
    active_weights = dict(weights)
    if not has_skills:
        active_weights['skill'] = 0.0
    if not has_interests:
        active_weights['interest'] = 0.0
    if not has_experiences:
        active_weights['experience'] = 0.0
    if not has_availability:
        active_weights['availability'] = 0.0

    total_w = sum(active_weights.values())
    if total_w > 0:
        norm_weights = {k: v / total_w for k, v in active_weights.items()}
        final_score = calculate_weighted_match(
            skill_score,
            interest_score,
            experience_score,
            availability_score,
            weights=active_weights
        )
    else:
        norm_weights = dict(DEFAULT_WEIGHTS)
        final_score = 100.0 if not any([has_skills, has_interests, has_experiences]) else 0.0

    # Enrich skill breakdown with certificate information
    enriched_skills = []
    for skill_name, req_level in project_data['required_skills'].items():
        stu_level = student_data['skills_dict'].get(skill_name, 0)
        score = skill_scores_breakdown.get(skill_name, 0)
        cert_info = student_data['skills_meta'].get(skill_name, {})
        enriched_skills.append({
            "skill": skill_name,
            "required_level": req_level,
            "student_level": stu_level,
            "match_pct": score,
            "has_certificate": bool(cert_info.get('certificate_filename')),
            "certificate_status": cert_info.get('certificate_status', 'None'),
            "certificate_filename": cert_info.get('certificate_filename')
        })

    return {
        "project_id": project_id,
        "project_title": project_data['project']['title'],
        "domain": project_data['project']['domain'],
        "final_score": final_score,
        "weights": {
            "skill_weight": f"{int(round(norm_weights.get('skill', 0.5) * 100))}%",
            "interest_weight": f"{int(round(norm_weights.get('interest', 0.2) * 100))}%",
            "experience_weight": f"{int(round(norm_weights.get('experience', 0.2) * 100))}%",
            "availability_weight": f"{int(round(norm_weights.get('availability', 0.1) * 100))}%"
        },
        "scores": {
            "skill_score": skill_score,
            "interest_score": interest_score,
            "experience_score": experience_score,
            "availability_score": availability_score
        },
        "skill_details": enriched_skills,
        "student_availability": student_data['availability'],
        "project_availability": project_data['required_availability']
    }


def get_ranked_project_recommendations(student_id):
    """Calculates compatibility scores for all open projects and returns them sorted."""
    projects = fetch_all("SELECT id, title, description, domain, team_size, required_availability, status FROM projects")
    
    scored_projects = []
    for p in projects:
        match_res = compute_match(student_id, p['id'])
        if match_res:
            p_data = dict(p)
            p_data['match_score'] = match_res['final_score']
            p_data['skill_score'] = match_res['scores']['skill_score']
            p_data['interest_score'] = match_res['scores']['interest_score']
            p_data['experience_score'] = match_res['scores']['experience_score']
            p_data['availability_score'] = match_res['scores']['availability_score']
            p_data['skill_details'] = match_res['skill_details']
            scored_projects.append(p_data)

    # Sort descending by match_score
    scored_projects.sort(key=lambda x: x['match_score'], reverse=True)
    return scored_projects


def get_project_skill_gaps(project_id):
    """Calculates collective skills of current team members and identifies missing/insufficient skills."""
    project_data = get_project_profile_data(project_id)
    if not project_data:
        return None

    # Get team
    team = fetch_one("SELECT * FROM teams WHERE project_id = %s", (project_id,))
    
    team_members = []
    team_skills = {}

    if team:
        members = fetch_all("""
            SELECT tm.id as tm_id, tm.role, s.id as student_id, u.name, u.email, s.department
            FROM team_members tm
            JOIN students s ON tm.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE tm.team_id = %s
        """, (team['id'],))
        team_members = members

        # Aggregate skills across team: take maximum proficiency
        for m in members:
            stu_skills = fetch_all("""
                SELECT s.name, ss.proficiency_level, ss.certificate_status
                FROM student_skills ss
                JOIN skills s ON ss.skill_id = s.id
                WHERE ss.student_id = %s
            """, (m['student_id'],))
            for sk in stu_skills:
                name = sk['name']
                lvl = sk['proficiency_level']
                if name not in team_skills or lvl > team_skills[name]:
                    team_skills[name] = lvl

    # Run skill gap detection
    gaps = detect_skill_gaps(team_skills, project_data['required_skills'])

    # Format list of all project requirements with status
    skill_breakdown = []
    for skill_name, req_level in project_data['required_skills'].items():
        avail_level = team_skills.get(skill_name, 0)
        if skill_name in gaps:
            status = gaps[skill_name]['status']  # 'Missing' or 'Insufficient'
        else:
            status = 'Covered'
        skill_breakdown.append({
            "skill": skill_name,
            "required_level": req_level,
            "available_level": avail_level,
            "status": status
        })

    return {
        "project": project_data['project'],
        "team": team,
        "team_members": team_members,
        "team_skills": team_skills,
        "gaps": gaps,
        "skill_breakdown": skill_breakdown
    }


def get_teammate_recommendations_for_project(project_id):
    """Recommends students who possess skills to fill missing gaps in the project team."""
    gap_data = get_project_skill_gaps(project_id)
    if not gap_data:
        return []

    gaps = gap_data['gaps']
    if not gaps:
        return []

    # Get current team student names
    current_team_names = [m['name'] for m in gap_data['team_members']]
    
    # Get all students
    all_students_db = fetch_all("""
        SELECT s.id as student_id, u.name, u.email, s.department, s.year, s.availability, s.bio
        FROM students s
        JOIN users u ON s.user_id = u.id
    """)

    students_skill_dict = {}
    students_meta = {}

    for stu in all_students_db:
        stu_name = stu['name']
        skills_rows = fetch_all("""
            SELECT sk.name, ss.proficiency_level, ss.certificate_status, ss.certificate_filename
            FROM student_skills ss
            JOIN skills sk ON ss.skill_id = sk.id
            WHERE ss.student_id = %s
        """, (stu['student_id'],))
        
        students_skill_dict[stu_name] = {row['name']: row['proficiency_level'] for row in skills_rows}
        students_meta[stu_name] = {
            "student_id": stu['student_id'],
            "email": stu['email'],
            "department": stu['department'],
            "year": stu['year'],
            "availability": stu['availability'],
            "bio": stu['bio'],
            "skills": skills_rows
        }

    # Run teammate recommendation algorithm
    recommendations = recommend_teammates(students_skill_dict, current_team_names, gaps)

    # Enrich recommendations with metadata and certificate proof
    enriched = []
    for rec in recommendations:
        name = rec['name']
        meta = students_meta.get(name, {})
        # Find which matching skills have verified certificates
        matching_skills_detailed = []
        for sk_name in rec['matching_skills']:
            for s_row in meta.get('skills', []):
                if s_row['name'] == sk_name:
                    matching_skills_detailed.append({
                        "name": sk_name,
                        "level": s_row['proficiency_level'],
                        "certificate_status": s_row.get('certificate_status', 'None'),
                        "has_certificate": bool(s_row.get('certificate_filename')),
                        "certificate_filename": s_row.get('certificate_filename')
                    })
                    break

        enriched.append({
            "student_id": meta.get('student_id'),
            "name": name,
            "email": meta.get('email'),
            "department": meta.get('department'),
            "year": meta.get('year'),
            "availability": meta.get('availability'),
            "bio": meta.get('bio'),
            "matching_skills": rec['matching_skills'],
            "gaps_filled": rec.get('gaps_filled', len(rec['matching_skills'])),
            "total_proficiency": rec.get('total_proficiency', 0),
            "matching_skills_detailed": matching_skills_detailed
        })

    return enriched
