import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from graph.course_builder import lesson_graph, assessment_graph, feedback_graph

logger = logging.getLogger(__name__)
router = APIRouter()



class LessonRequest(BaseModel):
    lesson_id:           str
    lesson_title:        str
    module_title:        str
    course_title:        str
    legal_topic:         str
    level:               str
    learning_objectives: list[str]
    user_context:        dict


class LessonResponse(BaseModel):
    lesson_id:  str
    content:    str
    key_terms:  list[dict]


class AssessmentRequest(BaseModel):
    legal_topic:     str
    level:           str
    scope:           str
    title:           str
    content_summary: str
    question_count:  int = 5
    user_mastery:    float = 0.1


class AssessmentResponse(BaseModel):
    questions: list[dict]


class FeedbackRequest(BaseModel):
    legal_topic: str
    score:       float
    passed:      bool
    results:     list[dict]
    next_action: str


class FeedbackResponse(BaseModel):
    feedback: str



@router.post("/lessons/generate", response_model=LessonResponse)
def generate_lesson(request: LessonRequest):
    initial_state = {
        "lesson_id":           request.lesson_id,
        "lesson_title":        request.lesson_title,
        "module_title":        request.module_title,
        "course_title":        request.course_title,
        "legal_topic":         request.legal_topic,
        "level":               request.level,
        "learning_objectives": request.learning_objectives,
        "user_context":        request.user_context,
        "content":             "",
        "key_terms":           [],
        "error":               None,
    }
    logger.info(
        "lesson_generation_requested",
        extra={"lesson_id": request.lesson_id, "legal_topic": request.legal_topic, "level": request.level},
    )
    try:
        result = lesson_graph.invoke(initial_state)
    except Exception as e:
        logger.error("lesson_generation_graph_failed", exc_info=True, extra={"lesson_id": request.lesson_id})
        raise HTTPException(status_code=500, detail=f"Lesson generation failed: {str(e)}")

    if result.get("error") or not result.get("content"):
        logger.warning(
            "lesson_generation_empty_result",
            extra={"lesson_id": request.lesson_id, "error": result.get("error")},
        )
        raise HTTPException(status_code=500, detail=result.get("error", "Empty lesson content returned."))

    return LessonResponse(
        lesson_id=request.lesson_id,
        content=result["content"],
        key_terms=result.get("key_terms", []),
    )


@router.post("/assessments/generate", response_model=AssessmentResponse)
def generate_assessment(request: AssessmentRequest):
    initial_state = {
        "legal_topic":     request.legal_topic,
        "level":           request.level,
        "scope":           request.scope,
        "title":           request.title,
        "content_summary": request.content_summary,
        "question_count":  request.question_count,
        "user_mastery":    request.user_mastery,
        "questions":       [],
        "error":           None,
    }
    logger.info(
        "assessment_generation_requested",
        extra={"legal_topic": request.legal_topic, "level": request.level, "question_count": request.question_count},
    )
    try:
        result = assessment_graph.invoke(initial_state)
    except Exception as e:
        logger.error("assessment_generation_graph_failed", exc_info=True, extra={"legal_topic": request.legal_topic})
        raise HTTPException(status_code=500, detail=f"Assessment generation failed: {str(e)}")

    if result.get("error") or not result.get("questions"):
        logger.warning(
            "assessment_generation_empty_result",
            extra={"legal_topic": request.legal_topic, "error": result.get("error")},
        )
        raise HTTPException(status_code=500, detail=result.get("error", "No questions generated."))

    return AssessmentResponse(questions=result["questions"])


@router.post("/assessments/feedback", response_model=FeedbackResponse)
def generate_feedback(request: FeedbackRequest):
    initial_state = {
        "legal_topic": request.legal_topic,
        "score":       request.score,
        "passed":      request.passed,
        "results":     request.results,
        "next_action": request.next_action,
        "feedback":    "",
        "error":       None,
    }
    logger.info(
        "assessment_feedback_requested",
        extra={"legal_topic": request.legal_topic, "passed": request.passed, "score": request.score},
    )
    try:
        result = feedback_graph.invoke(initial_state)
    except Exception as e:
        logger.error("assessment_feedback_graph_failed", exc_info=True, extra={"legal_topic": request.legal_topic})
        raise HTTPException(status_code=500, detail=f"Feedback generation failed: {str(e)}")

    return FeedbackResponse(feedback=result.get("feedback", ""))