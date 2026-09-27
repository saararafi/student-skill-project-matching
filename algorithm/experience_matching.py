def calculate_experience_match(student_experience, project_experience):
    """
    Calculates compatibility between a student's previous
    experience and a project's desired experience areas.

    Returns:
        experience_score: Experience compatibility percentage
    """

    # If the project has no experience requirements
    if not project_experience:
        return 0

    # Normalize student experience
    student_experience_normalized = {
        experience.strip().lower()
        for experience in student_experience
    }

    # Normalize project experience
    project_experience_normalized = {
        experience.strip().lower()
        for experience in project_experience
    }

    # Find common experience areas
    matching_experience = (
        student_experience_normalized
        & project_experience_normalized
    )

    # Calculate percentage
    experience_score = (
        len(matching_experience)
        / len(project_experience_normalized)
    ) * 100

    return round(experience_score, 2)


# ---------------------------------------------------------
# SAMPLE STUDENT DATA
# ---------------------------------------------------------

student_experience = [
    "Web Development",
    "Python Projects",
    "Database Projects"
]


# ---------------------------------------------------------
# SAMPLE PROJECT DATA
# ---------------------------------------------------------

project_experience = [
    "Web Development",
    "Python Projects",
    "Machine Learning"
]


# ---------------------------------------------------------
# RUNNING THE ALGORITHM
# ---------------------------------------------------------

experience_score = calculate_experience_match(
    student_experience,
    project_experience
)


# Normalize for displaying matches
student_normalized = {
    experience.strip().lower()
    for experience in student_experience
}


# ---------------------------------------------------------
# DISPLAYING RESULTS
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("                 EXPERIENCE COMPATIBILITY")
print("=" * 70)

print(
    f"{'Required Experience':<40}"
    f"{'Match':<15}"
    f"{'Status':<15}"
)

print("-" * 70)

for experience in project_experience:

    if experience.strip().lower() in student_normalized:
        match = "Yes"
        status = "Matched"
    else:
        match = "No"
        status = "Not Matched"

    print(
        f"{experience:<40}"
        f"{match:<15}"
        f"{status:<15}"
    )

print("-" * 70)

print(
    f"{'Experience Match Score':<55}"
    f"{experience_score}%"
)

print("=" * 70)