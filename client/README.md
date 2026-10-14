# Legal Chatbot — Frontend (React + Vite)

This is the React frontend for the **Personalized Legal Chatbot**. It communicates exclusively with the Django backend and never directly with the AI service.

The frontend is built with **React**, **TypeScript**, **Vite**, and **Tailwind CSS**.

---

## Tech Stack

| Component | Technology |
|---|---|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui |
| HTTP Client | Fetch API via `lib/api.ts` |
| Routing | React Router |

---

## Quickstart

### 1. Install dependencies

```bash
cd client
npm install
```

### 2. Create `.env`

```env
VITE_DJANGO_PROXY_TARGET=http://localhost:8000
```

When running locally, set this to:

```text
http://localhost:8000
```

In Docker, this is handled automatically via container networking.

### 3. Start the dev server

```bash
npm run dev
```

The app opens at:

```text
http://localhost:5173
```

---

## Project Structure

```text
client/
├── index.html
├── vite.config.ts                 # Vite config with Django proxy
├── .env                           # VITE_DJANGO_PROXY_TARGET
└── src/
    ├── main.tsx                   # React app entry point
    ├── App.tsx                    # Root component with routing
    ├── index.css                  # Global styles
    │
    ├── assets/images/             # Static images and logos
    │
    ├── pages/                     # One file per page/route
    │   ├── HomePage.tsx           # Landing page
    │   ├── RegisterPage.tsx       # User registration
    │   ├── LogInPage.tsx          # User login
    │   ├── OnboardingPage.tsx     # Profile setup after registration
    │   ├── SuccessPage.tsx        # Post-registration success screen
    │   ├── ChatEntryPage.tsx      # New chat creation: intake form + KB generation
    │   ├── ChatPage.tsx           # Main chat interface
    │   ├── SelfAssessmentPage.tsx # FSPR self-assessment form
    │   ├── TutoringPage.tsx       # Course catalog
    │   ├── TutoringCoursePage.tsx # Course detail with modules
    │   ├── TutoringLessonPage.tsx # Lesson content view
    │   ├── TutoringLessonQuizPage.tsx # MCQ assessment
    │   ├── StatisticsPage.tsx     # User learning statistics
    │   ├── UserProfilePage.tsx    # User profile management
    │   └── SettingsPage.tsx       # App settings
    │
    ├── features/                  # Feature-based modules
    │   ├── auth/
    │   │   └── api.ts             # Login and registration API calls
    │   ├── chat/
    │   │   ├── api.ts             # Chat and message API calls
    │   │   ├── types.ts           # Chat TypeScript types
    │   │   ├── useChatAppData.ts  # Hook: fetches user's chat list
    │   │   ├── useChatMessagesData.ts # Hook: fetches messages for a chat
    │   │   └── components/
    │   │       ├── ChatComposer.tsx      # Message input with file upload
    │   │       ├── ChatMessageItem.tsx   # Single message bubble
    │   │       ├── ChatMessageList.tsx   # Scrollable message thread
    │   │       ├── ChatServiceHub.tsx    # Self-assessment and tutoring links within chat
    │   │       ├── MessageCopyButton.tsx # Copy message to clipboard
    │   │       └── TypewriterText.tsx    # Animated LLM response rendering
    │   ├── courses/
    │   │   ├── api.ts             # Course, lesson, and assessment API calls
    │   │   └── types.ts           # Course TypeScript types
    │   ├── home/
    │   │   └── components/
    │   │       ├── HomeHero.tsx         # Hero section
    │   │       ├── HomeNav.tsx          # Navigation bar
    │   │       └── WhoItsForSection.tsx # Landing page feature highlights
    │   └── onboarding/
    │       ├── api.ts             # Onboarding API calls
    │       ├── constants.ts       # Onboarding field options
    │       ├── types.ts           # Onboarding TypeScript types
    │       ├── utils.ts           # Onboarding helper functions
    │       └── components/
    │           └── OnboardingProfileForm.tsx # Multi-step profile form
    │
    ├── components/                # Shared components used across features
    │   ├── AppSidebar.tsx         # Left sidebar with chat list and navigation
    │   ├── ChatLayout.tsx         # Layout wrapper for chat pages
    │   ├── CreateChatDialog.tsx   # Modal for creating a new chat session
    │   ├── FloatingLines.tsx      # Decorative animated background
    │   ├── LogInForm.tsx          # Login form component
    │   ├── PageTitleProvider.tsx  # Sets browser tab title per page
    │   ├── PageTransition.tsx     # Animated page transitions
    │   ├── RegisterForm.tsx       # Registration form component
    │   ├── RouteTitleManager.tsx  # Manages page titles based on route
    │   ├── SplitText.tsx          # Text animation component
    │   └── ui/                    # shadcn/ui base components
    │       ├── button.tsx
    │       ├── card.tsx
    │       ├── dialog.tsx
    │       ├── input.tsx
    │       ├── tabs.tsx
    │       └── ...                # Other shadcn/ui primitives
    │
    ├── hooks/                     # Shared React hooks
    │   ├── use-async-action.ts    # Hook for async operations with loading/error state
    │   └── use-mobile.ts          # Hook for responsive mobile detection
    │
    ├── lib/                       # Utility modules
    │   ├── api.ts                 # Base API client: headers and base URL
    │   ├── auth.ts                # Auth token storage and retrieval
    │   ├── theme.ts               # Theme configuration
    │   └── utils.ts               # General utility functions
    │
    └── routes/
        └── AppRoutes.tsx          # All route definitions
```

---

## Pages and User Flow

```text
/ (HomePage)
    ↓ Register or Log In

/register (RegisterPage)
    ↓
/onboarding (OnboardingPage)
    ↓
/success (SuccessPage)

/login (LogInPage)
    ↓
/chat (ChatEntryPage)
    └── Create new chat and enter legal situation
    ↓ KB generated, chat created
/chat/:chatId (ChatPage)
    └── Main chat interface
    ↓ optional
/chat/:chatId/self-assessment (SelfAssessmentPage)
    └── FSPR form

/tutoring (TutoringPage)
    └── Course catalog
/tutoring/:courseId (TutoringCoursePage)
    └── Modules and lessons
/tutoring/lesson/:lessonId (TutoringLessonPage)
    └── Lesson content
/tutoring/lesson/:lessonId/quiz (TutoringLessonQuizPage)
    └── MCQ assessment

/statistics (StatisticsPage)
    └── Learning dashboard

/profile (UserProfilePage)
    └── User profile

/settings (SettingsPage)
    └── App settings
```

---

## Key Components

### `ChatComposer`

Message input at the bottom of the chat.

Supports:

- Text input.
- Multiple PDF file attachments.
- Send on Enter or button click.

### `ChatMessageItem`

Renders a single message bubble.

Handles:

- User messages, right aligned.
- LLM messages, left aligned, with markdown rendering.
- Copy-to-clipboard button.

### `TypewriterText`

Animates LLM responses character by character as they appear, giving the impression of real-time generation.

### `AppSidebar`

Left sidebar showing:

- The user's chat sessions.
- Navigation links for Tutoring, Statistics, and Profile.
- Create new chat button.

### `CreateChatDialog`

Modal that collects intake form fields before creating a new chat.

Fields:

- Legal situation.
- Jurisdiction.
- Prior experience.
- Desired outcome.

Submitting the form triggers KB generation on the backend.

### `SelfAssessmentPage`

Four-dimension FSPR form.

Dimensions:

- Facts.
- Strategies.
- Procedures.
- Rationales.

Each dimension includes examples and uncertainties fields.

The form submits to Django, which calls the AI evaluation pipeline.

---

## API Communication

All API calls go through `lib/api.ts`, which sets the base URL and common headers.

The Vite dev server proxies `/api` requests to Django through `vite.config.ts`.

```ts
server: {
  proxy: {
    "/api": {
      target: process.env.VITE_DJANGO_PROXY_TARGET || "http://backend:8000",
      changeOrigin: true,
    },
  },
}
```

In local development, the frontend calls:

```text
/api/v1/...
```

Vite forwards the request to:

```text
http://localhost:8000/api/v1/...
```

In Docker, the proxy target is:

```text
http://backend:8000
```

The frontend never calls the AI service directly.

---

## Notes

- **TypeScript throughout:** All components and API calls are typed.
- **shadcn/ui:** Base UI primitives live in `components/ui/`. Do not edit these directly.
- **Feature-based structure:** Each feature, such as chat, courses, and onboarding, has its own folder with API calls, types, hooks, and components co-located.
- **Markdown rendering:** LLM responses are rendered as markdown, including bold text, bullet points, and headers.
- **Dark mode:** Supported via Tailwind dark mode classes.
- **No direct AI calls:** All requests go through the Django backend.
