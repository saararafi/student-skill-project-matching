"""
Unit tests for the rule-based matching algorithms.

Run with:
    python -m unittest discover -s tests -v

The algorithms are pure functions with no database dependency, so they can be
tested independently of the Flask application.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from algorithm.matching import calculate_skill_match
from algorithm.interest_matching import calculate_interest_match
from algorithm.experience_matching import calculate_experience_match
from algorithm.availability_matching import calculate_availability_match
from algorithm.weighted_matching import calculate_weighted_match
from algorithm.project_recommendation import recommend_projects
from algorithm.skill_gap import detect_skill_gaps
from algorithm.teammate_recommendation import recommend_teammates


class TestSkillMatching(unittest.TestCase):

    def test_exact_match_scores_100(self):
        score, breakdown = calculate_skill_match(
            {"Python": 4, "Java": 3},
            {"Python": 4, "Java": 3}
        )
        self.assertEqual(score, 100)
        self.assertEqual(breakdown, {"Python": 100.0, "Java": 100.0})

    def test_overqualified_skill_is_capped_at_100(self):
        score, breakdown = calculate_skill_match(
            {"Python": 5},
            {"Python": 3}
        )
        self.assertEqual(breakdown["Python"], 100.0)
        self.assertEqual(score, 100)

    def test_partial_proficiency_is_proportional(self):
        score, breakdown = calculate_skill_match(
            {"Python": 2},
            {"Python": 4}
        )
        self.assertEqual(breakdown["Python"], 50.0)
        self.assertEqual(score, 50.0)

    def test_missing_skill_scores_zero(self):
        score, breakdown = calculate_skill_match(
            {"Python": 5},
            {"Python": 5, "React": 4}
        )
        self.assertEqual(breakdown["React"], 0)
        self.assertEqual(score, 50.0)

    def test_empty_requirements_return_zero(self):
        score, breakdown = calculate_skill_match({"Python": 5}, {})
        self.assertEqual(score, 0)
        self.assertEqual(breakdown, {})

    def test_score_is_average_across_skills(self):
        score, _ = calculate_skill_match(
            {"Python": 4, "Java": 2, "HTML": 5},
            {"Python": 4, "Java": 4, "HTML": 5}
        )
        # (100 + 50 + 100) / 3 = 83.33
        self.assertAlmostEqual(score, 83.33, places=2)


class TestInterestMatching(unittest.TestCase):

    def test_full_overlap(self):
        score = calculate_interest_match(
            ["AI", "Web Development"],
            ["AI", "Web Development"]
        )
        self.assertEqual(score, 100)

    def test_partial_overlap(self):
        score = calculate_interest_match(
            ["AI", "Web Development"],
            ["AI", "Mobile Development"]
        )
        self.assertEqual(score, 50)

    def test_is_case_and_whitespace_insensitive(self):
        score = calculate_interest_match(
            ["  artificial intelligence "],
            ["Artificial Intelligence"]
        )
        self.assertEqual(score, 100)

    def test_no_overlap(self):
        score = calculate_interest_match(["AI"], ["Blockchain"])
        self.assertEqual(score, 0)

    def test_empty_project_interests(self):
        score = calculate_interest_match(["AI"], [])
        self.assertEqual(score, 0)


class TestExperienceMatching(unittest.TestCase):

    def test_full_overlap(self):
        score = calculate_experience_match(
            ["Web Development", "Python Projects"],
            ["Web Development", "Python Projects"]
        )
        self.assertEqual(score, 100)

    def test_partial_overlap(self):
        score = calculate_experience_match(
            ["Web Development", "Python Projects"],
            ["Web Development", "Machine Learning"]
        )
        self.assertEqual(score, 50)

    def test_no_overlap(self):
        score = calculate_experience_match(["C++ Systems"], ["Web Development"])
        self.assertEqual(score, 0)

    def test_empty_project_experiences(self):
        score = calculate_experience_match(["Web Development"], [])
        self.assertEqual(score, 0)


class TestAvailabilityMatching(unittest.TestCase):

    def test_full_time_on_full_time(self):
        self.assertEqual(calculate_availability_match("Full-time", "Full-time"), 100)

    def test_full_time_covers_part_time(self):
        self.assertEqual(calculate_availability_match("Full-time", "Part-time"), 100)

    def test_part_time_on_full_time_is_half(self):
        self.assertEqual(calculate_availability_match("Part-time", "Full-time"), 50)

    def test_part_time_on_part_time(self):
        self.assertEqual(calculate_availability_match("Part-time", "Part-time"), 100)

    def test_not_available_scores_zero(self):
        self.assertEqual(calculate_availability_match("Not available", "Full-time"), 0)
        self.assertEqual(calculate_availability_match("Not available", "Part-time"), 0)

    def test_case_insensitive(self):
        self.assertEqual(calculate_availability_match("full-time", "FULL-TIME"), 100)


class TestWeightedMatching(unittest.TestCase):

    def test_known_weighted_result(self):
        # 88.75*0.5 + 50*0.2 + 100*0.2 + 100*0.1
        # = 44.375 + 10 + 20 + 10 = 84.375 -> 84.38
        self.assertEqual(
            calculate_weighted_match(88.75, 50, 100, 100),
            84.38
        )

    def test_all_perfect_is_100(self):
        self.assertEqual(calculate_weighted_match(100, 100, 100, 100), 100)

    def test_all_zero_is_zero(self):
        self.assertEqual(calculate_weighted_match(0, 0, 0, 0), 0)

    def test_weights_sum_to_one(self):
        # If the weights did not sum to 1.0 this would not equal the input.
        self.assertEqual(calculate_weighted_match(80, 80, 80, 80), 80)

    def test_skill_dominates_other_factors(self):
        # Skill carries a 50% weight, more than any other single factor.
        high_skill = calculate_weighted_match(100, 0, 0, 0)   # 50
        high_interest = calculate_weighted_match(0, 100, 0, 0)  # 20
        high_experience = calculate_weighted_match(0, 0, 100, 0)  # 20
        high_availability = calculate_weighted_match(0, 0, 0, 100)  # 10
        self.assertGreater(high_skill, high_interest)
        self.assertGreater(high_skill, high_experience)
        self.assertGreater(high_skill, high_availability)

    def test_weights_sum_to_one(self):
        # If the weights did not sum to 1.0 this would not equal the input.
        self.assertEqual(calculate_weighted_match(80, 80, 80, 80), 80)

    def test_skill_and_other_factors_tie_at_fifty(self):
        # Sanity check on the published weights: 50% vs (20+20+10)% = 50%.
        self.assertEqual(calculate_weighted_match(100, 0, 0, 0), 50.0)
        self.assertEqual(calculate_weighted_match(0, 100, 100, 100), 50.0)

    def test_custom_weights_are_normalised(self):
        # Only the skill factor is enabled, so it carries the whole score.
        weights = {
            "skill": 0.5, "interest": 0, "experience": 0, "availability": 0
        }
        self.assertEqual(calculate_weighted_match(80, 0, 0, 0, weights=weights), 80.0)

    def test_disabled_factor_is_ignored(self):
        weights = {
            "skill": 0.5, "interest": 0, "experience": 0.2, "availability": 0.1
        }
        # skill 80 * 0.625 + experience 100 * 0.25 + availability 100 * 0.125
        expected = round(80 * 0.625 + 100 * 0.25 + 100 * 0.125, 2)
        self.assertEqual(
            calculate_weighted_match(80, 0, 100, 100, weights=weights),
            expected
        )

    def test_unnormalised_weights_are_scaled_to_one(self):
        # Weights that do not add up to 1.0 are normalised before use.
        weights = {
            "skill": 2, "interest": 1, "experience": 1, "availability": 1
        }
        self.assertEqual(calculate_weighted_match(100, 100, 100, 100, weights=weights), 100.0)

    def test_all_weights_zero_falls_back_safely(self):
        weights = {
            "skill": 0, "interest": 0, "experience": 0, "availability": 0
        }
        self.assertEqual(calculate_weighted_match(100, 100, 100, 100, weights=weights), 100.0)


class TestProjectRecommendation(unittest.TestCase):

    def test_sorted_descending(self):
        ranked = recommend_projects({
            "A": 60.0,
            "B": 90.0,
            "C": 75.0
        })
        self.assertEqual([name for name, _ in ranked], ["B", "C", "A"])

    def test_empty_input(self):
        self.assertEqual(recommend_projects({}), [])


class TestSkillGap(unittest.TestCase):

    def test_missing_skill_detected(self):
        gaps = detect_skill_gaps(
            {"Python": 4},
            {"Python": 4, "React": 3}
        )
        self.assertIn("React", gaps)
        self.assertEqual(gaps["React"]["status"], "Missing")
        self.assertEqual(gaps["React"]["available_level"], 0)

    def test_insufficient_skill_detected(self):
        gaps = detect_skill_gaps(
            {"Python": 2},
            {"Python": 4}
        )
        self.assertEqual(gaps["Python"]["status"], "Insufficient")
        self.assertEqual(gaps["Python"]["available_level"], 2)

    def test_covered_skill_not_reported(self):
        gaps = detect_skill_gaps(
            {"Python": 5},
            {"Python": 4}
        )
        self.assertEqual(gaps, {})

    def test_exact_level_is_covered(self):
        gaps = detect_skill_gaps({"Python": 4}, {"Python": 4})
        self.assertEqual(gaps, {})


class TestTeammateRecommendation(unittest.TestCase):

    def setUp(self):
        self.gaps = {
            "JavaScript": {"required_level": 3, "available_level": 0, "status": "Missing"},
            "Flask": {"required_level": 3, "available_level": 0, "status": "Missing"}
        }
        self.students = {
            "Aisha": {"Python": 4, "JavaScript": 4, "HTML": 5},
            "Rahul": {"Java": 4, "Flask": 3, "MySQL": 4},
            "Meera": {"JavaScript": 5, "React": 4, "CSS": 5},
            "Arjun": {"C++": 5, "Java": 4}
        }

    def test_recommends_students_with_gap_skills(self):
        recs = recommend_teammates(self.students, ["Arjun"], self.gaps)
        names = [r["name"] for r in recs]
        self.assertIn("Aisha", names)
        self.assertIn("Rahul", names)
        self.assertIn("Meera", names)

    def test_excludes_current_team_members(self):
        recs = recommend_teammates(self.students, ["Aisha", "Rahul", "Meera", "Arjun"], self.gaps)
        self.assertEqual(recs, [])

    def test_ignores_students_without_gap_skills(self):
        recs = recommend_teammates(self.students, [], self.gaps)
        self.assertNotIn("Arjun", [r["name"] for r in recs])

    def test_proficiency_below_requirement_does_not_count(self):
        # "Junior" knows JavaScript but only at level 1, below the required 3.
        students = {"Junior": {"JavaScript": 1, "Flask": 1}}
        recs = recommend_teammates(students, [], self.gaps)
        self.assertEqual(recs, [])

    def test_proficiency_at_requirement_counts(self):
        students = {"Exact": {"JavaScript": 3}}
        recs = recommend_teammates(students, [], self.gaps)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["matching_skills"], ["JavaScript"])

    def test_ranked_by_gaps_filled(self):
        recs = recommend_teammates(self.students, [], self.gaps)
        # All three close exactly one gap, so the stronger proficiency wins:
        # Meera (JavaScript 5) > Aisha (JavaScript 4).
        self.assertEqual(recs[0]["name"], "Meera")
        self.assertEqual(recs[0]["gaps_filled"], 1)
        counts = [r["gaps_filled"] for r in recs]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_more_gaps_filled_ranks_higher(self):
        students = {
            "Focused": {"JavaScript": 4},
            "Broad": {"JavaScript": 4, "Flask": 4}
        }
        recs = recommend_teammates(students, [], self.gaps)
        self.assertEqual(recs[0]["name"], "Broad")
        self.assertEqual(recs[0]["gaps_filled"], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
