def calculate_weighted_match(
    skill_score,
    interest_score,
    experience_score,
    availability_score
):
    """
    Calculates the final weighted compatibility score.

    Weights:
        Skill        = 50%
        Interest     = 20%
        Experience   = 20%
        Availability = 10%

    Returns:
        final_score: Overall weighted compatibility percentage
    """

    # Define weights
    skill_weight = 0.50
    interest_weight = 0.20
    experience_weight = 0.20
    availability_weight = 0.10

    # Calculate weighted contributions
    skill_contribution = skill_score * skill_weight
    interest_contribution = interest_score * interest_weight
    experience_contribution = experience_score * experience_weight
    availability_contribution = availability_score * availability_weight

    # Calculate final score
    final_score = (
        skill_contribution
        + interest_contribution
        + experience_contribution
        + availability_contribution
    )

    return round(final_score, 2)


# ---------------------------------------------------------
# SAMPLE SCORES
# ---------------------------------------------------------

skill_score = 88.75
interest_score = 50
experience_score = 100
availability_score = 100


# ---------------------------------------------------------
# RUNNING THE ALGORITHM
# ---------------------------------------------------------

final_score = calculate_weighted_match(
    skill_score,
    interest_score,
    experience_score,
    availability_score
)


# ---------------------------------------------------------
# DISPLAYING RESULTS
# ---------------------------------------------------------

print("\n" + "=" * 80)
print("                     WEIGHTED MATCHING")
print("=" * 80)

print(
    f"{'Attribute':<25}"
    f"{'Score':<15}"
    f"{'Weight':<15}"
    f"{'Contribution':<20}"
)

print("-" * 80)

print(
    f"{'Skill Compatibility':<25}"
    f"{skill_score:<15}%"
    f"{'50%':<15}"
    f"{skill_score * 0.50:<20.2f}"
)

print(
    f"{'Interest Compatibility':<25}"
    f"{interest_score:<15}%"
    f"{'20%':<15}"
    f"{interest_score * 0.20:<20.2f}"
)

print(
    f"{'Experience Compatibility':<25}"
    f"{experience_score:<15}%"
    f"{'20%':<15}"
    f"{experience_score * 0.20:<20.2f}"
)

print(
    f"{'Availability':<25}"
    f"{availability_score:<15}%"
    f"{'10%':<15}"
    f"{availability_score * 0.10:<20.2f}"
)

print("-" * 80)

print(
    f"{'FINAL MATCH SCORE':<60}"
    f"{final_score}%"
)

print("=" * 80)