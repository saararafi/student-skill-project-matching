"""
Tests for the matching algorithm modules.

Run with:  pytest tests/ -v

Why tests matter for your demo: if someone (maybe you) accidentally
changes the scoring logic, these tests fail loudly instead of your
demo showing wrong numbers to the evaluator.

Each test documents the expected behavior — they double as examples
of how to call the functions.
"""

import os
import sys

# Make the algorithm package importable no matter where pytest runs from
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "algorithm"))

from matching import calculate_skill_match
from skill_gap import detect_skill_gaps
from teammate_recommendation import recommend_teammates
from weighted_matching import calculate_weighted_match


# ---------- SKILL MATCHING ----------

def test_skill_match_ratio():
    """Student Python 4 vs required 5 → 80%"""
    score, per_skill = calculate_skill_match(
        {"Python": 4}, {"Python": 5}
    )
    assert score == 80.0
    assert per_skill["Python"] == 80.0


def test_skill_match_capped_at_100():
    """Student level 5 vs required 3 must not exceed 100%"""
    score, _ = calculate_skill_match({"Python": 5}, {"Python": 3})
    assert score == 100


def test_missing_skill_scores_zero():
    """A skill the student lacks contributes 0 to the average"""
    score, per_skill = calculate_skill_match(
        {"Python": 5}, {"Python": 5, "Flask": 4}
    )
    assert per_skill["Flask"] == 0
    assert score == 50.0  # average of 100 and 0


def test_empty_requirements():
    score, per_skill = calculate_skill_match({"Python": 5}, {})
    assert score == 0
    assert per_skill == {}


# ---------- WEIGHTED MATCHING ----------

def test_weighted_match_math():
    """50/20/20/10 weights applied correctly"""
    final = calculate_weighted_match(
        skill_score=80, interest_score=50,
        experience_score=100, availability_score=100
    )
    assert final == round(80 * 0.5 + 50 * 0.2 + 100 * 0.2 + 100 * 0.1, 2)
    assert final == 80.0


def test_weighted_match_max_is_100():
    final = calculate_weighted_match(100, 100, 100, 100)
    assert final == 100.0


# ---------- SKILL GAPS ----------

def test_detect_missing_skill():
    gaps = detect_skill_gaps(
        team_skills={"Python": 5},
        project_requirements={"Python": 5, "Flask": 3},
    )
    assert gaps["Flask"]["status"] == "Missing"
    assert gaps["Flask"]["available_level"] == 0


def test_detect_insufficient_skill():
    gaps = detect_skill_gaps(
        team_skills={"SQL": 2},
        project_requirements={"SQL": 4},
    )
    assert gaps["SQL"]["status"] == "Insufficient"
    assert gaps["SQL"]["available_level"] == 2


def test_no_gaps_when_team_covers_all():
    gaps = detect_skill_gaps(
        team_skills={"Python": 5, "SQL": 4},
        project_requirements={"Python": 4, "SQL": 4},
    )
    assert gaps == {}


# ---------- TEAMMATE RECOMMENDATIONS ----------

def test_teammates_excludes_current_team():
    students = {
        "Aisha": {"Python": 4},
        "Arjun": {"Python": 4},
    }
    recommendations = recommend_teammates(
        students, current_team=["Arjun"], skill_gaps={"Python": {"required_level": 3}}
    )
    names = [r["name"] for r in recommendations]
    assert "Arjun" not in names
    assert "Aisha" in names


def test_teammates_only_fill_gaps():
    """Students without any gap skill are not recommended"""
    students = {
        "Aisha": {"C++": 5},       # C++ is not a gap
        "Rahul": {"Flask": 4},    # Flask IS the gap
    }
    recommendations = recommend_teammates(
        students, current_team=[], skill_gaps={"Flask": {"required_level": 3}}
    )
    names = [r["name"] for r in recommendations]
    assert names == ["Rahul"]
