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

    # Normalize input
    student_availability = student_availability.strip().lower()
    project_requirement = project_requirement.strip().lower()

    # Student is not available
    if student_availability == "not available":
        return 0

    # Exact availability match
    if student_availability == project_requirement:
        return 100

    # A full-time student can satisfy a part-time requirement
    if (
        student_availability == "full-time"
        and project_requirement == "part-time"
    ):
        return 100

    # A part-time student partially satisfies a full-time requirement
    if (
        student_availability == "part-time"
        and project_requirement == "full-time"
    ):
        return 50

    # Default
    return 0


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