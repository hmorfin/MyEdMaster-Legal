from typing import TypedDict


class LessonGenerationState(TypedDict):
    # Input
    lesson_id:            str
    lesson_title:         str
    module_title:         str
    course_title:         str
    legal_topic:          str
    level:                str          # beginner | intermediate | advanced
    learning_objectives:  list[str]
    user_context:         dict         # knowledge_level, jurisdiction, profession, mastery_scores

    # Output
    content:              str          # LLM-generated markdown lesson
    key_terms:            list[dict]   
    error:                str | None


class AssessmentGenerationState(TypedDict):
    # Input
    legal_topic:          str
    level:                str
    scope:                str          # lesson | module | course
    title:                str
    content_summary:      str
    question_count:       int
    user_mastery:         float        

    # Output
    questions:            list[dict]   
    error:                str | None


class AssessmentFeedbackState(TypedDict):
    # Input
    legal_topic:          str
    score:                float
    passed:               bool
    results:              list[dict]   
    next_action:          str

    # Output
    feedback:             str
    error:                str | None