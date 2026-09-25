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
    if not project_requirements:
        return 0, skill_scores

    for skill, required_level in project_requirements.items():

        # Checking whether the student has the required skill
        if skill in student_skills:

            student_level = student_skills[skill]

            # Calculating compatibility percentage
            score = (student_level / required_level) * 100

            # Not allowing a skill score above 100%
            score = min(score, 100)

        else:

            # Student does not have the required skill
            score = 0

        skill_scores[skill] = round(score, 2)

    # Calculating the average of all skill scores
    overall_score = sum(skill_scores.values()) / len(skill_scores)

    return round(overall_score, 2), skill_scores


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