# graph/nodes.py
import json
import logging
import time

from langchain_openai import ChatOpenAI
from langsmith import traceable

from config import settings
from document_extraction.extractor import extractor
from anonymization.anonymizer import anonymize_text
from graph.state import LegalChatState
from graph.prompts import (
    LEGAL_ADVISOR_PROMPT,
    LEGAL_ADVISOR_PROMPT_NO_FSPR,
    LEGAL_DOCUMENT_ADVISOR_PROMPT,
    SUMMARIZATION_PROMPT,
)

logger = logging.getLogger(__name__)

# NOTE ON LOGGING: nodes in this pipeline see raw user queries, uploaded document
# text, and (briefly, before the anonymization node runs) unredacted PII. Never log
# the actual query/document/knowledge-chunk/LLM-response *content* here — log
# lengths, counts, scores, topics, and timings instead.


# ---------------------------------------------------------------------------
# Node 1: RAG
# ---------------------------------------------------------------------------

@traceable
def rag_node(state: LegalChatState) -> dict:
    start = time.time()
    try:
        from rag.embedder import embedder
        from rag.vector_store import search_chunks

        query_vector = embedder.embed(state["query"])
        results = search_chunks(query_vector=query_vector, top_k=5)

        chunks = []
        sources = []
        for r in results:
            text = r.payload.get("text", "")
            if r.score > 0.75 and text:
                chunks.append(text)
                sources.append({
                    "text": text[:300],
                    "score": round(r.score, 3),
                    "source": r.payload.get("source", "Legal Database"),
                })

        logger.info(
            "rag_node_completed",
            extra={
                "candidates_returned": len(results),
                "chunks_above_threshold": len(chunks),
                "duration_ms": round((time.time() - start) * 1000, 1),
            },
        )
        return {"knowledge_chunks": chunks, "knowledge_sources": sources}
    except Exception:
        logger.warning(
            "rag_node_failed_returning_empty",
            exc_info=True,
            extra={"duration_ms": round((time.time() - start) * 1000, 1)},
        )
        return {"knowledge_chunks": []}


# ---------------------------------------------------------------------------
# Node 2: Document Extraction
# ---------------------------------------------------------------------------

@traceable
def extraction_node(state: LegalChatState) -> dict:
    document_paths = state.get("document_paths") or []

    if not document_paths:
        return {"document_text": "", "document_urls": []}

    start = time.time()
    all_text = []
    document_urls = []
    failed = 0

    for path in document_paths:
        try:
            url = extractor._get_presigned_url(path)
            document_urls.append(url)
            text = extractor.extract_from_url(url)
            filename = path.split("/")[-1]
            all_text.append(f"[Document: {filename}]\n{text}")
        except Exception:
            failed += 1
            logger.warning("document_extraction_failed", exc_info=True)

    logger.info(
        "extraction_node_completed",
        extra={
            "documents_requested": len(document_paths),
            "documents_extracted": len(document_paths) - failed,
            "documents_failed": failed,
            "duration_ms": round((time.time() - start) * 1000, 1),
        },
    )

    return {
        "document_text": "\n\n---\n\n".join(all_text),
        "document_urls": document_urls,
    }


# ---------------------------------------------------------------------------
# Node 3: Anonymization
# ---------------------------------------------------------------------------

@traceable
def anonymization_node(state: LegalChatState) -> dict:
    start = time.time()

    anon_query = anonymize_text(state["query"])
    anon_document = anonymize_text(state["document_text"])
    anon_knowledge = [anonymize_text(chunk) for chunk in state["knowledge_chunks"]]

    # Log only whether the anonymizer changed anything (a proxy for "PII was found")
    # and lengths — never the raw or anonymized text itself.
    logger.info(
        "anonymization_node_completed",
        extra={
            "query_pii_redacted": anon_query != state["query"],
            "document_pii_redacted": anon_document != state["document_text"],
            "knowledge_chunks_anonymized": len(anon_knowledge),
            "duration_ms": round((time.time() - start) * 1000, 1),
        },
    )

    return {
        "anon_query":    anon_query,
        "anon_document": anon_document,
        "anon_knowledge": anon_knowledge,
    }


# ---------------------------------------------------------------------------
# Node 4: Summarization (called async from Django, not part of LangGraph graph)
# ---------------------------------------------------------------------------
@traceable
def run_summarization(messages: list, existing_summary: str | None = None) -> str:
    start = time.time()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
    )

    previous_summary_section = (
        f"\nPREVIOUS SUMMARY:\n{existing_summary}\n"
        if existing_summary else ""
    )

    history_text = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}"
        for msg in messages
    )

    prompt = SUMMARIZATION_PROMPT.format(
        previous_summary_section=previous_summary_section,
        history_text=history_text,
    )

    response = llm.invoke([{"role": "user", "content": prompt}])
    summary = response.content.strip()

    logger.info(
        "summarization_completed",
        extra={
            "messages_summarized": len(messages),
            "had_previous_summary": bool(existing_summary),
            "summary_length": len(summary),
            "duration_ms": round((time.time() - start) * 1000, 1),
        },
    )
    return summary


# ---------------------------------------------------------------------------
# Node 6: Legal Reasoning
# ---------------------------------------------------------------------------

@traceable
def reasoning_node(state: LegalChatState) -> dict:
    start = time.time()
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
    user_context = state.get("user_context", {})

    sa_context = state.get("self_assessment_context") or {}
    has_self_assessment = bool(sa_context.get("priority_focus"))

    # --- Build knowledge context ---
    knowledge_section = ""
    if state.get("anon_knowledge"):
        formatted = "\n\n".join(
            f"[Legal Reference {i+1}]:\n{chunk}"
            for i, chunk in enumerate(state["anon_knowledge"])
        )
        knowledge_section = f"\n\nRELEVANT LEGAL KNOWLEDGE:\n{formatted}"

    # --- Build document context ---
    document_section = ""
    if state.get("anon_document"):
        document_section = f"\n\nUSER'S DOCUMENT(S):\n{state['anon_document']}"

    # --- Summary context ---
    summary_section = ""
    if state.get("conversation_summary"):
        summary_section = f"\n\nCONVERSATION SUMMARY (earlier context):\n{state['conversation_summary']}"

    # --- Topics list ---
    from legal_topics import LEGAL_TOPICS
    topics_list = "\n".join(f"- {t}" for t in LEGAL_TOPICS)

    # --- System prompt ---
    mode = state.get("mode") or "chat"

    if mode == "document":
        doc_context = state.get("document_context") or {}
        logger.info("reasoning_mode_selected", extra={"mode": "document"})
        system_prompt = LEGAL_DOCUMENT_ADVISOR_PROMPT.format(
            document_type=doc_context.get("document_type", "legal document"),
            jurisdiction=sa_context.get("jurisdiction", "") or user_context.get("jurisdiction", ""),
            parties=doc_context.get("parties", ""),
            document_purpose=doc_context.get("document_purpose", ""),
            conversation_summary=state.get("conversation_summary") or "No prior summary.",
            topics_list=topics_list,
        )
        user_message = f"{knowledge_section}{document_section}\n\nUSER MESSAGE:\n{state['anon_query']}"

    elif has_self_assessment:
        logger.info("reasoning_mode_selected", extra={"mode": "fspr", "has_priority_focus": True})
        system_prompt = LEGAL_ADVISOR_PROMPT.format(
            legal_domain=sa_context.get("legal_domain", ""),
            jurisdiction=sa_context.get("jurisdiction", ""),
            legal_situation=sa_context.get("legal_situation", ""),
            prior_experience=sa_context.get("prior_experience", ""),
            desired_outcome=sa_context.get("desired_outcome", ""),
            baseline_familiarity=sa_context.get("baseline_familiarity", ""),
            priority_focus=sa_context.get("priority_focus", ""),
            evaluation_report=sa_context.get("evaluation_report", ""),
            topics_list=topics_list,
            conversation_summary=state.get("conversation_summary") or "No prior summary.",
        )
        user_message = f"{knowledge_section}{document_section}\n\nUSER QUESTION:\n{state['anon_query']}"
    else:
        logger.info("reasoning_mode_selected", extra={"mode": "fallback_no_fspr"})
        mastery_scores = user_context.get("mastery_scores", {})
        primary_topic = state.get("primary_topic") or ""
        mastery_score = mastery_scores.get(primary_topic, 0.1)

        last_llm_was_question = False
        for msg in reversed(state.get("conversation_history", [])):
            if msg["role"] in ("llm", "assistant"):
                content = msg["content"].split("---")[0].strip()
                last_llm_was_question = content.rstrip().endswith("?")
                break

        system_prompt = LEGAL_ADVISOR_PROMPT_NO_FSPR.format(
            legal_domain=sa_context.get("legal_domain", "") or user_context.get("legal_domain", ""),
            jurisdiction=sa_context.get("jurisdiction", ""),
            legal_situation=sa_context.get("legal_situation", ""),
            prior_experience=sa_context.get("prior_experience", ""),
            desired_outcome=sa_context.get("desired_outcome", ""),
            baseline_familiarity=sa_context.get("baseline_familiarity", "") or user_context.get("knowledge_level",
                                                                                                "low"),
            primary_topic=primary_topic or "Not yet established",
            mastery_score=f"{mastery_score:.1f}",
            last_llm_was_question=last_llm_was_question,
            conversation_summary=state.get("conversation_summary") or "No prior summary.",
            topics_list=topics_list,
        )
        user_message = f"{knowledge_section}{document_section}\n\nUSER QUESTION:\n{state['anon_query']}"
        if user_context:
            user_message = (
                    f"USER PROFILE: {sa_context.get('jurisdiction', '') or user_context.get('jurisdiction', '')} | "
                    f"{user_context.get('profession', '')} | "
                    f"Knowledge: {user_context.get('knowledge_level', 'beginner')}\n\n"
                    + user_message
            )

    # --- Build message list for OpenAI ---
    messages = [{"role": "system", "content": system_prompt}]

    for msg in state.get("conversation_history", []):
        role = "assistant" if msg["role"] == "llm" else msg["role"]
        messages.append({"role": role, "content": msg["content"]})

    user_message = f"{summary_section}{knowledge_section}{document_section}\n\nUSER QUESTION:\n{state['anon_query']}"
    if user_context:
        user_message = (
            f"USER PROFILE: {user_context.get('jurisdiction', '')} | "
            f"{user_context.get('profession', '')} | "
            f"Knowledge: {user_context.get('knowledge_level', 'beginner')}\n\n"
            + user_message
        )
    messages.append({"role": "user", "content": user_message})

    try:
        response = llm.invoke(messages)

        raw = response.content.strip()
        if not raw:
            logger.warning("llm_returned_empty_response")
            return {
                "llm_response": "",
                "detected_topic": None,
                "confidence_delta": None,
                "error": "LLM returned empty response — please try again",
            }

        if "```" in raw:
            import re
            raw = re.sub(r'```(?:json)?\s*', '', raw)
        raw = raw.strip()

        if not raw:
            logger.warning("llm_returned_empty_response_after_strip")
            return {
                "llm_response": "",
                "detected_topic": None,
                "confidence_delta": None,
                "error": "LLM returned empty response — please try again",
            }

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as je:
            # Try to extract JSON from mixed content (text before/after JSON)
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                except json.JSONDecodeError:
                    parsed = None
            else:
                parsed = None

            if not parsed:
                logger.warning(
                    "llm_response_json_parse_failed",
                    extra={"parse_error": str(je), "raw_response_length": len(raw)},
                )
                if raw and len(raw) > 20:
                    return {
                        "llm_response": raw,
                        "detected_topic": [],
                        "confidence_delta": 0.1,
                    }
                return {
                    "llm_response": "",
                    "detected_topic": None,
                    "confidence_delta": None,
                    "error": "Could not process response — please try again",
                }

        answer = parsed.get("answer", "")
        # Strip any leaked JSON from the answer field
        if answer and "ready_to_generate" in answer:
            try:
                import re
                json_match = re.search(r'\{.*\}', answer, re.DOTALL)
                if json_match:
                    inner = json.loads(json_match.group())
                    answer = inner.get("answer", answer)
            except Exception:
                pass

        logger.info(
            "reasoning_node_completed",
            extra={
                "detected_topics": parsed.get("detected_topics"),
                "confidence_delta": parsed.get("confidence_delta"),
                "ready_to_generate": parsed.get("ready_to_generate", False),
                "answer_length": len(answer or ""),
                "duration_ms": round((time.time() - start) * 1000, 1),
            },
        )

        return {
            "llm_response": answer,
            "detected_topic": parsed.get("detected_topics", []),
            "confidence_delta": float(parsed.get("confidence_delta", 0.1)),
            "ready_to_generate": parsed.get("ready_to_generate", False),
            "document_context": parsed.get("document_context", {}),
        }

    except Exception as e:
        logger.error(
            "reasoning_node_llm_call_failed",
            exc_info=True,
            extra={"duration_ms": round((time.time() - start) * 1000, 1)},
        )
        return {
            "llm_response": "",
            "detected_topic": None,
            "confidence_delta": None,
            "error": f"LLM call failed: {str(e)}",
        }


# ---------------------------------------------------------------------------
# Node 7: Formatter
# ---------------------------------------------------------------------------

@traceable
def formatter_node(state: LegalChatState) -> dict:
    if state.get("error"):
        logger.info("formatter_node_returning_error", extra={"error": state.get("error")})
        return {"final_answer": "Could you please rephrase that and try again?"}

    if not state.get("llm_response"):
        logger.warning("formatter_node_empty_llm_response")
        return {"final_answer": (
            "I wasn't able to generate a response. "
            "Could you rephrase your question and try again?"
        )}

    logger.info(
        "formatter_node_completed",
        extra={"final_answer_length": len(state["llm_response"])},
    )
    return {"final_answer": state["llm_response"]}