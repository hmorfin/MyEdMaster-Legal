import pytest
from unittest.mock import patch, MagicMock
from graph.nodes import run_summarization


def fake_llm_response(text):
    m = MagicMock()
    m.content = text
    return m


# basic summarization returns a non-empty string
@patch("graph.nodes.ChatOpenAI")
def test_basic_summarization_returns_string(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response(
        "User was involved in a car accident in Texas as the driver. Passenger was injured."
    )

    messages = [
        {"role": "user", "content": "I got into a car accident last week"},
        {"role": "llm", "content": "Are you the driver or passenger?"},
        {"role": "user", "content": "I was the driver"},
        {"role": "llm", "content": "Was anyone injured?"},
        {"role": "user", "content": "Yes my passenger got hurt"},
    ]

    result = run_summarization(messages)
    assert isinstance(result, str)
    assert len(result) > 0


# existing summary should be included in the prompt
@patch("graph.nodes.ChatOpenAI")
def test_existing_summary_is_included(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response(
        "Updated summary including previous context."
    )

    messages = [
        {"role": "user", "content": "The accident was on a highway"},
        {"role": "llm", "content": "Was it a multi-car accident?"},
    ]

    existing = "User was in a car accident in Texas as the driver. Passenger was injured."
    result = run_summarization(messages, existing_summary=existing)

    # check that the LLM was called with the existing summary in the prompt
    call_args = mock_llm_class.return_value.invoke.call_args
    prompt_text = call_args[0][0][0]["content"]
    assert "PREVIOUS SUMMARY" in prompt_text
    assert existing in prompt_text


# no existing summary means no PREVIOUS SUMMARY section in prompt
@patch("graph.nodes.ChatOpenAI")
def test_no_existing_summary_omits_previous_section(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response(
        "User has a landlord dispute in Arizona."
    )

    messages = [
        {"role": "user", "content": "my landlord won't fix my heating"},
        {"role": "llm", "content": "Which state are you in?"},
        {"role": "user", "content": "Arizona"},
    ]

    run_summarization(messages, existing_summary=None)

    call_args = mock_llm_class.return_value.invoke.call_args
    prompt_text = call_args[0][0][0]["content"]
    assert "PREVIOUS SUMMARY" not in prompt_text


# all messages should appear in the prompt
@patch("graph.nodes.ChatOpenAI")
def test_all_messages_included_in_prompt(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response(
        "User has an employment dispute."
    )

    messages = [
        {"role": "user", "content": "my employer fired me unfairly"},
        {"role": "llm", "content": "How long were you employed?"},
        {"role": "user", "content": "3 years"},
    ]

    run_summarization(messages)

    call_args = mock_llm_class.return_value.invoke.call_args
    prompt_text = call_args[0][0][0]["content"]
    assert "my employer fired me unfairly" in prompt_text
    assert "3 years" in prompt_text


# LLM failure should raise an exception — caller handles it
@patch("graph.nodes.ChatOpenAI")
def test_llm_failure_raises_exception(mock_llm_class):
    mock_llm_class.return_value.invoke.side_effect = Exception("OpenAI timeout")

    messages = [
        {"role": "user", "content": "I need help with my case"},
    ]

    with pytest.raises(Exception):
        run_summarization(messages)


# summary is stripped of whitespace
@patch("graph.nodes.ChatOpenAI")
def test_summary_is_stripped(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response(
        "   User has a traffic violation in California.   "
    )

    messages = [
        {"role": "user", "content": "I got a speeding ticket"},
        {"role": "llm", "content": "Which state?"},
        {"role": "user", "content": "California"},
    ]

    result = run_summarization(messages)
    assert result == "User has a traffic violation in California."
    assert not result.startswith(" ")
    assert not result.endswith(" ")
@patch("graph.nodes.ChatOpenAI")
def test_empty_messages_still_calls_llm(mock_llm_class):
    mock_llm_class.return_value.invoke.return_value = fake_llm_response(
        "No conversation history available."
    )
    result = run_summarization([])
    assert isinstance(result, str)