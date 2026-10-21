def calculate_skill_match(student_skills, project_requirements):
    """
    Calculates the compatibility between a student's skills
    and a project's required skills.

    Student proficiency and required proficiency are assumed
    to be on a scale of 1 to 5.

    Returns:
        overall_score: Overall compatibility percentage
        skill_scores: Individual score for each required skill
    """

    skill_scores = {}

    # If the project has no skill requirements
    if not isinstance(project_requirements, dict) or not project_requirements:
        return 0, skill_scores

    if not isinstance(student_skills, dict):
        student_skills = {}

    # Normalize student skills case-insensitively and clamp proficiency [0, 5]
    normalized_student = {}
    for s_name, s_lvl in student_skills.items():
        if s_name is None:
            continue
        try:
            val = float(s_lvl)
        except (TypeError, ValueError):
            val = 0.0
        val = max(0.0, min(5.0, val))
        k = str(s_name).strip().lower()
        if k not in normalized_student or val > normalized_student[k]:
            normalized_student[k] = val

    for skill, required_level in project_requirements.items():
        if skill is None:
            continue

        try:
            req_lvl = float(required_level)
        except (TypeError, ValueError):
            req_lvl = 1.0

        # Protect against division by zero and negative levels
        if req_lvl <= 0:
            req_lvl = 1.0
        else:
            req_lvl = min(5.0, req_lvl)

        norm_k = str(skill).strip().lower()

        # Checking whether the student has the required skill
        if norm_k in normalized_student:
            student_level = normalized_student[norm_k]

            # Calculating compatibility percentage
            score = (student_level / req_lvl) * 100.0

            # Not allowing a skill score above 100% or below 0%
            score = max(0.0, min(score, 100.0))
        else:
            # Student does not have the required skill
            score = 0.0

        skill_scores[skill] = round(score, 2)

    if not skill_scores:
        return 0, skill_scores

    # Calculating the average of all skill scores
    overall_score = sum(skill_scores.values()) / len(skill_scores)

    return round(overall_score, 2), skill_scores


if __name__ == "__main__":
    # Sample Student Data
    student_skills = {
        "Python": 4,
        "Java": 3,
        "HTML": 5,
        "MySQL": 3
    }


    # Sample Project Requirements
    project_requirements = {
        "Python": 5,
        "Java": 3,
        "HTML": 4,
        "MySQL": 4
    }


    # Running the Matching Algorithm
    overall_score, skill_scores = calculate_skill_match(
        student_skills,
        project_requirements
    )


    # Displaying Results
    print("======================================")
    print("   STUDENT-PROJECT SKILL MATCHING")
    print("======================================")

    print("\nIndividual Skill Scores:")
    print("--------------------------------------")

    for skill, score in skill_scores.items():
        print(f"{skill:<10} : {score}%")

    print("--------------------------------------")
    print(f"Overall Match Score : {overall_score}%")
    print("======================================")