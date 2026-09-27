def calculate_interest_match(student_interests, project_interests):
    """
    Calculates compatibility between a student's interests
    and a project's required/interested areas.

    Returns:
        interest_score: Interest compatibility percentage
    """

    # If the project has no interests
    if not project_interests:
        return 0

    # Convert interests to lowercase for comparison
    student_interests_normalized = {
        interest.strip().lower()
        for interest in student_interests
    }

    project_interests_normalized = {
        interest.strip().lower()
        for interest in project_interests
    }

    # Find common interests
    matching_interests = (
        student_interests_normalized
        & project_interests_normalized
    )

    # Calculate percentage
    interest_score = (
        len(matching_interests)
        / len(project_interests_normalized)
    ) * 100

    return round(interest_score, 2)


# ---------------------------------------------------------
# SAMPLE STUDENT DATA
# ---------------------------------------------------------

student_interests = [
    "Artificial Intelligence",
    "Web Development",
    "Cybersecurity",
    "Data Science"
]


# ---------------------------------------------------------
# SAMPLE PROJECT DATA
# ---------------------------------------------------------

project_interests = [
    "Artificial Intelligence",
    "Web Development",
    "Mobile Development"
]


# ---------------------------------------------------------
# RUNNING THE ALGORITHM
# ---------------------------------------------------------

interest_score = calculate_interest_match(
    student_interests,
    project_interests
)


# Find matching interests for display
student_normalized = {
    interest.strip().lower()
    for interest in student_interests
}


# ---------------------------------------------------------
# DISPLAYING RESULTS
# ---------------------------------------------------------

print("\n" + "=" * 65)
print("                INTEREST COMPATIBILITY")
print("=" * 65)

print(
    f"{'Project Interest':<35}"
    f"{'Match':<15}"
    f"{'Status':<15}"
)

print("-" * 65)

for interest in project_interests:

    if interest.strip().lower() in student_normalized:
        match = "Yes"
        status = "Matched"
    else:
        match = "No"
        status = "Not Matched"

    print(
        f"{interest:<35}"
        f"{match:<15}"
        f"{status:<15}"
    )

print("-" * 65)

print(
    f"{'Interest Match Score':<50}"
    f"{interest_score}%"
)

print("=" * 65)