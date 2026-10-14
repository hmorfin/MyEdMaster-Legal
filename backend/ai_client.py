import httpx
import os

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai:8001")
TIMEOUT = 180


class AIServiceClient:
    def __init__(self, base_url: str = AI_SERVICE_URL, timeout: int = TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout

    def health(self) -> dict:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            return {"status": "unreachable", "error": str(e)}

    def query(
            self,
            user_id: str,
            query: str,
            chat_id: str | None = None,
            document_paths: list | None = None,
            conversation_history: list | None = None,
            user_context: dict | None = None,
            primary_topic: str | None = None,
            self_assessment_context: dict | None = None,
            conversation_summary: str | None = None,
            mode: str = "chat",
            document_context: dict | None = None,

    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/query",
                json={
                    "user_id": user_id,
                    "query": query,
                    "chat_id": chat_id,
                    "document_paths": document_paths or [],
                    "conversation_history": conversation_history or [],
                    "user_context": user_context or {},
                    "primary_topic": primary_topic,
                    "self_assessment_context": self_assessment_context or {},
                    "conversation_summary": conversation_summary,
                    "mode": mode,
                    "document_context": document_context or {},
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise AIServiceError(
                "The AI service took too long to respond. "
                "Please try again with a shorter query."
            )
        except httpx.HTTPStatusError as e:
            raise AIServiceError(
                f"AI service returned an error: {e.response.status_code} "
                f"— {e.response.text}"
            )
        except httpx.HTTPError as e:
            raise AIServiceError(
                f"Could not reach the AI service: {str(e)}. "
                "Make sure it is running on port 8001."
            )

    def summarize(
            self,
            messages: list,
            existing_summary: str | None = None,
    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/query/summarize",
                json={
                    "messages": messages,
                    "existing_summary": existing_summary,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise AIServiceError(
                "Summarization timed out. Please try again."
            )
        except httpx.HTTPStatusError as e:
            raise AIServiceError(
                f"Summarization failed: {e.response.status_code} — {e.response.text}"
            )
        except httpx.HTTPError as e:
            raise AIServiceError(
                f"Could not reach AI service: {str(e)}"
            )

    def generate_document_content(
            self,
            document_type: str,
            jurisdiction: str,
            parties: str,
            document_purpose: str,
            clauses: list,
            special_provisions: list,
            conversation_summary: str | None = None,
            full_context: str | None = None,
    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/documents/generate",
                json={
                    "document_type": document_type,
                    "jurisdiction": jurisdiction,
                    "parties": parties,
                    "document_purpose": document_purpose,
                    "clauses": clauses,
                    "special_provisions": special_provisions,
                    "conversation_summary": conversation_summary,
                    "full_context": full_context,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise AIServiceError("Document generation timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"Document generation failed: {e.response.status_code} — {e.response.text}")
        except httpx.HTTPError as e:
            raise AIServiceError(f"Could not reach AI service: {str(e)}")

    def generate_document_pdf(
            self,
            document_type: str,
            jurisdiction: str,
            parties: str,
            document_purpose: str,
            clauses: list,
            special_provisions: list,
            conversation_summary: str | None = None,
            full_context: str | None = None,
    ) -> bytes:
        try:
            response = httpx.post(
                f"{self.base_url}/documents/generate-pdf",
                json={
                    "document_type": document_type,
                    "jurisdiction": jurisdiction,
                    "parties": parties,
                    "document_purpose": document_purpose,
                    "clauses": clauses,
                    "special_provisions": special_provisions,
                    "conversation_summary": conversation_summary,
                    "full_context": full_context,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.content
        except httpx.TimeoutException:
            raise AIServiceError("PDF generation timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"PDF generation failed: {e.response.status_code} — {e.response.text}")
        except httpx.HTTPError as e:
            raise AIServiceError(f"Could not reach AI service: {str(e)}")

    def ingest_text(self, text: str, source: str, section: str = "") -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/ingest/text",
                json={"text": text, "source": source, "section": section},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise AIServiceError(f"Ingestion failed: {str(e)}")

    def knowledge_base_status(self) -> dict:
        try:
            response = httpx.get(f"{self.base_url}/ingest/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise AIServiceError(f"Status check failed: {str(e)}")

    ######## courses related methods - start ##########

    def generate_lesson(
            self,
            lesson_id: str,
            lesson_title: str,
            module_title: str,
            course_title: str,
            legal_topic: str,
            level: str,
            learning_objectives: list,
            user_context: dict,
    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/learning/lessons/generate",
                json={
                    "lesson_id": lesson_id,
                    "lesson_title": lesson_title,
                    "module_title": module_title,
                    "course_title": course_title,
                    "legal_topic": legal_topic,
                    "level": level,
                    "learning_objectives": learning_objectives,
                    "user_context": user_context,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise AIServiceError("Lesson generation timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"AI service error: {e.response.status_code} — {e.response.text}")
        except httpx.HTTPError as e:
            raise AIServiceError(f"Could not reach AI service: {str(e)}")

    def generate_assessment(
            self,
            legal_topic: str,
            level: str,
            scope: str,
            title: str,
            content_summary: str,
            question_count: int,
            user_mastery: float,
    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/learning/assessments/generate",
                json={
                    "legal_topic": legal_topic,
                    "level": level,
                    "scope": scope,
                    "title": title,
                    "content_summary": content_summary,
                    "question_count": question_count,
                    "user_mastery": user_mastery,
                },
                timeout=45,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise AIServiceError("Assessment generation timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"AI service error: {e.response.status_code} — {e.response.text}")
        except httpx.HTTPError as e:
            raise AIServiceError(f"Could not reach AI service: {str(e)}")

    def generate_assessment_feedback(
            self,
            legal_topic: str,
            score: float,
            passed: bool,
            results: list,
            next_action: str,
    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/learning/assessments/feedback",
                json={
                    "legal_topic": legal_topic,
                    "score": score,
                    "passed": passed,
                    "results": results,
                    "next_action": next_action,
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {"feedback": ""}

    ######## courses related methods - end ##########

    def generate_kb(
            self,
            legal_situation: str,
            prior_experience: str,
            desired_outcome: str,
            jurisdiction: str,
    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/self-assessment/generate-kb",
                json={
                    "legal_situation": legal_situation,
                    "prior_experience": prior_experience,
                    "desired_outcome": desired_outcome,
                    "jurisdiction": jurisdiction,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise AIServiceError(
                "KB generation timed out. Please try again."
            )
        except httpx.HTTPStatusError as e:
            raise AIServiceError(
                f"KB generation failed: {e.response.status_code} — {e.response.text}"
            )
        except httpx.HTTPError as e:
            raise AIServiceError(
                f"Could not reach AI service: {str(e)}"
            )

    def evaluate_self_assessment(
            self,
            chat_id: str,
            legal_situation: str,
            legal_domain: str,
            branch: str,
            jurisdiction: str,
            baseline_familiarity: str,
            primary_intent: str,
            prior_experience: str,
            desired_outcome: str,
            kb_content: dict,
            facts: dict,
            strategies: dict,
            procedures: dict,
            rationales: dict,
    ) -> dict:
        try:
            response = httpx.post(
                f"{self.base_url}/self-assessment/evaluate",
                json={
                    "chat_id": chat_id,
                    "legal_situation": legal_situation,
                    "legal_domain": legal_domain,
                    "branch": branch,
                    "jurisdiction": jurisdiction,
                    "baseline_familiarity": baseline_familiarity,
                    "primary_intent": primary_intent,
                    "prior_experience": prior_experience,
                    "desired_outcome": desired_outcome,
                    "kb_content": kb_content,
                    "facts": facts,
                    "strategies": strategies,
                    "procedures": procedures,
                    "rationales": rationales,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise AIServiceError(
                "Self-assessment evaluation timed out. Please try again."
            )
        except httpx.HTTPStatusError as e:
            raise AIServiceError(
                f"Self-assessment evaluation failed: {e.response.status_code} — {e.response.text}"
            )
        except httpx.HTTPError as e:
            raise AIServiceError(
                f"Could not reach AI service: {str(e)}"
            )

    def markdown_to_pdf(self, title: str, content_markdown: str) -> bytes:
        try:
            response = httpx.post(
                f"{self.base_url}/documents/markdown-to-pdf",
                json={"title": title, "content_markdown": content_markdown},
                timeout=30,
            )
            response.raise_for_status()
            return response.content
        except httpx.TimeoutException:
            raise AIServiceError("PDF conversion timed out.")
        except httpx.HTTPStatusError as e:
            raise AIServiceError(f"PDF conversion failed: {e.response.status_code}")
        except httpx.HTTPError as e:
            raise AIServiceError(f"Could not reach AI service: {str(e)}")
        
    # courses 


class AIServiceError(Exception):
    pass


ai_client = AIServiceClient()