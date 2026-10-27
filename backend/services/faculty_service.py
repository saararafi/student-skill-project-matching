
"""
Aggregated data for the faculty console.

Faculty need a cross-project view: which applications are waiting for a
decision, which certificates are awaiting verification, and how their
projects are progressing.
"""

from backend.database import fetch_one, fetch_all


def get_faculty_overview(user_id):
    """Build the faculty console payload for the given faculty user."""

    faculty = fetch_one(
        "SELECT id, name, email, role FROM users WHERE id = %s",
        (user_id,)
    )

    if not faculty:
        return None

    is_admin = str(faculty.get("role", "")).lower() == "admin"

    # Fetch projects owned by this faculty member (or all projects if admin).
    if is_admin:
        projects = fetch_all("""
            SELECT
                p.id,
                p.title,
                p.description,
                p.domain,
                p.status,
                p.team_size,
                p.required_availability,
                p.created_at,

                (
                    SELECT COUNT(*)
                    FROM applications a
                    WHERE a.project_id = p.id
                ) AS application_count,

                (
                    SELECT COUNT(*)
                    FROM applications a
                    WHERE a.project_id = p.id
                      AND a.status = 'Pending'
                ) AS pending_count,

                (
                    SELECT COUNT(*)
                    FROM team_members tm
                    JOIN teams t ON tm.team_id = t.id
                    WHERE t.project_id = p.id
                ) AS member_count

            FROM projects p
            ORDER BY p.created_at DESC
        """)
    else:
        projects = fetch_all("""
            SELECT
                p.id,
                p.title,
                p.description,
                p.domain,
                p.status,
                p.team_size,
                p.required_availability,
                p.created_at,

                (
                    SELECT COUNT(*)
                    FROM applications a
                    WHERE a.project_id = p.id
                ) AS application_count,

                (
                    SELECT COUNT(*)
                    FROM applications a
                    WHERE a.project_id = p.id
                      AND a.status = 'Pending'
                ) AS pending_count,

                (
                    SELECT COUNT(*)
                    FROM team_members tm
                    JOIN teams t ON tm.team_id = t.id
                    WHERE t.project_id = p.id
                ) AS member_count

            FROM projects p
            WHERE p.faculty_id = %s
            ORDER BY p.created_at DESC
        """, (user_id,))

    project_ids = [project["id"] for project in projects]

    if project_ids:
        placeholders = ", ".join(["%s"] * len(project_ids))

        # Fetch applications for these projects.
        applications = fetch_all(f"""
            SELECT
                a.id,
                a.project_id,
                a.status,
                a.message,
                a.match_score,
                a.applied_at,
                a.student_id,
                p.title AS project_title,
                p.domain,
                u.name AS student_name,
                u.email AS student_email,
                s.department,
                s.year

            FROM applications a
            JOIN projects p ON a.project_id = p.id
            JOIN students s ON a.student_id = s.id
            JOIN users u ON s.user_id = u.id

            WHERE a.project_id IN ({placeholders})

            ORDER BY
                CASE a.status
                    WHEN 'Pending' THEN 0
                    ELSE 1
                END,
                a.applied_at DESC
        """, tuple(project_ids))

        # Fetch pending certificates.
        if is_admin:
            pending_certificates = fetch_all("""
                SELECT
                    ss.id,
                    ss.student_id,
                    ss.skill_id,
                    ss.certificate_status,
                    ss.certificate_filename,
                    ss.certificate_original_name,
                    ss.uploaded_at,
                    ss.proficiency_level,
                    sk.name AS skill_name,
                    sk.category,
                    u.name AS student_name,
                    u.email AS student_email

                FROM student_skills ss
                JOIN skills sk ON ss.skill_id = sk.id
                JOIN students s ON ss.student_id = s.id
                JOIN users u ON s.user_id = u.id

                WHERE ss.certificate_status = 'Pending'
                ORDER BY ss.uploaded_at DESC
            """)
        else:
            pending_certificates = fetch_all(f"""
                SELECT
                    ss.id,
                    ss.student_id,
                    ss.skill_id,
                    ss.certificate_status,
                    ss.certificate_filename,
                    ss.certificate_original_name,
                    ss.uploaded_at,
                    ss.proficiency_level,
                    sk.name AS skill_name,
                    sk.category,
                    u.name AS student_name,
                    u.email AS student_email

                FROM student_skills ss
                JOIN skills sk ON ss.skill_id = sk.id
                JOIN students s ON ss.student_id = s.id
                JOIN users u ON s.user_id = u.id

                WHERE ss.certificate_status = 'Pending'
                  AND ss.student_id IN (
                        SELECT DISTINCT a.student_id
                        FROM applications a
                        WHERE a.project_id IN ({placeholders})
                  )

                ORDER BY ss.uploaded_at DESC
            """, tuple(project_ids))

    else:
        applications = []
        if is_admin:
            pending_certificates = fetch_all("""
                SELECT
                    ss.id,
                    ss.student_id,
                    ss.skill_id,
                    ss.certificate_status,
                    ss.certificate_filename,
                    ss.certificate_original_name,
                    ss.uploaded_at,
                    ss.proficiency_level,
                    sk.name AS skill_name,
                    sk.category,
                    u.name AS student_name,
                    u.email AS student_email

                FROM student_skills ss
                JOIN skills sk ON ss.skill_id = sk.id
                JOIN students s ON ss.student_id = s.id
                JOIN users u ON s.user_id = u.id

                WHERE ss.certificate_status = 'Pending'
                ORDER BY ss.uploaded_at DESC
            """)
        else:
            pending_certificates = []

    # Calculate faculty dashboard statistics.
    stats = {
        "projects": len(projects),

        "open_projects": sum(
            1 for project in projects
            if project["status"] == "Open"
        ),

        "applications": len(applications),

        "pending_applications": sum(
            1 for application in applications
            if application["status"] == "Pending"
        ),

        "pending_certificates": len(pending_certificates),
    }

    return {
        "faculty": {
            "id": faculty["id"],
            "name": faculty["name"],
            "email": faculty["email"],
            "role": faculty["role"],
        },
        "stats": stats,
        "projects": projects,
        "applications": applications,
        "pending_certificates": pending_certificates,
    }
