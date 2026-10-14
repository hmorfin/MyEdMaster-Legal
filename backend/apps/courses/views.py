from django.shortcuts import render

import logging
from datetime import datetime, timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from bson import ObjectId

from apps.users.models import UserProfile
from apps.chat.models import TopicMastery
from .models import Course, Module, Lesson, Enrollment, LessonProgress, Assessment
from ai_client import ai_client, AIServiceError

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────

def _get_user(user_id: str):
    try:
        return UserProfile.objects.get(id=ObjectId(user_id)), None
    except Exception:
        return None, Response(
            {"status": "error", "message": "User not found."},
            status=status.HTTP_404_NOT_FOUND,
        )


def _module_progress(user, module):
    lessons = Lesson.objects.filter(module=module)
    total = lessons.count()
    if total == 0:
        return 0, 0, 0
    completed = LessonProgress.objects.filter(
        user=user,
        lesson__in=lessons,
        completed=True
    ).count()
    return round(completed / total * 100), completed, total


def _course_progress(user, course):
    """Return completion percentage and lesson counts for a course."""
    lessons = Lesson.objects.filter(module__course=course)
    total = lessons.count()
    if total == 0:
        return 0, 0, 0
    completed = LessonProgress.objects.filter(
        user=user,
        lesson__in=lessons,
        completed=True
    ).count()
    return round(completed / total * 100), completed, total


def _is_level_unlocked(user, course):
    """
    Beginner is always unlocked.
    Intermediate requires passing the beginner course assessment.
    Advanced requires passing the intermediate course assessment.
    """
    if course.level == "beginner":
        return True
    prereq_level = "beginner" if course.level == "intermediate" else "intermediate"
    try:
        prereq = Course.objects.get(legal_topic=course.legal_topic, level=prereq_level)
    except Course.DoesNotExist:
        return True
    passed = Assessment.objects.filter(
        user=user,
        course=prereq,
        scope="course",
        passed=True
    ).exists()
    return passed


# ── Course Catalog ────────────────────────────────────────────────────────

@api_view(["GET"])
def list_courses(request):
    """GET /api/v1/courses/?topic=&level="""
    topic = request.query_params.get("topic")
    level = request.query_params.get("level")
    qs = Course.objects.all()

    if topic:
        qs = qs.filter(legal_topic__icontains=topic)
    if level:
        qs = qs.filter(level=level)

    data = []
    for c in qs:
        data.append({
            "course_id": str(c.id),
            "legal_topic": c.legal_topic,
            "level": c.level,
            "title": c.title,
            "description": c.description,
            "module_count": c.modules.count(),
            "pass_threshold": c.pass_threshold,
        })

    return Response({"status": "success", "count": len(data), "data": data})


@api_view(["GET"])
def course_detail(request, course_id):
    """GET /api/v1/courses/:course_id/ — full structure with modules and lessons."""
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response(
            {"status": "error", "message": "Course not found."},
            status=404
        )

    modules = []
    for module in course.modules.all():
        lessons = []
        for lesson in module.lessons.all():
            lessons.append({
                "lesson_id": str(lesson.id),
                "title": lesson.title,
                "order": lesson.order,
                "learning_objectives": lesson.learning_objectives,
                "content_available": bool(lesson.content),
            })
        modules.append({
            "module_id": str(module.id),
            "title": module.title,
            "order": module.order,
            "lessons": lessons,
        })

    return Response({
        "status": "success",
        "data": {
            "course_id": str(course.id),
            "legal_topic": course.legal_topic,
            "level": course.level,
            "title": course.title,
            "description": course.description,
            "pass_threshold": course.pass_threshold,
            "modules": modules,
        }
    })


# ── Enrollment ────────────────────────────────────────────────────────────

@api_view(["POST"])
def enroll(request, course_id, user_id):
    """POST /api/v1/courses/:course_id/enroll/:user_id/"""
    user, err = _get_user(user_id)
    if err:
        return err

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response(
            {"status": "error", "message": "Course not found."},
            status=404
        )

    if not _is_level_unlocked(user, course):
        prereq_level = "beginner" if course.level == "intermediate" else "intermediate"
        return Response({
            "status": "error",
            "message": f"Complete and pass the {prereq_level} {course.legal_topic} course first."
        }, status=status.HTTP_403_FORBIDDEN)

    enrollment, created = Enrollment.objects.get_or_create(
        user=user,
        course=course,
        defaults={"status": "in_progress"}
    )

    return Response({
        "status": "success",
        "data": {
            "enrollment_id": str(enrollment.id),
            "course_id": str(course.id),
            "course_title": course.title,
            "already_enrolled": not created,
            "enrolled_at": enrollment.enrolled_at.isoformat(),
        }
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["GET"])
def enrolled_courses(request, user_id):
    """GET /api/v1/courses/enrolled/:user_id/ — user's courses with progress."""
    user, err = _get_user(user_id)
    if err:
        return err

    enrollments = Enrollment.objects.filter(user=user).select_related("course")
    data = []

    for e in enrollments:
        pct, completed, total = _course_progress(user, e.course)
        data.append({
            "enrollment_id": str(e.id),
            "course_id": str(e.course.id),
            "legal_topic": e.course.legal_topic,
            "level": e.course.level,
            "title": e.course.title,
            "status": e.status,
            "progress_percent": pct,
            "lessons_completed": completed,
            "lessons_total": total,
            "enrolled_at": e.enrolled_at.isoformat(),
        })

    return Response({"status": "success", "count": len(data), "data": data})


# ── Lessons ───────────────────────────────────────────────────────────────

@api_view(["GET"])
def get_lesson(request, lesson_id, user_id):
    """
    GET /api/v1/lessons/:lesson_id/?user_id=
    Returns lesson content. If content is not yet cached, calls the AI service
    to generate it, caches the result, then returns it.
    """
    user, err = _get_user(user_id)
    if err:
        return err

    try:
        lesson = Lesson.objects.select_related("module__course").get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response(
            {"status": "error", "message": "Lesson not found."},
            status=404
        )

    mastery_scores = dict(
        TopicMastery.objects.filter(user=user).values_list("topic", "mastery_level")
    )
    user_attrs = user.user_attributes or {}

    if not lesson.content:
        logger.info(f"Generating content for lesson: {lesson.title}")
        try:
            result = ai_client.generate_lesson(
                lesson_id=str(lesson.id),
                lesson_title=lesson.title,
                module_title=lesson.module.title,
                course_title=lesson.module.course.title,
                legal_topic=lesson.module.course.legal_topic,
                level=lesson.module.course.level,
                learning_objectives=lesson.learning_objectives,
                user_context={
                    "knowledge_level": user_attrs.get("knowledge_level", "beginner"),
                    "jurisdiction": (user.location or {}).get("state", "Federal"),
                    "profession": user_attrs.get("profession", ""),
                    "mastery_scores": mastery_scores,
                }
            )
            lesson.content = result["content"]
            lesson.content_generated_at = datetime.now(timezone.utc)
            lesson.save(update_fields=["content", "content_generated_at"])
        except AIServiceError as e:
            logger.error(f"Lesson generation failed: {e}")
            return Response(
                {"status": "error", "message": "Could not generate lesson content. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    progress = LessonProgress.objects.filter(user=user, lesson=lesson).first()

    return Response({
        "status": "success",
        "data": {
            "lesson_id": str(lesson.id),
            "title": lesson.title,
            "module_title": lesson.module.title,
            "course_title": lesson.module.course.title,
            "legal_topic": lesson.module.course.legal_topic,
            "level": lesson.module.course.level,
            "learning_objectives": lesson.learning_objectives,
            "content": lesson.content,
            "completed": progress.completed if progress else False,
        }
    })


@api_view(["POST"])
def complete_lesson(request, lesson_id, user_id):
    """POST /api/v1/lessons/:lesson_id/complete/:user_id/"""
    user, err = _get_user(user_id)
    if err:
        return err

    try:
        lesson = Lesson.objects.select_related("module__course").get(id=lesson_id)
    except Lesson.DoesNotExist:
        return Response(
            {"status": "error", "message": "Lesson not found."},
            status=404
        )

    progress, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    if not progress.completed:
        progress.completed = True
        progress.completed_at = datetime.now(timezone.utc)
        progress.save()

    course = lesson.module.course
    pct, completed, total = _course_progress(user, course)

    if pct == 100:
        Enrollment.objects.filter(user=user, course=course).update(
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )

    return Response({
        "status": "success",
        "data": {
            "lesson_id": str(lesson.id),
            "completed": True,
            "course_progress": pct,
        }
    })


# ── Assessments ───────────────────────────────────────────────────────────

@api_view(["POST"])
def generate_assessment(request, user_id):
    """
    POST /api/v1/assessments/generate/:user_id/
    Body: { scope: "lesson"|"module"|"course", target_id: "<id>" }
    Generates MCQ questions via AI service and saves an Assessment record.
    """
    user, err = _get_user(user_id)
    if err:
        return err

    scope = request.data.get("scope")
    target_id = request.data.get("target_id")

    if scope not in ("lesson", "module", "course"):
        return Response(
            {"status": "error", "message": "scope must be lesson, module, or course."},
            status=400
        )

    lesson_obj = module_obj = course_obj = None
    legal_topic = level = title = ""
    content_summary = ""

    if scope == "lesson":
        try:
            lesson_obj = Lesson.objects.select_related("module__course").get(id=target_id)
        except Lesson.DoesNotExist:
            return Response(
                {"status": "error", "message": "Lesson not found."},
                status=404
            )

        module_obj = lesson_obj.module
        course_obj = module_obj.course
        legal_topic = course_obj.legal_topic
        level = course_obj.level
        title = lesson_obj.title
        content_summary = lesson_obj.content[:3000] if lesson_obj.content else ""
        question_count = 5

    elif scope == "module":
        try:
            module_obj = Module.objects.select_related("course").get(id=target_id)
        except Module.DoesNotExist:
            return Response(
                {"status": "error", "message": "Module not found."},
                status=404
            )

        course_obj = module_obj.course
        legal_topic = course_obj.legal_topic
        level = course_obj.level
        title = module_obj.title
        content_summary = " | ".join(l.title for l in module_obj.lessons.all())
        question_count = 8

    elif scope == "course":
        try:
            course_obj = Course.objects.get(id=target_id)
        except Course.DoesNotExist:
            return Response(
                {"status": "error", "message": "Course not found."},
                status=404
            )

        legal_topic = course_obj.legal_topic
        level = course_obj.level
        title = course_obj.title
        content_summary = " | ".join(m.title for m in course_obj.modules.all())
        question_count = 12

    mastery_scores = dict(
        TopicMastery.objects.filter(user=user).values_list("topic", "mastery_level")
    )
    user_mastery = mastery_scores.get(legal_topic, 0.1)

    try:
        result = ai_client.generate_assessment(
            legal_topic=legal_topic,
            level=level,
            scope=scope,
            title=title,
            content_summary=content_summary,
            question_count=question_count,
            user_mastery=user_mastery,
        )
        questions = result["questions"]
    except AIServiceError as e:
        logger.error(f"Assessment generation failed: {e}")
        return Response(
            {"status": "error", "message": "Could not generate assessment. Please try again."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    assessment = Assessment.objects.create(
        user=user,
        lesson=lesson_obj,
        module=module_obj,
        course=course_obj,
        scope=scope,
        questions=questions,
    )

    safe_questions = [
        {
            "index": i,
            "question": q["question"],
            "options": q["options"],
        }
        for i, q in enumerate(questions)
    ]

    return Response({
        "status": "success",
        "data": {
            "assessment_id": str(assessment.id),
            "scope": scope,
            "title": title,
            "questions": safe_questions,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def submit_assessment(request, user_id, assessment_id):
    """
    POST /api/v1/assessments/:assessment_id/submit/:user_id/
    Body: { answers: { "0": 2, "1": 0, "2": 3, ... } }
    Scores the submission, updates mastery, and returns full feedback.
    """
    user, err = _get_user(user_id)
    if err:
        return err

    try:
        assessment = Assessment.objects.select_related(
            "lesson__module__course", "module__course", "course"
        ).get(id=assessment_id, user=user)
    except Assessment.DoesNotExist:
        return Response(
            {"status": "error", "message": "Assessment not found."},
            status=404
        )

    if assessment.submitted_at:
        return Response(
            {"status": "error", "message": "Assessment already submitted."},
            status=409,
        )

    answers = request.data.get("answers", {})
    if not isinstance(answers, dict):
        return Response(
            {"status": "error", "message": "answers must be an object of question indexes to option indexes."},
            status=400,
        )

    try:
        # Keep keys as strings for MongoDB; cast values to ints for scoring.
        user_answers = {str(k): int(v) for k, v in answers.items()}
    except (TypeError, ValueError):
        return Response(
            {"status": "error", "message": "All answer keys and values must be valid integers."},
            status=400,
        )

    questions = assessment.questions
    correct = 0
    results = []

    for i, q in enumerate(questions):
        chosen = user_answers.get(str(i))
        is_correct = chosen == q["correct_index"]
        if is_correct:
            correct += 1

        results.append({
            "index": i,
            "question": q["question"],
            "options": q["options"],
            "user_answer": chosen,
            "correct_answer": q["correct_index"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    score = round(correct / len(questions), 4) if questions else 0.0

    course_obj = assessment.course or (
        assessment.module.course if assessment.module else
        assessment.lesson.module.course if assessment.lesson else None
    )
    pass_threshold = course_obj.pass_threshold if course_obj else 0.70
    passed = score >= pass_threshold
    legal_topic = course_obj.legal_topic if course_obj else ""

    if not passed:
        next_action = "retry"
    elif assessment.scope == "lesson":
        next_action = "next_lesson"
    elif assessment.scope == "module":
        next_action = "next_module"
    else:
        next_action = "unlock_next_level"

    try:
        feedback_result = ai_client.generate_assessment_feedback(
            legal_topic=legal_topic,
            score=score,
            passed=passed,
            results=results,
            next_action=next_action,
        )
        feedback = feedback_result.get("feedback", "")
    except AIServiceError:
        feedback = (
            f"You scored {round(score * 100)}%. "
            f"{'Well done!' if passed else 'Review the material and try again.'}"
        )

    assessment.user_answers = user_answers
    assessment.score = score
    assessment.passed = passed
    assessment.feedback = feedback
    assessment.next_action = next_action
    assessment.submitted_at = datetime.now(timezone.utc)
    assessment.save()

    if legal_topic:
        mastery, _ = TopicMastery.objects.get_or_create(
            user=user,
            topic=legal_topic,
            defaults={"mastery_level": 0.1}
        )
        new_score = round(min(1.0, mastery.mastery_level * 0.6 + score * 0.4), 4)
        mastery.mastery_level = new_score
        mastery.save()
        logger.info(f"Mastery updated for {legal_topic}: {new_score} (score={score})")

    return Response({
        "status": "success",
        "data": {
            "assessment_id": str(assessment.id),
            "score": round(score * 100, 1),
            "passed": passed,
            "correct": correct,
            "total": len(questions),
            "next_action": next_action,
            "feedback": feedback,
            "results": results,
        }
    })


@api_view(["GET"])
def assessment_history(request, user_id):
    """GET /api/v1/assessments/history/:user_id/"""
    user, err = _get_user(user_id)
    if err:
        return err

    assessments = Assessment.objects.filter(
        user=user,
        submitted_at__isnull=False
    ).order_by("-submitted_at")

    data = []
    for a in assessments:
        data.append({
            "assessment_id": str(a.id),
            "scope": a.scope,
            "score": round((a.score or 0) * 100, 1),
            "passed": a.passed,
            "next_action": a.next_action,
            "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
        })

    return Response({"status": "success", "count": len(data), "data": data})


@api_view(["GET"])
def learning_progress(request, user_id):
    """GET /api/v1/progress/:user_id/ — full learning dashboard."""
    user, err = _get_user(user_id)
    if err:
        return err

    enrollments = Enrollment.objects.filter(user=user).select_related("course")
    mastery_scores = dict(
        TopicMastery.objects.filter(user=user).values_list("topic", "mastery_level")
    )

    topics = {}
    for e in enrollments:
        topic = e.course.legal_topic
        if topic not in topics:
            topics[topic] = {
                "legal_topic": topic,
                "mastery_score": mastery_scores.get(topic, 0.0),
                "courses": [],
            }

        pct, completed, total = _course_progress(user, e.course)
        topics[topic]["courses"].append({
            "course_id": str(e.course.id),
            "level": e.course.level,
            "title": e.course.title,
            "status": e.status,
            "progress_percent": pct,
            "lessons_completed": completed,
            "lessons_total": total,
        })

    return Response({
        "status": "success",
        "data": {
            "user_id": user_id,
            "topics": list(topics.values()),
        }
    })


@api_view(["GET"])
def module_progress(request, course_id, user_id):
    user, err = _get_user(user_id)
    if err:
        return err

    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return Response(
            {"status": "error", "message": "Course not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    modules = []
    for module in course.modules.all():
        pct, completed, total = _module_progress(user, module)
        assessment_passed = Assessment.objects.filter(
            user=user,
            module=module,
            scope="module",
            passed=True,
        ).exists()
        modules.append({
            "module_id": str(module.id),
            "title": module.title,
            "order": module.order,
            "lessons_total": total,
            "lessons_completed": completed,
            "progress_percent": pct,
            "assessment_passed": assessment_passed,
        })

    return Response({
        "status": "success",
        "data": {
            "course_id": str(course.id),
            "course_title": course.title,
            "user_id": user_id,
            "modules": modules,
        }
    })