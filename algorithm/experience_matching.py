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

    if not student_experience:
        return 0

    # Normalize student experience safely
    student_experience_normalized = set()
    for exp in student_experience:
        if exp is not None:
            cleaned = str(exp).strip().lower()
            if cleaned:
                student_experience_normalized.add(cleaned)

    # Normalize project experience safely
    project_experience_normalized = set()
    for exp in project_experience:
        if exp is not None:
            cleaned = str(exp).strip().lower()
            if cleaned:
                project_experience_normalized.add(cleaned)

    if not project_experience_normalized:
        return 0

    # Find common experience areas
    matching_experience = (
        student_experience_normalized
        & project_experience_normalized
    )

    # Calculate percentage
    experience_score = (
        len(matching_experience)
        / len(project_experience_normalized)
    ) * 100.0

    experience_score = max(0.0, min(100.0, experience_score))

    return round(experience_score, 2)


if __name__ == "__main__":
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