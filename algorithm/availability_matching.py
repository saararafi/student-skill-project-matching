def calculate_availability_match(
    student_availability,
    project_requirement
):
    """
    Calculates compatibility between a student's availability
    and the project's availability requirement.

    Availability options:
        - Full-time
        - Part-time
        - Not available

    Returns:
        score: Availability compatibility percentage
    """

    if student_availability is None or project_requirement is None:
        return 0

    # Normalize input safely
    s_avail = str(student_availability).strip().lower().replace(" ", "-")
    p_req = str(project_requirement).strip().lower().replace(" ", "-")

    # Student is not available
    if s_avail in ("not-available", "not available", "none", "0", ""):
        return 0

    # Exact availability match
    if s_avail == p_req:
        return 100

    # A full-time student can satisfy a part-time requirement
    if s_avail == "full-time" and p_req == "part-time":
        return 100

    # A part-time student partially satisfies a full-time requirement
    if s_avail == "part-time" and p_req == "full-time":
        return 50

    # Default
    return 0


if __name__ == "__main__":
    # ---------------------------------------------------------
    # SAMPLE DATA
    # ---------------------------------------------------------

    student_availability = "Full-time"
    project_requirement = "Part-time"

    # ---------------------------------------------------------
    # RUNNING THE ALGORITHM
    # ---------------------------------------------------------

    availability_score = calculate_availability_match(
        student_availability,
        project_requirement
    )

    # ---------------------------------------------------------
    # DISPLAYING RESULTS
    # ---------------------------------------------------------

    print("\n" + "=" * 65)
    print("                AVAILABILITY COMPATIBILITY")
    print("=" * 65)

    print(
        f"{'Category':<30}"
        f"{'Value':<25}"
    )

    print("-" * 65)

    print(
        f"{'Student Availability':<30}"
        f"{student_availability:<25}"
    )

    print(
        f"{'Project Requirement':<30}"
        f"{project_requirement:<25}"
    )

    print("-" * 65)

    print(
        f"{'Compatibility Score':<50}"
        f"{availability_score}%"
    )

    print("=" * 65)