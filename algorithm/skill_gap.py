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

    # Check every project requirement
    for skill, required_level in project_requirements.items():

        # If the team does not have the skill
        if skill not in team_skills:

            skill_gaps[skill] = {
                "required_level": required_level,
                "available_level": 0,
                "status": "Missing"
            }

        # If the team has the skill but not enough proficiency
        elif team_skills[skill] < required_level:

            skill_gaps[skill] = {
                "required_level": required_level,
                "available_level": team_skills[skill],
                "status": "Insufficient"
            }

    return skill_gaps


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