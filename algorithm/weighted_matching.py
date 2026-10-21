import math


def _clean_score(val):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return max(0.0, min(100.0, f))
    except (TypeError, ValueError):
        return 0.0


def _clean_weight(val, default):
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f) or f < 0:
            return 0.0
        return f
    except (TypeError, ValueError):
        return default


def calculate_weighted_match(
    skill_score,
    interest_score,
    experience_score,
    availability_score,
    weights=None
):
    """
    Calculates the final weighted compatibility score.

    Weights:
        Skill        = 50%
        Interest     = 20%
        Experience   = 20%
        Availability = 10%

    Parameters:
        weights: Optional override of the four factor weights, given as a
                 mapping with the keys 'skill', 'interest', 'experience' and
                 'availability'. The weights are normalised so they always
                 add up to 1.0, which is what happens when a student turns
                 one of the matching factors off in their settings.

    Returns:
        final_score: Overall weighted compatibility percentage
    """

    # Clean and validate input scores
    skill_score = _clean_score(skill_score)
    interest_score = _clean_score(interest_score)
    experience_score = _clean_score(experience_score)
    availability_score = _clean_score(availability_score)

    # Define weights
    if not isinstance(weights, dict):
        weights = {
            "skill": 0.50,
            "interest": 0.20,
            "experience": 0.20,
            "availability": 0.10
        }

    skill_weight = _clean_weight(weights.get("skill"), 0.50)
    interest_weight = _clean_weight(weights.get("interest"), 0.20)
    experience_weight = _clean_weight(weights.get("experience"), 0.20)
    availability_weight = _clean_weight(weights.get("availability"), 0.10)

    # Normalise so the weights always add up to 1.0
    total_weight = skill_weight + interest_weight + experience_weight + availability_weight
    if total_weight > 0:
        skill_weight /= total_weight
        interest_weight /= total_weight
        experience_weight /= total_weight
        availability_weight /= total_weight
    else:
        # Every factor was switched off: fall back to the standard weights.
        skill_weight, interest_weight = 0.50, 0.20
        experience_weight, availability_weight = 0.20, 0.10

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

    final_score = max(0.0, min(100.0, final_score))

    return round(final_score, 2)


if __name__ == "__main__":
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