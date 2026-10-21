def recommend_teammates(
    students,
    current_team,
    skill_gaps
):
    """
    Recommends students who possess skills missing
    from the current project team.

    A student is only credited with a gap when their proficiency for that
    skill actually reaches the level the project requires; merely owning the
    skill is not enough to close the gap.

    Parameters:
        students:
            Dictionary containing student names and skills.

        current_team:
            List of students already in the team.

        skill_gaps:
            Dictionary containing missing/insufficient skills.

    Returns:
        recommendations:
            List of students who have skills required
            by the project, best match first.
    """

    recommendations = []

    if not isinstance(students, dict) or not students:
        return recommendations

    if not isinstance(skill_gaps, dict) or not skill_gaps:
        return recommendations

    if not current_team:
        current_team = []

    team_set = {str(x).strip().lower() for x in current_team if x is not None}

    # Map normalized skill name -> (original_skill, required_level)
    normalized_gaps = {}
    for skill, gap_info in skill_gaps.items():
        if skill is None:
            continue
        req_lvl = 1.0
        if isinstance(gap_info, dict):
            try:
                req_lvl = float(gap_info.get('required_level', 1))
            except (TypeError, ValueError):
                req_lvl = 1.0
        normalized_gaps[str(skill).strip().lower()] = (str(skill), req_lvl)

    # Check every student
    for student_name, student_skills in students.items():
        if student_name is None:
            continue

        # Do not recommend students already in the team
        if str(student_name).strip().lower() in team_set or student_name in current_team:
            continue

        if not isinstance(student_skills, dict):
            continue

        # Find skills that match the gaps at a sufficient proficiency
        matching_skills = []
        total_level = 0.0

        for skill, level in student_skills.items():
            if skill is None:
                continue
            norm_k = str(skill).strip().lower()
            if norm_k not in normalized_gaps:
                continue

            orig_skill_name, required_level = normalized_gaps[norm_k]

            try:
                stu_lvl = float(level)
            except (TypeError, ValueError):
                stu_lvl = 0.0

            # The student's proficiency must meet the required level
            if stu_lvl >= required_level:
                matching_skills.append(orig_skill_name)
                total_level += stu_lvl

        # If the student has useful skills, recommend them
        if matching_skills:
            recommendations.append({
                "name": student_name,
                "matching_skills": matching_skills,
                "gaps_filled": len(matching_skills),
                "total_proficiency": round(total_level, 2)
            })

    # Best candidates first: most gaps closed, then strongest proficiency
    recommendations.sort(
        key=lambda r: (r['gaps_filled'], r['total_proficiency']),
        reverse=True
    )

    return recommendations


if __name__ == "__main__":
    # ---------------------------------------------------------
    # SAMPLE STUDENT DATA
    # ---------------------------------------------------------

    students = {

        "Aisha": {
            "Python": 4,
            "JavaScript": 4,
            "HTML": 5
        },

        "Rahul": {
            "Java": 4,
            "Flask": 3,
            "MySQL": 4
        },

        "Meera": {
            "JavaScript": 5,
            "React": 4,
            "CSS": 5
        },

        "Arjun": {
            "C++": 5,
            "Java": 4
        }
    }

    # ---------------------------------------------------------
    # CURRENT TEAM
    # ---------------------------------------------------------

    current_team = [
        "Arjun"
    ]

    # ---------------------------------------------------------
    # SAMPLE SKILL GAPS
    # ---------------------------------------------------------

    skill_gaps = {

        "JavaScript": {
            "required_level": 3,
            "available_level": 0,
            "status": "Missing"
        },

        "Flask": {
            "required_level": 3,
            "available_level": 0,
            "status": "Missing"
        }
    }

    # ---------------------------------------------------------
    # RUNNING THE ALGORITHM
    # ---------------------------------------------------------

    recommendations = recommend_teammates(
        students,
        current_team,
        skill_gaps
    )

    # ---------------------------------------------------------
    # DISPLAYING RESULTS
    # ---------------------------------------------------------

    print("\n" + "=" * 75)
    print("                  TEAMMATE RECOMMENDATIONS")
    print("=" * 75)

    print(
        f"{'Student':<25}"
        f"{'Matching Skills':<45}"
    )

    print("-" * 75)

    if recommendations:

        for student in recommendations:

            skills = ", ".join(
                student["matching_skills"]
            )

            print(
                f"{student['name']:<25}"
                f"{skills:<45}"
            )

    else:

        print("No suitable teammates found.")

    print("=" * 75)