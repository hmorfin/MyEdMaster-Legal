from langgraph.graph import StateGraph, END
from graph.course_state import (
    LessonGenerationState,
    AssessmentGenerationState,
    AssessmentFeedbackState,
)
from graph.course_nodes import (
    lesson_content_node,
    lesson_formatter_node,
    question_generator_node,
    assessment_formatter_node,
    feedback_node,
    feedback_formatter_node,
)


def build_lesson_graph():
    graph = StateGraph(LessonGenerationState)
    graph.add_node("generate_lesson", lesson_content_node)
    graph.add_node("format_lesson", lesson_formatter_node)
    graph.set_entry_point("generate_lesson")
    graph.add_edge("generate_lesson", "format_lesson")
    graph.add_edge("format_lesson", END)
    return graph.compile()


def build_assessment_graph():
    graph = StateGraph(AssessmentGenerationState)
    graph.add_node("generate_assessment", question_generator_node)
    graph.add_node("format_assessment", assessment_formatter_node)
    graph.set_entry_point("generate_assessment")
    graph.add_edge("generate_assessment", "format_assessment")
    graph.add_edge("format_assessment", END)
    return graph.compile()


def build_feedback_graph():
    graph = StateGraph(AssessmentFeedbackState)
    graph.add_node("generate_feedback", feedback_node)
    graph.add_node("format_feedback", feedback_formatter_node)
    graph.set_entry_point("generate_feedback")
    graph.add_edge("generate_feedback", "format_feedback")
    graph.add_edge("format_feedback", END)
    return graph.compile()


lesson_graph = build_lesson_graph()
assessment_graph = build_assessment_graph()
feedback_graph = build_feedback_graph()