# Legal Chatbot — Backend (Django)

This is the Django REST API backend for the **Personalized Legal Chatbot**. It handles user management, conversation lifecycle, document upload, self-assessment flow, tutoring service, and orchestration between the React frontend and the FastAPI AI service.

The frontend never calls the AI service directly. All traffic flows through Django, which handles authentication, preprocessing, document management, and message persistence before delegating to the AI layer.

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | Django 6.0 + Django REST Framework |
| Database | MongoDB via `django-mongodb-backend` |
| Object Storage | AWS S3 for document upload and PDF storage |
| AI Service Client | `httpx` for HTTP calls to the FastAPI AI service |
| Tokenization | `tiktoken` for summarization threshold token counting |

---

## Quickstart

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create `.env`

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_HOST=localhost
MONGODB_DB_NAME=legal_chatbot_db

AI_SERVICE_URL=http://localhost:8001

AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Seed courses, first time only

```bash
python manage.py seed_courses
```

### 5. Start the server

```bash
python manage.py runserver
```

---

## Project Structure

```text
backend/
├── manage.py
├── ai_client.py                   # HTTP client for all AI service calls
├── requirements.txt
├── Dockerfile
├── .env.example
├── config/
│   ├── settings.py                # Django settings
│   ├── urls.py                    # Root URL configuration
│   ├── asgi.py
│   └── wsgi.py
└── apps/
    ├── mongo_db_config.py         # PyMongo collections: knowledge_base, self_assessments
    ├── users/                     # User registration, login, profile management
    │   ├── models.py              # UserProfile model
    │   ├── views.py               # CreateUserView, LoginView, ModifyUserView
    │   ├── choices.py             # Field choices
    │   └── urls.py
    ├── chat/                      # Core chat, messaging, self-assessment
    │   ├── models.py              # Conversation, Message, TopicMastery
    │   ├── views.py               # send_message, chat_session, self-assessment views
    │   ├── masterPipeline.py      # Preprocessing orchestrator
    │   ├── preprocessingUtilityFunctions.py  # Sanitize, context fetch, summarization threshold
    │   ├── legal_topics.py        # 20 legal domain topics list
    │   └── urls.py
    ├── courses/                   # Tutoring service: courses, lessons, assessments
    │   ├── models.py              # Course, Module, Lesson, Enrollment, LessonProgress, Assessment
    │   ├── views.py               # Course catalog, enrollment, lesson delivery, assessment flow
    │   ├── management/commands/
    │   │   └── seed_courses.py    # Populates course catalog for all 20 legal domains
    │   └── urls.py
    ├── documents/                 # Document upload and S3 storage
    │   ├── models.py              # UserDocument
    │   ├── serializers.py         # DRF serializers
    │   ├── services.py            # CloudStorageService, S3 upload
    │   └── urls.py
    └── vector_db/
        └── client.py              # Qdrant client, legacy; vector DB now managed by AI layer
```

---

## Data Models

### UserProfile

Stores user registration and onboarding data.

| Field | Type | Description |
|---|---|---|
| `first_name` | `CharField` | User's first name. |
| `last_name` | `CharField` | User's last name. |
| `email` | `EmailField` | Unique email address. |
| `phone` | `CharField` | User's phone number. |
| `dob` | `DateField` | Date of birth. |
| `location` | `JSONField` | `{state, county, city}` |
| `user_attributes` | `JSONField` | `{knowledge_level, profession, age_range, ...}` |
| `onboarded` | `BooleanField` | True after profile completion. |

### Conversation

One conversation per chat session. Created when a user starts a new chat and provides their legal situation.

| Field | Type | Description |
|---|---|---|
| `user` | `FK → UserProfile` | Conversation owner. |
| `legal_situation` | `TextField` | User's legal situation intake. |
| `prior_experience` | `TextField` | Prior legal experience. |
| `desired_outcome` | `TextField` | What the user wants to achieve. |
| `jurisdiction` | `CharField` | User's jurisdiction. |
| `chat_name` | `CharField` | Auto-generated from legal domain and situation. |
| `primary_topic` | `CharField` | First detected legal topic, set after first message. |
| `legal_domain` | `CharField` | LLM-classified domain, such as Employment Law. |
| `branch` | `CharField` | LLM-classified branch. |
| `baseline_familiarity` | `CharField` | `low`, `medium`, or `high`. |
| `primary_intent` | `CharField` | Examples: `understand_options`, `take_action`. |
| `self_assessment_status` | `CharField` | `pending`, `completed`, or `skipped`. |
| `conversation_summary` | `TextField` | Rolling summary from async summarization. |
| `last_summarized_message_id` | `CharField` | ID of last message included in summary. |
| `fspr_profile` | `JSONField` | FSPR dimension scores per conversation. |
| `example_text` | `TextField` | Self-assessment reference example. |
| `empty_template` | `JSONField` | Self-assessment blank template. |

### Message

One record per message in a conversation.

| Field | Type | Description |
|---|---|---|
| `conversation` | `FK → Conversation` | Parent conversation. |
| `role` | `CharField` | `user` or `llm`. |
| `content` | `TextField` | Message text. |
| `document_paths` | `JSONField` | S3 paths of documents uploaded with this message. |

### TopicMastery

Tracks per-user mastery score per legal topic. Updated after every chat message.

| Field | Type | Description |
|---|---|---|
| `user` | `FK → UserProfile` | User associated with this mastery record. |
| `topic` | `CharField` | Legal topic name. |
| `mastery_level` | `FloatField` | Score from `0.0` to `1.0`. |

### Course, Module, and Lesson

Three-level hierarchy for the tutoring service.

#### Course

Top-level course. There is one course per legal topic per level: beginner, intermediate, and advanced.

```python
pass_threshold = 0.70
```

This is the minimum assessment score required to unlock the next level.

#### Module

Chapter within a course.

#### Lesson

Individual lesson within a module.

| Field | Description |
|---|---|
| `content` | LLM-generated markdown, cached after first access. |
| `learning_objectives` | JSON list of strings. |

### Enrollment, LessonProgress, and Assessment

These models track user progress through the tutoring service.

| Model | Purpose |
|---|---|
| `Enrollment` | One per user per course. Status is `in_progress` or `completed`. |
| `LessonProgress` | Tracks completion per lesson per user. |
| `Assessment` | Stores questions as JSON, user answers, score, feedback, and `next_action`. |

---

## MongoDB Collections via PyMongo

Two collections are managed directly via PyMongo instead of the Django ORM.

| Collection | Purpose |
|---|---|
| `knowledge_base` | Stores LLM-generated KB per legal domain and jurisdiction. Scoped per conversation to avoid concurrency conflicts. |
| `self_assessments` | Stores FSPR evaluation reports per chat session. |

---

## Preprocessing Pipeline

Every chat message goes through a two-step preprocessing pipeline in `masterPipeline.py` before reaching the AI service.

```text
User query
   │
   ▼
Step 1: sanitize_input()
   │
   ▼
Step 2: fetch_user_context()
   │
   ▼
Preprocessed data passed to send_message()
```

### Step 1: `sanitize_input()`

- Strips whitespace.
- Removes null bytes.
- Enforces `MAX_QUERY_LENGTH`, currently `1000` characters.

### Step 2: `fetch_user_context()`

- Fetches `UserProfile`, including jurisdiction, knowledge level, profession, and mastery scores.
- Fetches messages since the last summarization point instead of full history.
- Counts tokens of unsummarized messages using `tiktoken` with `cl100k_base`.
- Sets `needs_summarization=True` if tokens are greater than `1500` and messages are greater than `6`.
- Returns:
  - `conversation_history`
  - `conversation_summary`
  - `needs_summarization`
  - `messages_to_summarize`
  - `cutoff_message_id`

---

## Message Flow — `send_message()`

Full flow when a user sends a chat message:

1. Validate that the user and conversation exist.
2. Validate uploaded files: PDF only, maximum 10 MB each.
3. Upload files to S3 and save `UserDocument` records.
4. Run the preprocessing pipeline: sanitize input and fetch context.
5. Save user `Message` to MongoDB.
6. Build `self_assessment_context` from `Conversation` and the `self_assessments` collection.
7. Call `ai_client.query()` with:
   - Cleaned query.
   - Conversation history.
   - User context.
   - Document paths, including current and historical paths from the same chat.
   - `self_assessment_context`.
   - `conversation_summary`.
8. Save LLM `Message` to MongoDB.
9. If `needs_summarization`, start a background thread, call `ai_client.summarize()`, and save the new summary to `Conversation`.
10. Update `TopicMastery` scores for detected topics.
11. Set `Conversation.primary_topic` if it is not already set.
12. Return the response to the frontend.

---

## Chat Session Creation Flow

When a user creates a new chat:

1. User provides `legal_situation`, `jurisdiction`, `prior_experience`, and `desired_outcome`.
2. Django calls `ai_client.generate_kb()`, which sends `POST /self-assessment/generate-kb` to the AI service.
3. AI service returns `legal_domain`, `branch`, `baseline_familiarity`, KB content, and `example_text`.
4. Django creates a `Conversation` with all fields populated.
5. Django saves the KB to the `knowledge_base` MongoDB collection using an upsert by domain and jurisdiction.
6. Django returns `chat_id` and `self_assessment_data` to the frontend.

---

## Self-Assessment Flow

```text
User submits self-assessment form
   │
   ▼
POST /api/v1/chats/:user_id/:chat_id/self-assessment/submit/
   │
   ▼
All subsequent chat messages inject FSPR context into the reasoning node
```

### Submit Self-Assessment

`POST /api/v1/chats/:user_id/:chat_id/self-assessment/submit/`

- Validates facts, strategies, procedures, and rationales inputs.
- Fetches KB from the `knowledge_base` MongoDB collection.
- Calls `ai_client.evaluate_self_assessment()`, which sends `POST /self-assessment/evaluate` to the AI service.
- AI returns:
  - `evaluation_report` per dimension.
  - `priority`, the top gap.
- Saves the result to the `self_assessments` MongoDB collection.
- Sets `Conversation.self_assessment_status = "completed"`.

### Skip Self-Assessment

`POST /api/v1/chats/:user_id/:chat_id/self-assessment/skip/`

- Sets `Conversation.self_assessment_status = "skipped"`.
- The reasoning node falls back to intake fields and mastery scores.

---

## AI Service Client

`ai_client.py` is the HTTP client for all AI service calls. All methods raise `AIServiceError` on failure.

| Method | AI Endpoint | Timeout |
|---|---|---:|
| `query()` | `POST /query` | 180s |
| `summarize()` | `POST /query/summarize` | 180s |
| `generate_kb()` | `POST /self-assessment/generate-kb` | 180s |
| `evaluate_self_assessment()` | `POST /self-assessment/evaluate` | 180s |
| `generate_lesson()` | `POST /learning/lessons/generate` | 60s |
| `generate_assessment()` | `POST /learning/assessments/generate` | 45s |
| `generate_assessment_feedback()` | `POST /learning/assessments/feedback` | 30s |
| `health()` | `GET /health` | 5s |

---

## API Endpoints

All endpoints are served on:

```text
http://localhost:8000
```

### Users — `/api/v1/users`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/users/` | Register a new user. |
| POST | `/api/v1/users/login/` | Authenticate user. |
| PATCH | `/api/v1/users/:user_id/` | Update user profile and attributes. |

### Chat — `/api/v1/chats`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/chats/:user_id/` | List all chats for a user. |
| POST | `/api/v1/chats/:user_id/` | Create new chat. Triggers KB generation. |
| GET | `/api/v1/chats/:user_id/:chat_id/` | Get chat session details. |
| PATCH | `/api/v1/chats/:user_id/:chat_id/` | Rename a chat. |
| DELETE | `/api/v1/chats/:user_id/:chat_id/` | Delete chat and all messages. |
| GET | `/api/v1/chats/:user_id/:chat_id/messages/` | Fetch all messages in a chat. |
| POST | `/api/v1/chats/:user_id/:chat_id/messages/` | Send a message. Uses `multipart/form-data` and supports PDF upload. |
| POST | `/api/v1/chats/:user_id/:chat_id/self-assessment/submit/` | Submit self-assessment form. |
| POST | `/api/v1/chats/:user_id/:chat_id/self-assessment/skip/` | Skip self-assessment. |
| GET | `/api/v1/chats/ai/health/` | AI service health check. |

### Documents — `/api/v1/docs`

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/docs/:user_id/` | Upload a document to S3. |
| GET | `/api/v1/docs/:user_id/` | List all documents for a user. |

### Courses — `/api/v1/courses`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/courses/` | List all courses. Supports filtering by topic and level. |
| GET | `/api/v1/courses/:course_id/` | Return full course structure with modules and lessons. |
| POST | `/api/v1/courses/:course_id/enroll/:user_id/` | Enroll user in a course. |
| GET | `/api/v1/courses/enrolled/:user_id/` | List user's enrolled courses with progress. |
| GET | `/api/v1/courses/lessons/:lesson_id/:user_id/` | Get lesson content. Generates if not cached. |
| POST | `/api/v1/courses/lessons/:lesson_id/complete/:user_id/` | Mark lesson as completed. |
| POST | `/api/v1/courses/assessments/generate/:user_id/` | Generate MCQ assessment. |
| POST | `/api/v1/courses/assessments/:assessment_id/submit/:user_id/` | Submit assessment answers. |
| GET | `/api/v1/courses/assessments/history/:user_id/` | User's assessment history. |
| GET | `/api/v1/courses/progress/:user_id/` | Full learning dashboard. |
| GET | `/api/v1/courses/:course_id/progress/:user_id/modules/` | Module-level progress for a course. |

---

## Async Summarization

After every LLM response, Django checks whether background summarization should trigger.

Threshold:

```text
unsummarized message tokens > 1500 AND messages since last summary > 6
```

Example logic:

```python
if needs_summarization and messages_to_summarize and cutoff_message_id:
    threading.Thread(target=run_summarization, daemon=True).start()
```

The background thread:

1. Calls `ai_client.summarize()` with older messages and the existing summary.
2. Saves the new summary to `Conversation.conversation_summary`.
3. Updates `Conversation.last_summarized_message_id` to track the cutoff point.
4. On the next request, `fetch_user_context()` fetches only messages after this cutoff point.

This means the AI layer always receives compact context: a summary of older history plus recent messages only.

---

## Topic Mastery Updates

After every chat message response, Django updates mastery scores:

```python
new_score = round(min(1.0, current_score * 0.8 + confidence_delta * 0.2), 4)
```

After every assessment submission:

```python
new_score = round(min(1.0, mastery.mastery_level * 0.6 + score * 0.4), 4)
```

Assessment scores have a higher weight, `0.4`, than chat confidence deltas, `0.2`, because assessments are a more direct measure of understanding.

---

## Tutoring Service — Level Unlocking

| Level | Unlock Rule |
|---|---|
| Beginner | Always accessible. |
| Intermediate | Requires passing beginner course assessment with score `≥ 70%`. |
| Advanced | Requires passing intermediate course assessment with score `≥ 70%`. |

`_is_level_unlocked()` checks whether a `passed=True` `Assessment` record exists for the prerequisite course before allowing enrollment.

---

## Notes

- **Container networking:** When running in Docker, use `mongodb` as the MongoDB hostname instead of `localhost`. Use `http://ai:8001` as the AI service URL instead of `http://localhost:8001`.
- **Migrations:** Migrations run automatically on container startup via the Dockerfile `CMD`.
- **Seed courses:** Run `python manage.py seed_courses` once after first startup to populate the course catalog.
- **Document upload:** PDFs only, max 10 MB per file. Documents are stored in S3 and never locally.
- **KB storage:** Knowledge base is scoped per conversation, using legal domain and jurisdiction, to avoid concurrency conflicts between simultaneous users.
