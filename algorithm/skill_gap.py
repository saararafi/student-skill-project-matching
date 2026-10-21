def detect_skill_gaps(team_skills, project_requirements):
    """
    Identifies missing or insufficient skills in a team.

    team_skills:
        Dictionary containing the team's available
        skill levels.

    project_requirements:
        Dictionary containing required skill levels.

    Returns:
        skill_gaps: Dictionary containing missing or
                    insufficient skills.
    """

    skill_gaps = {}

    if not isinstance(project_requirements, dict) or not project_requirements:
        return skill_gaps

    if not isinstance(team_skills, dict):
        team_skills = {}

    # Case-insensitive map of team skills: normalized_name -> available_level
    norm_team = {}
    for sk, lvl in team_skills.items():
        if sk is not None:
            try:
                num = float(lvl)
            except (TypeError, ValueError):
                num = 0.0
            k = str(sk).strip().lower()
            if k not in norm_team or num > norm_team[k]:
                norm_team[k] = num

    # Check every project requirement
    for skill, required_level in project_requirements.items():
        if skill is None:
            continue

        try:
            req_lvl = float(required_level)
        except (TypeError, ValueError):
            req_lvl = 1.0

        norm_k = str(skill).strip().lower()

        # If the team does not have the skill
        if norm_k not in norm_team:
            skill_gaps[skill] = {
                "required_level": req_lvl,
                "available_level": 0,
                "status": "Missing"
            }
        # If the team has the skill but not enough proficiency
        elif norm_team[norm_k] < req_lvl:
            skill_gaps[skill] = {
                "required_level": req_lvl,
                "available_level": norm_team[norm_k],
                "status": "Insufficient"
            }

    return skill_gaps


if __name__ == "__main__":
    # ---------------------------------------------------------
    # SAMPLE TEAM DATA
    # ---------------------------------------------------------

    team_skills = {
        "Python": 5,
        "HTML": 5,
        "CSS": 4,
        "MySQL": 2
    }

    # ---------------------------------------------------------
    # SAMPLE PROJECT REQUIREMENTS
    # ---------------------------------------------------------

    project_requirements = {
        "Python": 5,
        "HTML": 4,
        "CSS": 4,
        "MySQL": 4,
        "JavaScript": 3,
        "Flask": 3
    }

    # ---------------------------------------------------------
    # RUNNING THE ALGORITHM
    # ---------------------------------------------------------

    gaps = detect_skill_gaps(
        team_skills,
        project_requirements
    )

    # ---------------------------------------------------------
    # DISPLAYING RESULTS
    # ---------------------------------------------------------

    print("\n" + "=" * 80)
    print("                    PROJECT SKILL GAP ANALYSIS")
    print("=" * 80)

    print(
        f"{'Skill':<25}"
        f"{'Required':<15}"
        f"{'Available':<15}"
        f"{'Status':<20}"
    )

    print("-" * 80)

    if gaps:

        for skill, details in gaps.items():

            print(
                f"{skill:<25}"
                f"{details['required_level']:<15}"
                f"{details['available_level']:<15}"
                f"{details['status']:<20}"
            )

    else:

        print(
            f"{'No skill gaps detected.':<80}"
        )

    print("=" * 80)