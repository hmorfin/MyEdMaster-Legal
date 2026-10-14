# Personalized Legal Chatbot

An AI-powered full-stack legal assistant that helps users understand their legal rights, review contracts, and get answers to legal questions — grounded in real case law and curated legal knowledge. Built with a microservices architecture, fully containerized via Docker.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Docker Setup](#docker-setup)
- [API Endpoints](#api-endpoints)
- [How the AI Pipeline Works](#how-the-ai-pipeline-works)
- [Notes](#notes)

---

## Features

- **Personalized legal Q&A** — responses tailored to the user's jurisdiction, profession, knowledge level, and conversation history
- **Self-assessment driven personalization** — users complete a four-dimension FSPR self-assessment before chatting; the AI injects their knowledge gaps and priority focus into every response
- **Multi-document PDF support** — upload one or more PDFs per query; the AI extracts and reasons over all of them
- **RAG-powered retrieval** — semantic search over 174k legal document chunks (contracts + case law) using a domain-specific legal embedding model
- **PII anonymization** — all user text and document content is stripped of personal identifiers before reaching the LLM
- **Async rolling summarization** — conversation history is compressed into a rolling summary after a token threshold, preventing context loss across long sessions without token bloat
- **Gotcha questioning** — the AI proactively surfaces risks, traps, and things the other party may not want the user to know
- **Topic mastery tracking** — per-user mastery scores per legal topic, updated after every interaction
- **Structured legal tutoring** — 20 legal domains × 3 levels (beginner / intermediate / advanced) with LLM-generated lesson content, MCQ assessments, and personalized feedback
- **FSPR knowledge tracking** — per-exchange knowledge profile updates across Facts, Strategies, Procedures, and Rationales dimensions
- **LangSmith observability** — full pipeline tracing and LLM call monitoring
- **User authentication and chat history** — full user profile management with conversation persistence
- **Fully containerized** — one command to spin up the entire stack locally

---

## Architecture

The system is split into three independent services that communicate over a shared Docker network:

```
User (Browser)
      │  HTTP
      ▼
React Frontend (Vite) — port 5173
      │  REST API
      ▼
Django Backend — port 8000
  ├── User & auth management
  ├── Document upload → AWS S3
  ├── Preprocessing pipeline (sanitize → context fetch → summarization check)
  ├── Conversation & message persistence → MongoDB
  ├── Self-assessment flow (KB generation + FSPR evaluation)
  ├── Tutoring service (courses, lessons, assessments, progress)
  ├── Async rolling summarization (background thread)
  └── AI service proxy
              │  HTTP
              ▼
        FastAPI AI Service — port 8001
          ├── LangGraph Pipeline (main chat)
          │     ├── RAG Node           (Qdrant semantic search)
          │     ├── Extraction Node    (PDF fetch from S3)
          │     ├── Anonymization Node (Microsoft Presidio PII removal)
          │     ├── Reasoning Node     (GPT-4o — unified clarification + legal analysis)
          │     └── Formatter Node     (final answer assembly)
          ├── Summarization Utility    (async, called by Django background thread)
          ├── Self-Assessment Pipeline (4-LLM KB generation + FSPR evaluation)
          ├── Tutoring Pipelines       (lesson, assessment, feedback — each with formatter)
          └── FSPR Inference           (per-exchange knowledge profile updates)
```

The frontend never calls the AI service directly — all traffic flows through Django, which handles auth, preprocessing, document management, and message persistence before delegating to the AI service.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite |
| Backend | Django 6.0 + Django REST Framework + django-mongodb-backend |
| AI Service | FastAPI + Uvicorn |
| AI Orchestration | LangGraph + LangChain |
| LLM (main) | OpenAI GPT-4o |
| LLM (FSPR inference) | OpenAI GPT-4o-mini |
| Embeddings | `Stern5497/sbert-legal-xlm-roberta-base` (legal domain model, 768-dim) |
| Vector Store | Qdrant Cloud |
| Anonymization | Microsoft Presidio + spaCy `en_core_web_lg` |
| Database | MongoDB |
| Object Storage | AWS S3 |
| Observability | LangSmith |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
├── client/                        # React + Vite + TypeScript frontend
│   ├── src/
│   │   ├── pages/                 # One file per page/route
│   │   ├── features/              # Feature modules (chat, courses, onboarding, auth)
│   │   ├── components/            # Shared components + shadcn/ui primitives
│   │   ├── lib/                   # API client, auth, utilities
│   │   └── routes/                # React Router route definitions
│   ├── .env                       # VITE_DJANGO_PROXY_TARGET
│   └── Dockerfile
│
├── backend/                       # Django REST API
│   ├── config/
│   │   ├── settings.py            # Django settings
│   │   └── urls.py                # Root URL configuration
│   ├── apps/
│   │   ├── users/                 # User registration, login, profile
│   │   ├── chat/                  # Chat sessions, messages, self-assessment, preprocessing
│   │   │   ├── models.py          # Conversation, Message, TopicMastery
│   │   │   ├── views.py           # send_message, chat_session, self-assessment views
│   │   │   ├── masterPipeline.py  # Preprocessing orchestrator
│   │   │   └── preprocessingUtilityFunctions.py  # Sanitize, context fetch, summarization threshold
│   │   ├── courses/               # Tutoring service — courses, lessons, assessments, progress
│   │   │   ├── models.py          # Course, Module, Lesson, Enrollment, LessonProgress, Assessment
│   │   │   ├── views.py           # Course catalog, enrollment, lesson delivery, assessment scoring
│   │   │   └── management/commands/seed_courses.py
│   │   ├── documents/             # Document upload, S3 storage
│   │   └── mongo_db_config.py     # PyMongo collections (knowledge_base, self_assessments)
│   ├── ai_client.py               # HTTP client for all AI service calls
│   ├── requirements.txt
│   ├── .env
│   └── Dockerfile
│
├── ai/                            # FastAPI AI microservice
│   ├── main.py                    # FastAPI app entry point + lifespan
│   ├── config.py                  # Pydantic settings
│   ├── legal_topics.py            # 20 predefined legal domain topics
│   ├── graph/
│   │   ├── state.py               # LegalChatState TypedDict
│   │   ├── nodes.py               # 5 pipeline nodes + run_summarization utility
│   │   ├── builder.py             # LangGraph compilation (linear 5-node graph)
│   │   ├── prompts.py             # LEGAL_ADVISOR_PROMPT, LEGAL_ADVISOR_PROMPT_NO_FSPR, SUMMARIZATION_PROMPT
│   │   ├── course_nodes.py        # Tutoring nodes + formatter nodes
│   │   ├── course_builder.py      # Three tutoring LangGraph pipelines
│   │   └── course_state.py        # TypedDicts for tutoring pipelines
│   ├── routers/
│   │   ├── query.py               # POST /query, POST /query/summarize, POST /query/search
│   │   ├── ingest.py              # POST /ingest/upload, DELETE /ingest/{doc_id}
│   │   ├── courses.py             # POST /learning/lessons/generate, /assessments/*, /feedback
│   │   └── fspr.py                # POST /fspr/infer
│   ├── self_assessment/           # 4-LLM self-assessment pipeline
│   ├── document_extraction/       # PyMuPDF + S3 presigned URL fetcher
│   ├── anonymization/             # Presidio PII detection and replacement
│   ├── rag/                       # Embedding model + Qdrant wrapper + corpus ingestion
│   ├── requirements.txt
│   ├── .env
│   └── Dockerfile
│
└── docker-compose.yml             # Full stack orchestration
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) v4.0+ (includes Docker Compose v2)
- An [OpenAI API key](https://platform.openai.com/account/api-keys)
- AWS S3 bucket with credentials (for document upload and PDF extraction)
- Qdrant Cloud account (for vector database)

> No Python, Node.js, or any other local runtime required — everything runs inside containers.

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Mrunal2148/ser517-industry-9-personalized-legal-chatbot.git
cd ser517-industry-9-personalized-legal-chatbot
```

### 2. Set up environment variables

```bash
cp backend/.env.example backend/.env
cp ai/.env.example ai/.env
```

Fill in your credentials in each `.env` file — see the [Environment Variables](#environment-variables) section for the full list.

### 3. Start all services

```bash
docker compose --profile app up --build
```

Use `--build` the first time, or anytime dependencies or Dockerfiles change. For normal subsequent runs:

```bash
docker compose --profile app up
```

This starts all four services (frontend, backend, AI service, MongoDB). On first run, the legal embedding model (~737MB) downloads and caches automatically — this only happens once.

Once running, open **http://localhost:5173** in your browser.

### 4. Seed the course catalog (first time only)

In a new terminal after services are running:

```bash
docker compose exec backend python manage.py seed_courses
```

This populates courses for all 20 legal domains × 3 levels. Only needs to run once.

### 5. Stop all services

```bash
docker compose --profile app down
```

### 6. Full cleanup (fresh start)

```bash
docker compose --profile app down -v
docker system prune -f
docker compose --profile app up --build
```

> `down -v` deletes MongoDB data and the cached embedding model. The model will re-download (~737MB) on next startup.

---

## Environment Variables

### `backend/.env`

| Variable | Description | Example |
|---|---|---|
| `MONGODB_URI` | MongoDB connection string | `mongodb://local_mongodb:27017` |
| `MONGODB_HOST` | MongoDB hostname | `local_mongodb` |
| `MONGODB_DB_NAME` | MongoDB database name | `legal_chatbot_db` |
| `AI_SERVICE_URL` | Internal URL of the AI service | `http://ai:8001` |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `...` |
| `AWS_STORAGE_BUCKET_NAME` | S3 bucket for document storage | `your-bucket-name` |
| `AWS_S3_REGION_NAME` | S3 bucket region | `us-east-1` |

### `ai/.env`

| Variable | Description | Example |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o | `sk-proj-...` |
| `OPENAI_MODEL` | OpenAI model | `gpt-4o` |
| `LEGAL_EMBEDDING_MODEL` | HuggingFace legal embedding model | `Stern5497/sbert-legal-xlm-roberta-base` |
| `QDRANT_URL` | Qdrant Cloud URL | `https://...qdrant.io` |
| `QDRANT_API_KEY` | Qdrant Cloud API key | `...` |
| `QDRANT_COLLECTION` | Qdrant collection name | `corpus` |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 presigned URLs | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `...` |
| `S3_BUCKET_NAME` | S3 bucket name | `your-bucket-name` |
| `MONGODB_URI` | MongoDB connection string | `mongodb://mongodb:27017` |
| `MONGODB_DB_NAME` | MongoDB database name | `legal_chatbot_db` |
| `LANGCHAIN_API_KEY` | LangSmith API key (optional) | `ls__...` |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing (optional) | `true` |

### `client/.env`

| Variable | Description | Example |
|---|---|---|
| `VITE_DJANGO_PROXY_TARGET` | Backend URL for Vite dev proxy | `http://backend:8000` |

> **Never commit `.env` files.** They are listed in `.gitignore` by default.

---

## Docker Setup

### Container network

All services run on a shared Docker network. Use container hostnames — never `localhost` — in `.env` files when running in Docker.

| Container | Hostname | Port |
|---|---|---|
| `local_mongodb` | `mongodb` | 27017 |
| `legal-backend` | `backend` | 8000 |
| `legal-ai` | `ai` | 8001 |
| `legal-frontend` | `frontend` | 5173 |

### Volumes

| Volume | Purpose |
|---|---|
| `mongo_data` | Persists MongoDB data across container restarts |
| `ai_model_cache` | Caches the 737MB embedding model after first download |

### Common commands

```bash
# Rebuild a single service after code changes
docker compose up --build backend

# View logs for specific services
docker compose logs -f backend ai

# Restart a service without rebuilding (e.g. after .env change)
docker compose restart ai

# Start only MongoDB (useful for local development)
docker compose up mongodb

# Stop containers only (preserves DB data)
docker compose --profile app down

# Stop containers + wipe volumes (destroys DB and model cache)
docker compose --profile app down -v
```

---

## API Endpoints

### Backend (Django) — `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/users/` | Register a new user |
| POST | `/api/v1/users/login/` | Authenticate user |
| PATCH | `/api/v1/users/:user_id/` | Update user profile |
| GET | `/api/v1/chats/:user_id/` | List all chats for a user |
| POST | `/api/v1/chats/:user_id/` | Create a new chat (triggers KB generation) |
| GET | `/api/v1/chats/:user_id/:chat_id/` | Get chat session details |
| PATCH | `/api/v1/chats/:user_id/:chat_id/` | Rename a chat |
| DELETE | `/api/v1/chats/:user_id/:chat_id/` | Delete a chat |
| GET | `/api/v1/chats/:user_id/:chat_id/messages/` | Fetch messages |
| POST | `/api/v1/chats/:user_id/:chat_id/messages/` | Send a message (supports PDF upload) |
| POST | `/api/v1/chats/:user_id/:chat_id/self-assessment/submit/` | Submit self-assessment |
| POST | `/api/v1/chats/:user_id/:chat_id/self-assessment/skip/` | Skip self-assessment |
| POST | `/api/v1/docs/:user_id/` | Upload a document to S3 |
| GET | `/api/v1/docs/:user_id/` | List documents for a user |
| GET | `/api/v1/courses/` | List all courses |
| GET | `/api/v1/courses/:course_id/` | Course detail with modules and lessons |
| POST | `/api/v1/courses/:course_id/enroll/:user_id/` | Enroll in a course |
| GET | `/api/v1/courses/enrolled/:user_id/` | User's enrolled courses |
| GET | `/api/v1/courses/lessons/:lesson_id/:user_id/` | Get lesson content |
| POST | `/api/v1/courses/lessons/:lesson_id/complete/:user_id/` | Mark lesson complete |
| POST | `/api/v1/courses/assessments/generate/:user_id/` | Generate MCQ assessment |
| POST | `/api/v1/courses/assessments/:assessment_id/submit/:user_id/` | Submit assessment |
| GET | `/api/v1/courses/progress/:user_id/` | Full learning dashboard |

### AI Service (FastAPI) — `http://localhost:8001`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/query` | Run full 5-node LangGraph pipeline |
| POST | `/query/summarize` | Summarize conversation history (called async by Django) |
| POST | `/query/search` | Direct Qdrant semantic search |
| POST | `/learning/lessons/generate` | Generate lesson content |
| POST | `/learning/assessments/generate` | Generate MCQ questions |
| POST | `/learning/assessments/feedback` | Generate assessment feedback |
| POST | `/self-assessment/generate-kb` | Generate personalized knowledge base |
| POST | `/self-assessment/evaluate` | Evaluate FSPR self-assessment submission |
| POST | `/fspr/infer` | Update FSPR knowledge profile |
| POST | `/ingest/upload` | Ingest a document into Qdrant |
| GET | `/health` | Service health check |

> The frontend never calls the AI service directly. All traffic goes through Django.

---

## How the AI Pipeline Works

### Main Chat Pipeline

Every chat message flows through a 5-node linear LangGraph pipeline:

1. **RAG Node** — embeds the query using the legal BERT model and performs semantic search over 174k legal document chunks in Qdrant Cloud (top 5 chunks above 0.75 cosine similarity threshold). Fails silently — returns empty list if unavailable.

2. **Extraction Node** — fetches user-uploaded PDFs from S3 via presigned URLs and extracts text using PyMuPDF. Previously uploaded documents in the same chat are automatically re-fetched for follow-up queries.

3. **Anonymization Node** — runs Microsoft Presidio over the query, document text, and knowledge chunks to strip PII before any data reaches the LLM. Preserves location (jurisdiction) and dollar amounts.

4. **Reasoning Node** — single LLM call that handles clarification, legal analysis, and gotcha questioning simultaneously. Two modes:
   - **FSPR mode** (self-assessment completed) — injects evaluation report, priority knowledge gaps, and knowledge profile into the system prompt
   - **Fallback mode** (self-assessment skipped) — uses topic mastery scores and knowledge level as proxy
   Both modes inject conversation summary and RAG context.

5. **Formatter Node** — returns the LLM answer or a graceful error message.

### Async Summarization

After every LLM response, Django checks if background summarization should trigger (unsummarized tokens > 1500 AND messages since last summary > 6). If triggered, a background thread calls `POST /query/summarize`, compresses older history into a structured summary, and saves it to MongoDB. The next request passes this summary to the reasoning node — full context without token overhead.

### Self-Assessment Pipeline

When a user creates a new chat, Django calls the AI service to run a 4-LLM pipeline that generates a personalized knowledge base. The user then completes a four-dimension FSPR self-assessment. The AI evaluates their submission and produces a priority report that gets injected into every subsequent chat response.

### Tutoring Service

Three independent LangGraph pipelines (lesson → format, assessment → format, feedback → format) generate adaptive content based on user mastery level. Django handles enrollment, progress tracking, caching, and level unlocking (70% pass threshold required to advance).

---

## Notes

- **First run is slow** — the embedding model (~737MB) downloads on first startup. Subsequent runs use the `ai_model_cache` Docker volume.
- **OpenAI key required** — GPT-4o is used for reasoning, summarization, and tutoring. Without a valid key all queries will fail.
- **AWS S3 required** — document upload and PDF extraction depend on S3. Documents are never stored locally.
- **Qdrant Cloud required** — the legal knowledge base lives in Qdrant Cloud. The RAG node will return empty results without a valid connection but the pipeline will continue.
- **Seed courses** — run `python manage.py seed_courses` once after first startup to populate the tutoring course catalog.
- **LangSmith** — set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` in `ai/.env` to enable pipeline observability.
- **Container networking** — use container hostnames (`mongodb`, `backend`, `ai`) in `.env` files, not `localhost`, when running in Docker.
- **Django migrations** — run automatically on backend container startup.