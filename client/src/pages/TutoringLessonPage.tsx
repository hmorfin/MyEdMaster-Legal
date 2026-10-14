import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, CircleDot, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import PageTransition from "@/components/PageTransition";
import { Button } from "@/components/ui/button";
import { getStoredUserId } from "@/lib/auth";
import { completeLesson, fetchLessonContent } from "@/features/courses/api";
import type { LessonContent } from "@/features/courses/types";
import "@/features/home/styles/home.css";

export default function TutoringLessonPage() {
  const { courseId, lessonId } = useParams<{ courseId: string; lessonId: string }>();
  const navigate = useNavigate();
  const userId = getStoredUserId();

  const [lessonLoading, setLessonLoading] = useState(true);
  const [lessonError, setLessonError] = useState<string | null>(null);
  const [lesson, setLesson] = useState<LessonContent | null>(null);

  const contentScrollRef = useRef<HTMLDivElement | null>(null);
  const [canMarkComplete, setCanMarkComplete] = useState(false);
  const [markCompleteLoading, setMarkCompleteLoading] = useState(false);
  const [markCompleteError, setMarkCompleteError] = useState<string | null>(null);

  const completedStorageKey = useMemo(() => {
    if (!userId || !lessonId) return null;
    return `legal_chatbot_completed_lesson_${userId}_${lessonId}`;
  }, [userId, lessonId]);

  const loadLesson = useCallback(async () => {
    if (!lessonId || !userId) return;

    setLessonLoading(true);
    setLessonError(null);
    setLesson(null);
    setCanMarkComplete(false);
    setMarkCompleteError(null);
    setMarkCompleteLoading(false);

    const { response, payload } = await fetchLessonContent(lessonId, userId);
    if (!response.ok || payload?.status !== "success" || !payload.data) {
      setLesson(null);
      setLessonError(payload?.message || `Could not load lesson (HTTP ${response.status}).`);
      setLessonLoading(false);
      return;
    }

    setLesson(payload.data);
    setLessonLoading(false);
  }, [lessonId, userId]);

  useEffect(() => {
    void loadLesson();
  }, [loadLesson]);

  // Enable "Mark complete" only after the user scrolls to the bottom of the content.
  useEffect(() => {
    if (!lesson || lesson.completed) {
      setCanMarkComplete(false);
      return;
    }

    const el = contentScrollRef.current;
    if (!el) return;

    const thresholdPx = 24;
    const check = () => {
      const remaining = el.scrollHeight - el.scrollTop - el.clientHeight;
      setCanMarkComplete(remaining <= thresholdPx);
    };

    check();
    el.addEventListener("scroll", check);
    return () => el.removeEventListener("scroll", check);
  }, [lesson?.lesson_id, lesson?.content, lesson?.completed]);

  const handleMarkComplete = useCallback(async () => {
    if (!lessonId || !userId) return;
    if (!lesson || lesson.completed) return;
    if (!completedStorageKey) return;

    setMarkCompleteLoading(true);
    setMarkCompleteError(null);

    const { response, payload } = await completeLesson(lessonId, userId);

    if (response.ok && payload?.status === "success") {
      try {
        localStorage.setItem(completedStorageKey, "true");
      } catch {
        // Ignore localStorage issues; UI will still update based on API response.
      }

      setLesson((prev) => (prev ? { ...prev, completed: true } : prev));
      setCanMarkComplete(false);
      setMarkCompleteLoading(false);
      navigate(`/tutoring/course/${courseId}/lesson/${lessonId}/quiz`);
      return;
    }

    setMarkCompleteError(payload?.message || `Could not mark complete (HTTP ${response.status}).`);
    setMarkCompleteLoading(false);
  }, [completedStorageKey, lesson, lessonId, userId]);

  const backToCourseHref = useMemo(() => {
    if (!courseId) return "/tutoring";
    return `/tutoring/course/${courseId}`;
  }, [courseId]);

  if (!userId) {
    return <Navigate to="/log-in" replace />;
  }

  if (!courseId || !lessonId) {
    return <Navigate to="/tutoring" replace />;
  }

  return (
    <PageTransition>
      <div className="home-theme min-h-screen overflow-x-hidden bg-[var(--home-bg)] text-[var(--home-fg)]">
        <div className="mx-auto max-w-3xl px-6 py-10 md:py-16">
          <Button
            type="button"
            variant="ghost"
            className="mb-6 -ml-2 gap-2 text-[var(--home-muted)] hover:text-[var(--home-fg)]"
            onClick={() => navigate(backToCourseHref)}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to course
          </Button>

          {lessonLoading ? (
            <p className="text-sm text-[var(--home-muted)]">Loading lesson…</p>
          ) : lessonError ? (
            <p className="text-sm text-red-600">{lessonError}</p>
          ) : lesson ? (
            <>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--home-muted)]">
                {lesson.course_title} • {lesson.module_title}
              </p>

              <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--home-fg)] md:text-4xl">
                {lesson.title}
              </h1>

              <div className="mt-5 rounded-2xl border border-[var(--home-chip-border)] bg-[var(--home-chip-bg)] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.03)]">
                <h2 className="text-lg font-semibold text-[var(--home-fg)]">Learning objectives</h2>
                {Array.isArray(lesson.learning_objectives) && lesson.learning_objectives.length > 0 ? (
                  <ul className="mt-3 space-y-2 pl-4">
                    {lesson.learning_objectives.map((obj, idx) => (
                      <li key={`${lesson.lesson_id}-obj-${idx}`} className="flex items-start gap-2 text-sm text-[var(--home-muted)]">
                        <CircleDot className="mt-1 h-3.5 w-3.5 shrink-0 text-[var(--home-muted)]" aria-hidden />
                        <span>{obj}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-[var(--home-muted)]">No objectives provided.</p>
                )}
              </div>

              <section className="mt-10">
                <h2 className="text-lg font-semibold text-[var(--home-fg)]">Lesson content</h2>
                <div className="mt-4 rounded-2xl border border-[var(--home-chip-border)] bg-[var(--home-chip-bg)] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.03)]">
                  <div ref={contentScrollRef} className="max-h-[420px] overflow-y-auto">
                    <div className="text-sm leading-7 text-[var(--home-fg)]">
                      <ReactMarkdown
                        components={{
                          h1: ({ children }) => (
                            <h1 className="mb-4 text-2xl font-bold tracking-tight text-[var(--home-fg)]">
                              {children}
                            </h1>
                          ),
                          h2: ({ children }) => (
                            <h2 className="mb-3 mt-8 text-xl font-semibold text-[var(--home-fg)] first:mt-0">
                              {children}
                            </h2>
                          ),
                          h3: ({ children }) => (
                            <h3 className="mb-3 mt-6 text-lg font-semibold text-[var(--home-fg)] first:mt-0">
                              {children}
                            </h3>
                          ),
                          p: ({ children }) => (
                            <p className="mb-4 whitespace-pre-wrap text-[var(--home-fg)] last:mb-0">
                              {children}
                            </p>
                          ),
                          ul: ({ children }) => (
                            <ul className="mb-4 ml-5 list-disc space-y-2 marker:text-[var(--home-muted)]">
                              {children}
                            </ul>
                          ),
                          ol: ({ children }) => (
                            <ol className="mb-4 ml-5 list-decimal space-y-2 marker:font-semibold marker:text-[var(--home-muted)]">
                              {children}
                            </ol>
                          ),
                          li: ({ children }) => <li className="pl-1 text-[var(--home-fg)]">{children}</li>,
                          strong: ({ children }) => <strong className="font-semibold text-[var(--home-fg)]">{children}</strong>,
                          em: ({ children }) => <em className="italic">{children}</em>,
                          a: ({ children, href }) => (
                            <a
                              href={href}
                              target="_blank"
                              rel="noreferrer"
                              className="font-medium text-[var(--home-button-bg)] underline underline-offset-2"
                            >
                              {children}
                            </a>
                          ),
                          code: ({ children }) => (
                            <code className="rounded bg-black/5 px-1.5 py-0.5 font-mono text-[0.9em] dark:bg-white/10">
                              {children}
                            </code>
                          ),
                          blockquote: ({ children }) => (
                            <blockquote className="mb-4 border-l-2 border-[var(--home-chip-border)] pl-4 italic text-[var(--home-muted)]">
                              {children}
                            </blockquote>
                          ),
                        }}
                      >
                        {lesson.content || ""}
                      </ReactMarkdown>
                    </div>
                  </div>

                  {!lesson.completed && canMarkComplete ? (
                    <div className="mt-4 flex flex-col items-start gap-2">
                      <Button
                        type="button"
                        disabled={markCompleteLoading}
                        className="bg-[var(--home-button-bg)] text-[var(--home-button-fg)] hover:bg-[var(--home-fg)]/90"
                        onClick={() => void handleMarkComplete()}
                      >
                        {markCompleteLoading ? "Starting quiz…" : "Finish lesson & start quiz"}
                      </Button>
                      {markCompleteError ? (
                        <p className="text-sm text-red-600" role="alert">
                          {markCompleteError}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>

                {lesson.completed ? (
                  <div className="mt-4 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
                    <p className="inline-flex items-center gap-2 text-xs font-medium text-emerald-700 dark:text-emerald-300">
                      <Check className="h-3.5 w-3.5" aria-hidden />
                      Completed
                    </p>
                    <Button
                      type="button"
                      size="sm"
                      className="bg-[var(--home-button-bg)] text-[var(--home-button-fg)] hover:bg-[var(--home-fg)]/90"
                      onClick={() => navigate(`/tutoring/course/${courseId}/lesson/${lessonId}/quiz`)}
                    >
                      <Sparkles className="h-4 w-4" aria-hidden />
                      Open quiz
                    </Button>
                  </div>
                ) : null}
              </section>

              <p className="mt-10 text-center text-xs text-[var(--home-muted)]">
                <Link
                  to="/tutoring"
                  className="underline underline-offset-2 hover:text-[var(--home-fg)]"
                >
                  Return to tutoring home
                </Link>
              </p>
            </>
          ) : null}
        </div>
      </div>
    </PageTransition>
  );
}
