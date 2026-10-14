# graph/lesson_nodes.py

import json
import logging
import time

from langchain_openai import ChatOpenAI
from langsmith import traceable

from config import settings
from graph.tutoring_prompts import (
    LEVEL_DESCRIPTIONS,
    LEVEL_DEPTH,
    LESSON_CONTENT_SYSTEM_PROMPT,
    LESSON_CONTENT_USER_PROMPT,
    QUESTION_GENERATOR_SYSTEM_PROMPT,
    QUESTION_GENERATOR_USER_PROMPT,
    FEEDBACK_ACTION_MAP,
    FEEDBACK_SYSTEM_PROMPT,
    FEEDBACK_USER_PROMPT,
)

logger = logging.getLogger(__name__)


def _llm():
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.4,
    )


# ---------------------------------------------------------------------------
# Lesson Generation Nodes
# ---------------------------------------------------------------------------

@traceable
def lesson_content_node(state) -> dict:
    start = time.time()
    llm = _llm()
    level = state["level"]
    topic = state["legal_topic"]
    mastery = state["user_context"].get("mastery_scores", {}).get(topic, 0.1)
    jurisdiction = state["user_context"].get("jurisdiction", "Federal")
    profession = state["user_context"].get("profession", "")

    if mastery < 0.3:
        mastery_guidance = "Start from first principles."
    elif mastery < 0.7:
        mastery_guidance = "Build on existing knowledge."
    else:
        mastery_guidance = "Challenge assumptions and add nuance."

    objectives_text = "\n".join(f"- {o}" for o in state["learning_objectives"])

    system_prompt = LESSON_CONTENT_SYSTEM_PROMPT.format(
        level_description=LEVEL_DESCRIPTIONS[level],
        level_depth=LEVEL_DEPTH[level],
        mastery=mastery,
        mastery_guidance=mastery_guidance,
        jurisdiction=jurisdiction,
        profession_suffix=f" | Profession: {profession}" if profession else "",
    )

    user_message = LESSON_CONTENT_USER_PROMPT.format(
        course_title=state["course_title"],
        level=level,
        module_title=state["module_title"],
        lesson_title=state["lesson_title"],
        topic=topic,
        objectives_text=objectives_text,
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        logger.info(
            "lesson_content_generated",
            extra={
                "legal_topic": topic,
                "level": level,
                "content_length": len(parsed["content"]),
                "key_terms_count": len(parsed.get("key_terms", [])),
                "duration_ms": round((time.time() - start) * 1000, 1),
            },
        )
        return {
            "content": parsed["content"],
            "key_terms": parsed.get("key_terms", []),
        }
    except Exception as e:
        logger.error(
            "lesson_content_generation_failed",
            exc_info=True,
            extra={"legal_topic": topic, "level": level},
        )
        return {
            "content": "",
            "key_terms": [],
            "error": f"Lesson generation failed: {str(e)}",
        }


# ---------------------------------------------------------------------------
# Assessment Generation Nodes
# ---------------------------------------------------------------------------

@traceable
def question_generator_node(state) -> dict:
    start = time.time()
    llm = _llm()
    mastery = state["user_mastery"]
    level = state["level"]
    n = state["question_count"]

    if mastery < 0.3:
        difficulty = "straightforward recall and basic comprehension questions"
    elif mastery < 0.6:
        difficulty = "application questions requiring the student to apply concepts to scenarios"
    else:
        difficulty = "analysis and evaluation questions requiring nuanced judgment and distinguishing between similar concepts"

    system_prompt = QUESTION_GENERATOR_SYSTEM_PROMPT.format(
        legal_topic=state["legal_topic"],
        level=level,
        scope=state["scope"],
        title=state["title"],
        difficulty=difficulty,
        mastery=mastery,
        n=n,
    )

    user_message = QUESTION_GENERATOR_USER_PROMPT.format(
        n=n,
        content_summary=state["content_summary"],
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())
        questions = parsed["questions"]
        logger.info(
            "assessment_questions_generated",
            extra={
                "legal_topic": state["legal_topic"],
                "level": level,
                "questions_count": len(questions),
                "duration_ms": round((time.time() - start) * 1000, 1),
            },
        )
        return {"questions": questions}
    except Exception as e:
        logger.error(
            "assessment_question_generation_failed",
            exc_info=True,
            extra={"legal_topic": state["legal_topic"], "level": level},
        )
        return {
            "questions": [],
            "error": f"Question generation failed: {str(e)}",
        }


# ---------------------------------------------------------------------------
# Assessment Feedback Node
# ---------------------------------------------------------------------------

@traceable
def feedback_node(state) -> dict:
    llm = _llm()
    score_pct = round(state["score"] * 100)
    passed = state["passed"]
    next_action = state["next_action"]

    wrong = [r for r in state["results"] if not r["is_correct"]]
    wrong_summary = (
        "\n".join(
            f"- Q: {r['question'][:100]}... | Correct: {r['options'][r['correct_answer']]}"
            for r in wrong[:5]
        )
        if wrong else "None — perfect score!"
    )

    action_guidance = FEEDBACK_ACTION_MAP.get(next_action, "encourage them to continue learning")

    system_prompt = FEEDBACK_SYSTEM_PROMPT.format(action_guidance=action_guidance)

    user_message = FEEDBACK_USER_PROMPT.format(
        legal_topic=state["legal_topic"],
        score_pct=score_pct,
        passed_label="PASSED" if passed else "NOT PASSED",
        wrong_summary=wrong_summary,
    )

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ])
        feedback = response.content.strip()
        logger.info(
            "assessment_feedback_generated",
            extra={
                "legal_topic": state["legal_topic"],
                "passed": passed,
                "score_pct": score_pct,
                "feedback_length": len(feedback),
            },
        )
        return {"feedback": feedback}
    except Exception as e:
        logger.error(
            "assessment_feedback_generation_failed",
            exc_info=True,
            extra={"legal_topic": state["legal_topic"], "passed": passed},
        )
        fallback = (
            f"You scored {score_pct}%. "
            + ("Great work — you passed!" if passed else "Review the topics you missed and try again.")
        )
        return {"feedback": fallback, "error": f"Feedback generation failed: {str(e)}"}


# ---------------------------------------------------------------------------
# Formatter Nodes
# ---------------------------------------------------------------------------

def lesson_formatter_node(state) -> dict:
    if state.get("error"):
        return {"content": "", "key_terms": [], "error": state["error"]}

    content = state.get("content", "").strip()
    if not content:
        return {"content": "", "key_terms": [], "error": "Lesson generation returned empty content"}

    if len(content) < 100:
        logger.warning("lesson_content_unusually_short", extra={"content_length": len(content)})

    raw_terms = state.get("key_terms", [])
    key_terms = [
        t for t in raw_terms
        if isinstance(t, dict) and "term" in t and "definition" in t
        and t["term"].strip() and t["definition"].strip()
    ]

    if not key_terms:
        logger.warning("lesson_no_valid_key_terms")

    logger.info(
        "lesson_formatter_completed",
        extra={"content_length": len(content), "key_terms_count": len(key_terms)},
    )
    return {"content": content, "key_terms": key_terms, "error": None}


def assessment_formatter_node(state) -> dict:
    if state.get("error"):
        return {"questions": [], "error": state["error"]}

    questions = state.get("questions", [])
    if not questions:
        return {"questions": [], "error": "Assessment generation returned no questions"}

    valid_questions = [
        q for q in questions
        if isinstance(q, dict)
        and "question" in q
        and "options" in q
        and "correct_index" in q
        and "explanation" in q
        and len(q["options"]) == 4
        and isinstance(q["correct_index"], int)
        and 0 <= q["correct_index"] <= 3
    ]

    if not valid_questions:
        logger.warning(
            "assessment_no_valid_questions",
            extra={"questions_returned_by_llm": len(questions)},
        )
        return {"questions": [], "error": "No valid questions after validation"}

    logger.info(
        "assessment_formatter_completed",
        extra={"valid_questions": len(valid_questions), "total_questions": len(questions)},
    )
    return {"questions": valid_questions, "error": None}


def feedback_formatter_node(state) -> dict:
    if state.get("error") and not state.get("feedback"):
        return {"feedback": "We encountered an issue generating feedback. Please try again.", "error": state["error"]}

    feedback = state.get("feedback", "").strip()
    if not feedback:
        logger.warning("feedback_formatter_empty_feedback")
        return {"feedback": "Thank you for completing the assessment. Keep practicing!", "error": None}

    logger.info("feedback_formatter_completed", extra={"feedback_length": len(feedback)})
    return {"feedback": feedback, "error": None}