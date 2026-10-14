from typing import TypedDict


class LegalChatState(TypedDict):
    user_id: str
    query: str

    document_paths: list[str]
    chat_id: str

    user_context: dict
    conversation_history: dict
    primary_topic: str | None
    self_assessment_context: dict
    conversation_summary: str | None

    mode: str | None
    ready_to_generate: bool | None

    knowledge_chunks: list[dict]
    knowledge_sources: list[dict]

    document_text: str
    document_urls: list[str]
    anon_query: str
    anon_knowledge: list[str]
    anon_document: str

    llm_response: str

    final_answer: str

    detected_topic: list[str] | None
    confidence_delta: float | None

    error: str | None