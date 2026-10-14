# ai/graph/test_clarification_node.py
import json
import pytest
from unittest.mock import patch, MagicMock
from graph.nodes import clarification_node


# helper to build a minimal state dict for testing
def build_state(query, history=None, has_document=False):
    return {
        "user_id": "test_user",
        "query": query,
        "anon_query": query,
        "anon_document": "some document text here" if has_document else "",
        "conversation_history": history or [],
        "document_paths": [],
        "document_text": "",
        "document_urls": [],
        "knowledge_chunks": [],
        "anon_knowledge": [],
        "user_context": {},
        "primary_topic": None,
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": None,
        "llm_response": "",
        "final_answer": "",
        "detected_topic": None,
        "confidence_delta": None,
        "error": None,
        "chat_id": "test_chat",
    }


def fake_llm_response(data):
    m = MagicMock()
    m.content = json.dumps(data)
    return m


# if user already uploaded a doc we skip clarification entirely
def test_no_clarification_when_doc_is_attached():
    state = build_state("what does this say?", has_document=True)
    result = clarification_node(state)
    assert result["needs_clarification"] == False
    assert result["clarification_options"] is None


# vague question with no context should trigger clarification with options
@patch("graph.nodes.ChatOpenAI")
def test_vague_question_triggers_mcq(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response({
        "ready_to_answer": False,
        "plain_question": "Are you a tenant or landlord?",
        "question": {
            "question": "Are you a tenant or landlord?",
            "type": "single_select",
            "options": ["Tenant", "Landlord"]
        }
    })

    result = clarification_node(build_state("can they do that?"))

    assert result["needs_clarification"] == True
    assert result["clarification_question"] == "Are you a tenant or landlord?"
    assert result["clarification_options"][0]["type"] == "single_select"
    assert "Tenant" in result["clarification_options"][0]["options"]


# urgent situation like a court date should go straight to answering
@patch("graph.nodes.ChatOpenAI")
def test_urgent_query_skips_clarification(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response({
        "ready_to_answer": True,
        "plain_question": None,
        "question": None
    })

    result = clarification_node(build_state("I have a court date tomorrow what do I do?"))

    assert result["needs_clarification"] == False
    assert result["clarification_options"] is None


# after user answers first question llm should ask the next logical one
@patch("graph.nodes.ChatOpenAI")
def test_follows_up_after_first_answer(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response({
        "ready_to_answer": False,
        "plain_question": "What is the issue you are facing?",
        "question": {
            "question": "What is the issue you are facing?",
            "type": "multi_select",
            "options": ["Eviction", "Unpaid Rent", "Repairs", "Harassment", "Other"]
        }
    })

    history = [
        {"role": "user", "content": "can they do that?"},
        {"role": "llm", "content": "Are you a tenant or landlord?"}
    ]
    result = clarification_node(build_state("I am a tenant", history=history))

    assert result["needs_clarification"] == True
    assert result["clarification_options"][0]["type"] == "multi_select"
    assert "Eviction" in result["clarification_options"][0]["options"]


# if llm crashes we should not crash the whole pipeline
@patch("graph.nodes.ChatOpenAI")
def test_handles_llm_failure_gracefully(mock_llm_class):
    mock_llm_class.return_value.invoke.side_effect = Exception("connection timeout")

    result = clarification_node(build_state("what are my rights?"))

    assert result["needs_clarification"] == False
    assert result["clarification_question"] is None
    assert result["clarification_options"] is None


# free text questions should come back with empty options list not null
@patch("graph.nodes.ChatOpenAI")
def test_free_text_has_empty_options(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response({
        "ready_to_answer": False,
        "plain_question": "Which state did this happen in?",
        "question": {
            "question": "Which state did this happen in?",
            "type": "free_text",
            "options": []
        }
    })

    result = clarification_node(build_state("my landlord is harassing me"))

    assert result["needs_clarification"] == True
    assert result["clarification_options"][0]["type"] == "free_text"
    assert result["clarification_options"][0]["options"] == []