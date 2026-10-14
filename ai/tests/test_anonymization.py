import pytest
from anonymization.anonymizer import anonymize_text


def test_removes_person_name():
    text = "My name is Joe Smith and I need legal help."
    result = anonymize_text(text)
    assert "Joe Smith" not in result


def test_removes_email():
    text = "Contact me at joe.doe@example.com for details."
    result = anonymize_text(text)
    assert "joe.doe@example.com" not in result


def test_removes_phone_number():
    text = "Call me at 555-867-5309."
    result = anonymize_text(text)
    assert "555-867-5309" not in result


def test_removes_ssn():
    text = "My social security number is 123-45-6789."
    result = anonymize_text(text)
    assert "123-45-6789" not in result


def test_removes_credit_card():
    text = "My credit card is 4111111111111111."
    result = anonymize_text(text)
    assert "4111111111111111" not in result


def test_preserves_dollar_amount():
    text = "The contract value is $4111111111111111."
    result = anonymize_text(text)
    # dollar amounts should not be redacted
    assert "$" in result


def test_preserves_non_pii_text():
    text = "The tenant must give 30 days notice before vacating."
    result = anonymize_text(text)
    assert result == text


def test_empty_string_returns_empty():
    assert anonymize_text("") == ""


def test_whitespace_only_returns_unchanged():
    assert anonymize_text("   ") == "   "


def test_multiple_pii_in_one_text():
    text = "Joe Smith can be reached at joe@example.com or 555-123-4567."
    result = anonymize_text(text)
    assert "Joe Smith" not in result
    assert "joe@example.com" not in result
    assert "555-123-4567" not in result