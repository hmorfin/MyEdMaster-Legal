from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import logging
import os
import re
from collections import Counter

logger = logging.getLogger(__name__)

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')


def _load_entities() -> list[str]:
    config_path = os.path.join(os.path.dirname(__file__), "anonymize_fields.txt")
    with open(config_path, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def anonymize_text(text: str) -> str:
    if not text or not text.strip():
        return text

    entities = _load_entities()
    results = analyzer.analyze(
        text=text,
        entities=entities,
        language="en"
    )

    filtered = [
        r for r in results
        if not (r.entity_type == "CREDIT_CARD" and _is_dollar_amount(text, r.start, r.end))
    ]

    if not filtered:
        result_text = text
    else:
        anonymized = anonymizer.anonymize(text=text, analyzer_results=filtered)
        result_text = anonymized.text

    ssn_matches = len(SSN_PATTERN.findall(result_text))
    result_text = SSN_PATTERN.sub("<US_SSN>", result_text)

    # Log only entity TYPE counts (e.g. "PERSON: 2, LOCATION: 1") — never the
    # matched values themselves, and never the raw or anonymized text.
    if filtered or ssn_matches:
        entity_type_counts = Counter(r.entity_type for r in filtered)
        if ssn_matches:
            entity_type_counts["US_SSN"] += ssn_matches
        logger.info(
            "pii_entities_redacted",
            extra={
                "input_length": len(text),
                "entity_counts": dict(entity_type_counts),
                "total_entities_redacted": sum(entity_type_counts.values()),
            },
        )

    return result_text


def _is_dollar_amount(text: str, start: int, end: int) -> bool:
    check_start = max(0, start - 2)
    surrounding = text[check_start:end]
    return "$" in surrounding