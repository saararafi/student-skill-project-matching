def recommend_teammates(
    students,
    current_team,
    skill_gaps
):
    """
    Recommends students who possess skills missing
    from the current project team.

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
            by the project.
    """

    recommendations = []

    # Get the skills required to fill the gaps
    required_skills = set(skill_gaps.keys())

    # Check every student
    for student_name, student_skills in students.items():

        # Do not recommend students already in the team
        if student_name in current_team:
            continue

        # Find skills that match the gaps
        matching_skills = []

        for skill in student_skills:

            if skill in required_skills:
                matching_skills.append(skill)

        # If the student has useful skills, recommend them
        if matching_skills:

            recommendations.append({
                "name": student_name,
                "matching_skills": matching_skills
            })

    return recommendations


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