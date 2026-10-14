# Legal Chatbot — AI Layer (FastAPI)

This service powers the AI pipeline for a **Personalized Legal Chatbot** built with **FastAPI**, **LangGraph**, and **Qdrant Cloud**.

It handles semantic retrieval, document extraction, PII anonymization, intelligent case analysis, conversation summarization, self-assessment evaluation, FSPR knowledge tracking, and structured legal tutoring.

---

## What This Service Does

* **Semantic search (RAG)** — Retrieves relevant legal knowledge from Qdrant Cloud before every LLM call using a domain-specific legal embedding model.
* **Corpus ingestion** — Bulk-ingests legal documents, including contracts and case law, into Qdrant with GPT-4o metadata extraction.
* **Document extraction** — Extracts PDFs from AWS S3 for user-uploaded documents via presigned URLs.
* **PII anonymization** — Uses Microsoft Presidio to anonymize all text before any LLM call.
* **LangGraph orchestration** — Runs a 5-node linear pipeline: RAG → Extraction → Anonymization → Reasoning → Formatter.
* **Unified reasoning node** — Uses a single LLM call for clarification, gotcha questioning, FSPR injection, and legal response generation.
* **Async rolling summarization** — Compresses older conversation history into a structured summary triggered by Django after a token threshold.
* **Self-assessment evaluation** — Runs a 4-LLM pipeline that generates a personalized knowledge base and FSPR evaluation report per user.
* **FSPR inference** — Tracks per-exchange knowledge across Facts, Strategies, Procedures, and Rationales.
* **Tutoring service** — Provides three independent LangGraph pipelines for lesson generation, MCQ assessment, and feedback.
* **LangSmith integration** — Adds observability and tracing across pipeline nodes via `@traceable` decorators.
* **Topic detection** — Maps queries to one or more of 20 predefined legal domains.
* **Confidence delta scoring** — Scores user understanding from `0.0` to `1.0` per message.

---

## Tech Stack

| Component              | Technology                                         |
| ---------------------- | -------------------------------------------------- |
| API Framework          | FastAPI                                            |
| Pipeline Orchestration | LangGraph                                          |
| LLM (main)             | OpenAI GPT-4o                                      |
| LLM (FSPR inference)   | OpenAI GPT-4o-mini                                 |
| Vector Database        | Qdrant Cloud                                       |
| Embedding Model        | `Stern5497/sbert-legal-xlm-roberta-base` (768-dim) |
| Anonymization          | Microsoft Presidio + spaCy `en_core_web_lg`        |
| Document Extraction    | AWS S3 + PyMuPDF                                   |
| Observability          | LangSmith                                          |

---

## Quickstart

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### 3. Create `.env`

```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o

# Qdrant Cloud
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION=corpus

# Embedding Model
LEGAL_EMBEDDING_MODEL=Stern5497/sbert-legal-xlm-roberta-base
EMBEDDING_DIM=768

# AWS S3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket
S3_PRESIGN_EXPIRES_SECONDS=300

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=legal_chatbot_db

# LangSmith (optional)
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=legal-chatbot
```

### 4. Run the server

Mac/Linux:

```bash
uvicorn ai.main:app --host 0.0.0.0 --port 8001 --reload
```

Windows PowerShell, from the project root:

```powershell
$env:PYTHONPATH="ai"
uvicorn ai.main:app --host 0.0.0.0 --port 8001 --reload
```

> **Windows note:** `PYTHONPATH="ai"` is required because bare imports like `from config import settings` resolve relative to the `ai/` folder. Without it, you will get `ModuleNotFoundError`.

### 5. Health check

```http
GET http://localhost:8001/health
```

---

## Service Structure

```text
ai/
├── main.py                        # FastAPI app entry point + lifespan
├── config.py                      # Pydantic settings
├── legal_topics.py                # 20 predefined legal domain topics
├── graph/
│   ├── state.py                   # LegalChatState TypedDict
│   ├── nodes.py                   # 5 pipeline nodes + run_summarization utility
│   ├── builder.py                 # LangGraph compilation (linear 5-node graph)
│   ├── prompts.py                 # LEGAL_ADVISOR_PROMPT, LEGAL_ADVISOR_PROMPT_NO_FSPR, SUMMARIZATION_PROMPT
│   ├── course_state.py            # TypedDicts for tutoring service pipelines
│   ├── course_nodes.py            # Tutoring nodes: lesson, assessment, feedback + formatters
│   ├── course_builder.py          # Three tutoring LangGraph pipelines
│   └── tutoring_prompts.py        # Prompts for tutoring service
├── routers/
│   ├── query.py                   # POST /query, POST /query/summarize, POST /query/search
│   ├── ingest.py                  # POST /ingest/upload, DELETE /ingest/{doc_id}
│   ├── courses.py                 # POST /learning/lessons/generate, /assessments/generate, /assessments/feedback
│   └── fspr.py                    # POST /fspr/infer
├── self_assessment/
│   ├── router.py                  # POST /self-assessment/generate-kb, /self-assessment/evaluate
│   ├── pipeline.py                # 4-LLM self-assessment pipeline
│   ├── prompts.py                 # Self-assessment prompts
│   └── schemas.py                 # Request/response schemas
├── document_extraction/
│   └── extractor.py               # PyMuPDF + S3 presigned URL fetcher
├── anonymization/
│   ├── anonymizer.py              # Presidio PII detection and replacement
│   └── anonymize_fields.txt       # Configurable list of PII entity types
└── rag/
    ├── embedder.py                # Legal embedding model wrapper
    ├── vector_store.py            # Qdrant Cloud wrapper
    └── corpus_ingestion.py        # Bulk ingestion pipeline
```

---

## LangGraph Pipeline — Main Chat

Every chat message flows through a 5-node linear LangGraph pipeline.

```text
User Query
   │
   ▼
[Node 1: RAG]
   │
   ▼
[Node 2: Extraction]
   │
   ▼
[Node 3: Anonymization]
   │
   ▼
[Node 4: Reasoning]
   │
   ▼
[Node 5: Formatter]
```

### Node 1: RAG

* Embeds query using `sbert-legal-xlm-roberta-base`.
* Fetches top 5 chunks from Qdrant Cloud.
* Filters by cosine similarity threshold `0.75`.
* Returns `knowledge_chunks: list[str]`.
* Fails silently and returns an empty list if the corpus is unavailable.

### Node 2: Extraction

* Fetches user-uploaded PDFs from AWS S3 via presigned URLs.
* Extracts and labels text per document using PyMuPDF.
* Skips extraction if no `document_paths` are provided.

### Node 3: Anonymization

* Uses Presidio to anonymize the query, document text, and knowledge chunks.
* Replaces PII with entity labels such as `PERSON`, `ORG`, and `DATE`.
* Preserves locations and dollar amounts for legal accuracy.

### Node 4: Reasoning

* Uses a single LLM call for clarification, legal analysis, and gotcha questioning.
* Supports two modes based on self-assessment status:

  * **Mode A (FSPR):** Injects evaluation report, priority focus, and knowledge gaps.
  * **Mode B (Fallback):** Uses topic mastery scores, conversation history, and knowledge level.
* Injects conversation summary when available.
* Injects RAG knowledge chunks and document content.
* Asks targeted lawyer-style follow-up questions when critical facts are missing.
* Surfaces gotcha insights, including risks to avoid, user leverage, and the other party's exposure.
* Returns `answer`, `detected_topics`, and `confidence_delta`.

### Node 5: Formatter

* Returns the LLM answer or a graceful error message.
* Falls back to `Could you please rephrase that?` on error.

---

## Reasoning Node — Two Modes

### Mode A — FSPR-Aware

Used when the user has completed self-assessment.

Uses `LEGAL_ADVISOR_PROMPT`, which injects:

* Legal domain, jurisdiction, legal situation, prior experience, and desired outcome.
* Baseline familiarity level: `low`, `medium`, or `high`.
* Priority focus from FSPR evaluation, such as `Strategies — Know-Don't Know`.
* Full FSPR evaluation report identifying knowledge gaps.
* Conversation summary from async summarization.

Guidance per gap type:

| Gap Type        | Behavior                                          |
| --------------- | ------------------------------------------------- |
| False Knowledge | Proactively correct the misconception early.      |
| Omission        | Surface the missing concept before anything else. |
| Know-Don't Know | Explain the unknown area and available options.   |
| Know-Know       | Do not repeat; build on existing knowledge.       |

### Mode B — Fallback

Used when self-assessment is skipped or pending.

Uses `LEGAL_ADVISOR_PROMPT_NO_FSPR`, which injects:

* User context: jurisdiction, profession, and knowledge level.
* Primary topic and mastery score.
* Conversation summary from async summarization.

Both modes follow the same response style rules: warm, conversational, naturally integrated gotcha insights, and no generic step-by-step legal advice before the relevant facts are known.

---

## Async Summarization

Summarization runs outside the LangGraph graph as the `run_summarization` utility function. It is triggered asynchronously by Django after each LLM response.

### Trigger Conditions

Both must be true:

1. Unsummarized message tokens exceed `1500`.
2. More than 6 messages have occurred since the last summarization point.

### How It Works

1. After every LLM response, Django checks the token count of unsummarized messages.
2. If the threshold is hit, Django starts a background thread.
3. The background thread calls `POST /query/summarize` with the older messages.
4. The summary is saved to `Conversation.conversation_summary` in MongoDB.
5. On the next request, Django passes `conversation_summary` to the AI layer.
6. The reasoning node injects the summary so the LLM retains full history without token overhead.

### What the Summary Preserves

* Legal issue, domain, and branch.
* Key facts: jurisdiction, role, situation, timeline, dates, and amounts.
* Clarifications already provided by the user.
* Actions the user has already taken.
* Advice already given to prevent repetition.
* Confirmed facts and agreements reached.

---

## Tutoring Service Pipelines

The tutoring service has three independent LangGraph pipelines under `/learning`. Each pipeline has a generation node followed by a formatter node.

### Lesson Generation

```text
generate_lesson → format_lesson → END
```

* `lesson_content_node` generates full markdown lessons with key terms, adapted to user mastery level and jurisdiction.
* Depth levels:

  * **Beginner:** Practical, plain English.
  * **Intermediate:** Terminology and exceptions.
  * **Advanced:** Statutes, case law, and nuance.
* `lesson_formatter_node` validates content length and filters invalid key terms.

### Assessment Generation

```text
generate_assessment → format_assessment → END
```

* `question_generator_node` generates MCQs adapted to mastery level:

  * Recall: `< 0.3`
  * Application: `0.3–0.6`
  * Analysis: `> 0.6`
* `assessment_formatter_node` validates all required fields per question.
* Questions are rejected if they do not have exactly 4 options or if `correct_index` is outside `0–3`.

### Feedback

```text
generate_feedback → format_feedback → END
```

* `feedback_node` generates personalized feedback referencing specific wrong answers and guiding the next action.
* `feedback_formatter_node` returns a fallback message if feedback is empty or the LLM fails.

### Course Structure

* 20 legal domains × 3 levels: beginner, intermediate, advanced.
* Pass threshold: `70%` to unlock the next level.
* `pass_threshold = 0.70`.
* Lesson content is LLM-generated on first access and cached in the Django database.

---

## Self-Assessment Pipeline

Four LLM calls run in `self_assessment/pipeline.py`.

| Step                     | Purpose                                                                    |
| ------------------------ | -------------------------------------------------------------------------- |
| LLM1 — Classifier        | Identifies legal domain, branch, baseline familiarity, and primary intent. |
| LLM2 — KB Generator      | Generates knowledge base, RAG snippets, and few-shot examples.             |
| LLM3 — Auditor           | Validates KB quality. Runs only if `KB_AUDIT_ENABLED=true`.                |
| LLM4 — Example Generator | Generates reference examples for user self-assessment.                     |

`LLM2` and `LLM4` run in parallel via `ThreadPoolExecutor`.

The evaluation pipeline runs four parallel dimension evaluators to produce the FSPR report across:

* **Facts** — Legal facts, statutes, and rights.
* **Strategies** — Approaches and options.
* **Procedures** — Step-by-step processes.
* **Rationales** — Reasoning behind legal rules.

---

## FSPR Inference

`POST /fspr/infer` is called after each chat exchange to update the user's knowledge profile.

It uses GPT-4o-mini to evaluate the exchange and return:

* Which FSPR dimension was most revealed.
* Knowledge label:

  * `Know-Know`
  * `Know-Don't Know`
  * `False Knowledge`
  * `Omission`
* Updated score:

```text
new_score = current_score * 0.7 + signal_strength * 0.3
```

Signal strengths:

| Label           | Signal Strength |
| --------------- | --------------: |
| Know-Know       |             0.8 |
| Know-Don't Know |             0.4 |
| Omission        |             0.3 |
| False Knowledge |             0.2 |

---

## LLM Call Registry

| Purpose                         | Location                  | Model       | Trigger                                                        |
| ------------------------------- | ------------------------- | ----------- | -------------------------------------------------------------- |
| Legal reasoning + clarification | `reasoning_node`          | GPT-4o      | Every chat message                                             |
| Conversation summarization      | `run_summarization`       | GPT-4o      | Async background thread from Django                            |
| Lesson content generation       | `lesson_content_node`     | GPT-4o      | `POST /learning/lessons/generate`                              |
| Assessment generation           | `question_generator_node` | GPT-4o      | `POST /learning/assessments/generate`                          |
| Assessment feedback             | `feedback_node`           | GPT-4o      | `POST /learning/assessments/feedback`                          |
| Self-assessment classification  | LLM1 in `pipeline.py`     | GPT-4o      | `POST /self-assessment/generate-kb`                            |
| KB generation                   | LLM2 in `pipeline.py`     | GPT-4o      | `POST /self-assessment/generate-kb` parallel                   |
| KB audit                        | LLM3 in `pipeline.py`     | GPT-4o      | `POST /self-assessment/generate-kb` if `KB_AUDIT_ENABLED=true` |
| Example generation              | LLM4 in `pipeline.py`     | GPT-4o      | `POST /self-assessment/generate-kb` parallel                   |
| FSPR inference                  | `fspr.py`                 | GPT-4o-mini | `POST /fspr/infer`                                             |
| Corpus metadata extraction      | `corpus_ingestion.py`     | GPT-4o      | Manual ingestion only                                          |

---

## API Endpoints

All endpoints are served on:

```text
http://localhost:8001
```

### Query — `/query`

| Method | Endpoint           | Description                                             |
| ------ | ------------------ | ------------------------------------------------------- |
| POST   | `/query`           | Run full 5-node LangGraph pipeline.                     |
| POST   | `/query/summarize` | Summarize conversation history. Called async by Django. |
| POST   | `/query/search`    | Direct Qdrant semantic search. Bypasses LangGraph.      |

#### `POST /query` request

```json
{
  "user_id": "user_123",
  "query": "My landlord won't fix the heating",
  "chat_id": "chat_456",
  "document_paths": [],
  "conversation_history": [],
  "conversation_summary": null,
  "user_context": {
    "knowledge_level": "beginner",
    "jurisdiction": "Arizona",
    "profession": "student",
    "mastery_scores": {}
  }
}
```

#### `POST /query` response

```json
{
  "answer": "Your landlord is legally required to maintain habitable conditions...",
  "has_document_context": false,
  "has_knowledge_context": true,
  "document_urls": [],
  "detected_topic": ["Tenant & Landlord Rights"],
  "confidence_delta": 0.3,
  "conversation_summary": null
}
```

#### `POST /query/summarize` request

```json
{
  "messages": [
    {
      "role": "user",
      "content": "I got into a car accident"
    },
    {
      "role": "llm",
      "content": "Were you the driver?"
    },
    {
      "role": "user",
      "content": "Yes, in Texas"
    }
  ],
  "existing_summary": null
}
```

### Learning — `/learning`

| Method | Endpoint                         | Description                                    |
| ------ | -------------------------------- | ---------------------------------------------- |
| POST   | `/learning/lessons/generate`     | Generate lesson content for a topic and level. |
| POST   | `/learning/assessments/generate` | Generate MCQ assessment questions.             |
| POST   | `/learning/assessments/feedback` | Generate personalized assessment feedback.     |

#### `POST /learning/lessons/generate` request

```json
{
  "lesson_id": "lesson_001",
  "lesson_title": "Understanding Tenant Rights",
  "module_title": "Landlord-Tenant Basics",
  "course_title": "Tenant & Landlord Rights",
  "legal_topic": "Tenant & Landlord Rights",
  "level": "beginner",
  "learning_objectives": [
    "Understand what a lease is",
    "Know your rights as a tenant"
  ],
  "user_context": {
    "knowledge_level": "beginner",
    "jurisdiction": "Arizona",
    "profession": "student",
    "mastery_scores": {}
  }
}
```

#### `POST /learning/assessments/generate` request

```json
{
  "legal_topic": "Tenant & Landlord Rights",
  "level": "beginner",
  "scope": "lesson",
  "title": "Understanding Tenant Rights",
  "content_summary": "Covered lease agreements, tenant rights, landlord obligations in Arizona",
  "question_count": 5,
  "user_mastery": 0.2
}
```

#### `POST /learning/assessments/feedback` request

```json
{
  "legal_topic": "Tenant & Landlord Rights",
  "score": 0.8,
  "passed": true,
  "results": [
    {
      "question": "Can a landlord enter without notice?",
      "options": [
        "Yes always",
        "No never",
        "Only in emergencies",
        "Only on weekdays"
      ],
      "correct_answer": 2,
      "user_answer": 2,
      "is_correct": true
    }
  ],
  "next_action": "next_lesson"
}
```

### Self-Assessment — `/self-assessment`

| Method | Endpoint                       | Description                                                    |
| ------ | ------------------------------ | -------------------------------------------------------------- |
| POST   | `/self-assessment/generate-kb` | Generate personalized knowledge base using the 4-LLM pipeline. |
| POST   | `/self-assessment/evaluate`    | Evaluate user self-assessment submission.                      |

### FSPR — `/fspr`

| Method | Endpoint      | Description                                                |
| ------ | ------------- | ---------------------------------------------------------- |
| POST   | `/fspr/infer` | Update FSPR knowledge profile from a single chat exchange. |

### Ingest — `/ingest`

| Method | Endpoint           | Description                               |
| ------ | ------------------ | ----------------------------------------- |
| POST   | `/ingest/upload`   | Upload and ingest a document into Qdrant. |
| GET    | `/ingest/status`   | Check current chunk count in Qdrant.      |
| DELETE | `/ingest/{doc_id}` | Remove a document from Qdrant.            |

### Health

| Method | Endpoint  | Description                                                        |
| ------ | --------- | ------------------------------------------------------------------ |
| GET    | `/health` | Service health check. Returns embedding model and LLM model names. |

---

## Anonymization Pipeline

The anonymization pipeline runs between extraction and reasoning. It processes three inputs.

| Input Field                 | Output Field              | Content                                  |
| --------------------------- | ------------------------- | ---------------------------------------- |
| `state["query"]`            | `state["anon_query"]`     | User's question                          |
| `state["document_text"]`    | `state["anon_document"]`  | Extracted PDF text                       |
| `state["knowledge_chunks"]` | `state["anon_knowledge"]` | RAG chunks, each anonymized individually |

### PII Entity Types

Configured in `anonymize_fields.txt`.

| Entity              | What It Catches                               |
| ------------------- | --------------------------------------------- |
| `PERSON`            | Full and partial names                        |
| `EMAIL_ADDRESS`     | Email addresses                               |
| `PHONE_NUMBER`      | US and international phone numbers            |
| `US_SSN`            | Social Security Numbers                       |
| `US_DRIVER_LICENSE` | Driver license numbers                        |
| `CREDIT_CARD`       | Credit card numbers, excluding dollar amounts |

### Intentionally Preserved

* `LOCATION` — Jurisdiction such as Arizona or Maricopa County must be preserved for legal accuracy.
* Dollar amounts — Values such as `$1800` or `$3600` are not flagged as credit cards.

---

## Vector Database — Qdrant Cloud

### Embedding Model

```text
Stern5497/sbert-legal-xlm-roberta-base
```

| Property            | Value             |
| ------------------- | ----------------- |
| Dimensions          | 768               |
| Distance metric     | Cosine similarity |
| Retrieval threshold | 0.75              |
| Chunks per query    | Top 5             |

### Collection Structure

| Field           | Type   | Description                                                               |
| --------------- | ------ | ------------------------------------------------------------------------- |
| `doc_id`        | string | UUID shared by all chunks from the same source.                           |
| `chunk_id`      | int    | Sequential chunk index within the document.                               |
| `doc_type`      | string | `contract` or `case_law`.                                                 |
| `text`          | string | Raw chunk text, approximately 1200 characters with 200-character overlap. |
| `contract_type` | string | Example: `Purchase Agreement`. Contracts only.                            |
| `contract_date` | string | Extracted contract date.                                                  |
| `case_title`    | string | Case name. Case law only.                                                 |
| `case_date`     | string | Decision date.                                                            |
| `title`         | string | Source filename.                                                          |

Payload indexes are created on:

* `doc_id`
* `doc_type`
* `contract_type`
* `case_title`

These indexes are required for filtered search and delete.

### Current Collection Stats

| Metric          |          Value |
| --------------- | -------------: |
| Total chunks    |        174,668 |
| Contract chunks | ~103,989 (60%) |
| Case law chunks |  ~70,679 (40%) |
| Vector size     | 768 dimensions |
| Distance metric |         Cosine |

### Data Sources

| Type      | Source                                                   |
| --------- | -------------------------------------------------------- |
| Contracts | Stanford MCC — 1M+ SEC EDGAR filings from 2000–2023      |
| Case Law  | Harvard Caselaw Access Project — 6.7M US court decisions |

---

## Corpus Ingestion

Run the ingestion pipeline:

```bash
python -m ai.rag.corpus_ingestion
```

Place source files in:

```text
ai/data/corpus/contracts/    # PDF or HTML contract files
ai/data/corpus/case_law/     # PDF or HTML case law files
```

The pipeline chunks, embeds, extracts metadata via GPT-4o, and upserts to Qdrant Cloud.

---

## Migration and Deduplication

### How `doc_id` Works

Each ingested document gets a UUID `doc_id` generated once at ingestion time. All chunks from the same source file share this `doc_id`.

For example, a PDF with 50 chunks produces 50 Qdrant points. Each point has the same `doc_id` in its payload but a different numeric point ID.

Point IDs are assigned sequentially starting from the current collection count:

```text
current count = 174,668
new file with 50 chunks → point IDs 174,668 to 174,717
```

Qdrant uses upsert rather than insert, so running ingestion twice on the same files with the same point IDs overwrites existing points instead of creating duplicates. This is safe within a single ingestion run.

### Migrating to a Different Vector Database

#### Option 1 — Qdrant Snapshot Recommended

Create a snapshot:

```bash
curl -X POST "https://your-qdrant-url/collections/corpus/snapshots" \
  -H "api-key: your-api-key"
```

The API key and Qdrant URL will be shared by the team at handover.

Restore the `.snapshot` file to any Qdrant instance. All vectors, payloads, and IDs are preserved exactly.

#### Option 2 — Fresh Re-Ingest

1. Update `QDRANT_URL`, `QDRANT_API_KEY`, and `QDRANT_COLLECTION` in `ai/.env`.
2. Wipe the new collection if it exists.
3. Run:

```bash
python -m ai.rag.corpus_ingestion
```

Re-embedding 174k chunks takes significant time. Plan accordingly.

#### Option 3 — Switch Vector DB Entirely

For alternatives such as Pinecone or Weaviate, only `ai/rag/vector_store.py` needs to change. It acts as the abstraction layer.

The embedding model in `embedder.py` is database-agnostic and remains unchanged.

### Deduplication Risk — Snapshot + Fresh Ingest

Do **not** restore a snapshot and then re-run ingestion on top of it.

The snapshot already contains points `0` to `174,667`. Fresh ingestion would start new point IDs from `174,668`, creating a full second copy of all content with different IDs. Qdrant has no content-level deduplication.

Safe migration paths:

* Snapshot restore only, with no re-ingestion.
* Wipe collection first, then re-ingest fresh.

Not implemented:

* Content hash deduplication.
* File-level checks to determine whether a file has already been ingested.

---

## Corpus Data — Licensing and Public Use

The legal knowledge base is built from two fully open, publicly available datasets.

### Contracts — Stanford Multi-Document Contract Corpus (MCC)

| Field    | Description                                                                                                                      |
| -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Source   | Stanford Law School                                                                                                              |
| Origin   | 1M+ commercial contracts filed with the US SEC via EDGAR from 2000–2023                                                          |
| License  | Underlying contracts are US public records filed with a federal agency and are freely available for research and commercial use. |
| Coverage | NDAs, employment agreements, purchase agreements, master services agreements, licensing deals, and more.                         |

### Case Law — Harvard Caselaw Access Project

| Field            | Description                                                                                                          |
| ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| Source           | Harvard Law School                                                                                                   |
| Coverage         | 6.7 million US court decisions spanning 1685–2020 across all state and federal jurisdictions.                        |
| License          | Fully open access since March 2024; all restrictions lifted. Free to use, reproduce, and build upon for any purpose. |
| Why this matters | Prior to March 2024, bulk access required a research agreement. The dataset is now unrestricted.                     |

### Why These Sources

Both datasets cover US law, which aligns with the chatbot's primary jurisdiction focus.

The legal embedding model, `sbert-legal-xlm-roberta-base`, was fine-tuned on legal text from similar sources. As a result, the embeddings and corpus are semantically aligned, improving retrieval accuracy compared with a general-purpose corpus.

---

## Notes

* **Windows:** Always set `$env:PYTHONPATH="ai"` before running `uvicorn`.
* **First run:** The embedding model, approximately 737 MB, downloads on first startup and is cached.
* **OpenAI key required:** GPT-4o is used for reasoning, summarization, and tutoring. Without a valid key, all queries will fail.
* **AWS S3 required:** Document upload and PDF extraction depend on S3. Documents are never stored locally.
* **LangSmith:** Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` to enable pipeline observability.
* **KB Audit:** LLM3 self-assessment KB audit is disabled by default. Enable it with `KB_AUDIT_ENABLED=true`.
* **Seed courses:** After first Docker startup, run `python manage.py seed_courses` once to populate the tutoring service course catalog.
* **RAG fails silently:** If Qdrant is unavailable, the RAG node returns an empty list and the pipeline continues. Reasoning falls back to general legal knowledge.
