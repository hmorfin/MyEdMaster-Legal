from graph.tutoring_graph.course_nodes import (
    lesson_formatter_node,
    assessment_formatter_node,
    feedback_formatter_node,
)


# ─────────────────────────────────────────────
# lesson_formatter_node tests
# ─────────────────────────────────────────────

def test_lesson_formatter_returns_clean_content():
    state = {
        "content": "  ## Overview\nThis is a lesson about tenant rights.  ",
        "key_terms": [{"term": "Lease", "definition": "A rental agreement"}],
        "error": None,
    }
    result = lesson_formatter_node(state)
    assert result["content"] == "## Overview\nThis is a lesson about tenant rights."
    assert len(result["key_terms"]) == 1
    assert result["error"] is None


def test_lesson_formatter_passes_through_on_error():
    state = {"content": "", "key_terms": [], "error": "Lesson generation failed"}
    result = lesson_formatter_node(state)
    assert result["content"] == ""
    assert result["key_terms"] == []
    assert result["error"] == "Lesson generation failed"


def test_lesson_formatter_catches_empty_content():
    state = {"content": "   ", "key_terms": [], "error": None}
    result = lesson_formatter_node(state)
    assert result["content"] == ""
    assert "empty" in result["error"].lower()


def test_lesson_formatter_removes_invalid_key_terms():
    state = {
        "content": "Valid lesson content here",
        "key_terms": [
            {"term": "Lease", "definition": "A rental agreement"},
            {"term": "Missing definition"},
            {"definition": "Missing term"},
            "not a dict",
        ],
        "error": None,
    }
    result = lesson_formatter_node(state)
    assert len(result["key_terms"]) == 1
    assert result["key_terms"][0]["term"] == "Lease"


def test_lesson_formatter_handles_empty_key_terms():
    state = {"content": "Valid lesson content here", "key_terms": [], "error": None}
    result = lesson_formatter_node(state)
    assert result["key_terms"] == []
    assert result["error"] is None


# ─────────────────────────────────────────────
# assessment_formatter_node tests
# ─────────────────────────────────────────────

def test_assessment_formatter_returns_valid_questions():
    state = {
        "questions": [
            {
                "question": "What is a lease?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "explanation": "A lease is a rental agreement.",
            }
        ],
        "error": None,
    }
    result = assessment_formatter_node(state)
    assert len(result["questions"]) == 1
    assert result["error"] is None


def test_assessment_formatter_passes_through_on_error():
    state = {"questions": [], "error": "Question generation failed"}
    result = assessment_formatter_node(state)
    assert result["questions"] == []
    assert result["error"] == "Question generation failed"


def test_assessment_formatter_removes_invalid_questions():
    state = {
        "questions": [
            {
                "question": "Valid question?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 1,
                "explanation": "Because B is correct.",
            },
            {
                "question": "Missing options",
                "correct_index": 0,
                "explanation": "No options field",
            },
            {
                "question": "Wrong option count",
                "options": ["A", "B"],
                "correct_index": 0,
                "explanation": "Should have 4 options",
            },
        ],
        "error": None,
    }
    result = assessment_formatter_node(state)
    assert len(result["questions"]) == 1


def test_assessment_formatter_catches_empty_questions():
    state = {"questions": [], "error": None}
    result = assessment_formatter_node(state)
    assert result["questions"] == []
    assert result["error"] is not None


def test_assessment_formatter_rejects_out_of_range_correct_index():
    state = {
        "questions": [
            {
                "question": "Valid question?",
                "options": ["A", "B", "C", "D"],
                "correct_index": 5,
                "explanation": "Index out of range",
            }
        ],
        "error": None,
    }
    result = assessment_formatter_node(state)
    assert len(result["questions"]) == 0


# ─────────────────────────────────────────────
# feedback_formatter_node tests
# ─────────────────────────────────────────────

def test_feedback_formatter_returns_clean_feedback():
    state = {"feedback": "  Great job! You passed the assessment.  ", "error": None}
    result = feedback_formatter_node(state)
    assert result["feedback"] == "Great job! You passed the assessment."
    assert result["error"] is None


def test_feedback_formatter_uses_fallback_on_error_with_no_feedback():
    state = {"feedback": "", "error": "LLM timeout"}
    result = feedback_formatter_node(state)
    assert "issue" in result["feedback"].lower()
    assert result["error"] == "LLM timeout"


def test_feedback_formatter_uses_fallback_on_empty_feedback():
    state = {"feedback": "   ", "error": None}
    result = feedback_formatter_node(state)
    assert len(result["feedback"]) > 0
    assert result["error"] is None


def test_feedback_formatter_returns_feedback_even_with_error_if_feedback_exists():
    state = {"feedback": "You scored 80%. Well done!", "error": "minor issue"}
    result = feedback_formatter_node(state)
    assert result["feedback"] == "You scored 80%. Well done!"