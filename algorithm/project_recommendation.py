def recommend_projects(project_scores):
    """
    Sorts projects according to their compatibility scores.

    Parameters:
        project_scores: Dictionary containing project names
                        and their compatibility scores.

    Returns:
        recommendations: Projects sorted from highest
                          score to lowest score.
    """

    # Sort projects by score in descending order
    recommendations = sorted(
        project_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return recommendations


# ---------------------------------------------------------
# SAMPLE PROJECT SCORES
# ---------------------------------------------------------

project_scores = {
    "AI-Based Healthcare System": 84.38,
    "Student Attendance System": 72.50,
    "E-Commerce Website": 91.25,
    "Cybersecurity Monitoring System": 65.75,
    "Smart Campus Management": 80.00
}


# ---------------------------------------------------------
# RUNNING THE ALGORITHM
# ---------------------------------------------------------

recommendations = recommend_projects(project_scores)


# ---------------------------------------------------------
# DISPLAYING RESULTS
# ---------------------------------------------------------

print("\n" + "=" * 75)
print("                   PROJECT RECOMMENDATIONS")
print("=" * 75)

print(
    f"{'Rank':<10}"
    f"{'Project':<45}"
    f"{'Match Score':<15}"
)

print("-" * 75)

for position, (project, score) in enumerate(
    recommendations,
    start=1
):

    print(
        f"{position:<10}"
        f"{project:<45}"
        f"{score}%"
    )

print("=" * 75)