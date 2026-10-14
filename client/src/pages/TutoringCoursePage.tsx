import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, BookOpen, CircleDot } from "lucide-react";
import PageTransition from "@/components/PageTransition";
import { Button } from "@/components/ui/button";
import { getStoredUserId } from "@/lib/auth";
import { fetchCourseDetail, fetchLessonContent, fetchModuleProgress } from "@/features/courses/api";
import type { CourseDetail } from "@/features/courses/types";
import { cn } from "@/lib/utils";
import "@/features/home/styles/home.css";

function sortByOrder<T extends { order: number }>(items: T[]): T[] {
  return [...items].sort((a, b) => a.order - b.order);
}

export default function TutoringCoursePage() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const userId = getStoredUserId();

  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [completedLessonIds, setCompletedLessonIds] = useState<Set<string>>(new Set());
  const [moduleProgressById, setModuleProgressById] = useState<Record<string, number>>({});

  const load = useCallback(async () => {
    if (!courseId) return;
    setLoading(true);
    setError(null);
    const { response, payload } = await fetchCourseDetail(courseId);
    if (!response.ok || payload?.status !== "success" || !payload.data) {
      setCourse(null);
      setError(payload?.message || `Could not load course (HTTP ${response.status}).`);
      setLoading(false);
      return;
    }
    setCourse(payload.data);
    setLoading(false);
  }, [courseId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const resolvedCourseId = courseId ?? "";
    const resolvedUserId = userId ?? "";
    if (!resolvedCourseId || !resolvedUserId) return;
    let cancelled = false;

    async function loadModuleProgress() {
      const { response, payload } = await fetchModuleProgress(resolvedCourseId, resolvedUserId);
      if (!response.ok || payload?.status !== "success" || !payload.data) {
        if (!cancelled) setModuleProgressById({});
        return;
      }
      const next = Object.fromEntries(
        payload.data.modules.map((m) => [m.module_id, m.progress_percent]),
      ) as Record<string, number>;
      if (!cancelled) setModuleProgressById(next);
    }

    void loadModuleProgress();
    return () => {
      cancelled = true;
    };
  }, [courseId, userId]);

  const modulesSorted = useMemo(() => {
    if (!course?.modules) return [];
    return sortByOrder(course.modules).map((m) => ({
      ...m,
      lessons: sortByOrder(m.lessons),
    }));
  }, [course]);

  const totalLessonCount = useMemo(
    () => modulesSorted.reduce((sum, module) => sum + module.lessons.length, 0),
    [modulesSorted],
  );

  const completedLessonCount = completedLessonIds.size;
  const isCourseCompleted = totalLessonCount > 0 && completedLessonCount === totalLessonCount;

  useEffect(() => {
    if (!userId) return;
    if (!modulesSorted.length) {
      setCompletedLessonIds(new Set());
      return;
    }

    const uid = userId;
    const allLessonIds = modulesSorted.flatMap((m) => m.lessons.map((l) => l.lesson_id));
    const uniqueLessonIds = Array.from(new Set(allLessonIds));

    let cancelled = false;

    async function loadCompletionStatus() {
      try {
        const nextCompleted = new Set<string>();

        // Limit concurrency to avoid overwhelming the backend.
        const concurrency = 4;
        let cursor = 0;

        async function worker() {
          while (cursor < uniqueLessonIds.length) {
            const lessonId = uniqueLessonIds[cursor++];
            const { response, payload } = await fetchLessonContent(lessonId, uid);

            if (response.ok && payload?.status === "success" && payload.data?.completed) {
              nextCompleted.add(lessonId);
            }
          }
        }

        await Promise.all(
          Array.from({ length: Math.min(concurrency, uniqueLessonIds.length) }, () => worker()),
        );

        if (!cancelled) setCompletedLessonIds(nextCompleted);
      } finally {
        // no-op
      }
    }

    void loadCompletionStatus();

    return () => {
      cancelled = true;
    };
  }, [modulesSorted, userId]);

  if (!userId) {
    return <Navigate to="/log-in" replace />;
  }

  if (!courseId) {
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
            onClick={() => navigate("/tutoring")}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to courses
          </Button>

          {loading ? (
            <p className="text-sm text-[var(--home-muted)]">Loading course…</p>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : course ? (
            <>
              <p className="text-xs font-medium uppercase tracking-wide text-[var(--home-muted)]">
                {course.legal_topic}
              </p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--home-fg)] md:text-4xl">
                {course.title}
              </h1>
              <p className="mt-4 text-[15px] leading-relaxed text-[var(--home-muted)]">{course.description}</p>
              <p className="mt-3 text-xs text-[var(--home-muted)]">
                Pass threshold: {Math.round(course.pass_threshold * 100)}%
              </p>

              <section className="mt-12">
                <h2 className="text-lg font-semibold text-[var(--home-fg)]">Modules & lessons</h2>
                <ol className="mt-6 space-y-8">
                  {modulesSorted.map((mod, modIdx) => (
                    <li key={mod.module_id}>
                      <div
                        className={cn(
                          "rounded-2xl border border-[var(--home-chip-border)] bg-[var(--home-chip-bg)] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.03)]",
                          "ring-1 ring-amber-500/25 dark:ring-amber-400/20",
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--home-pill-icon-bg)] text-sm font-semibold text-[var(--home-fg)]">
                            {modIdx + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <h3 className="flex items-center gap-2 text-base font-semibold text-[var(--home-fg)]">
                              <BookOpen className="h-4 w-4 shrink-0 opacity-70" aria-hidden />
                              {mod.title}
                            </h3>
                            <div className="mt-3">
                              <div className="flex items-center justify-between text-xs text-[var(--home-muted)]">
                                <span>Progress</span>
                                <span>{moduleProgressById[mod.module_id] ?? 0}%</span>
                              </div>
                              <div className="mt-2 h-2 w-full rounded-full bg-black/10 dark:bg-white/10">
                                <div
                                  className="h-2 rounded-full bg-emerald-500 dark:bg-emerald-400"
                                  style={{ width: `${moduleProgressById[mod.module_id] ?? 0}%` }}
                                />
                              </div>
                            </div>
                            <ol className="mt-4 space-y-3 border-l-2 border-[var(--home-chip-border)] pl-4">
                              {mod.lessons.map((lesson, i) => (
                                <li key={lesson.lesson_id}>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      navigate(
                                        `/tutoring/course/${courseId}/lesson/${lesson.lesson_id}`,
                                      )
                                    }
                                    className={cn(
                                      "w-full rounded-xl border border-transparent px-3 py-2 text-left transition hover:bg-[var(--home-card)] hover:border-[var(--home-chip-border)]",
                                    )}
                                  >
                                    <div className="flex items-start gap-2">
                                      <CircleDot
                                        className={cn(
                                          "mt-0.5 h-3.5 w-3.5 shrink-0",
                                          completedLessonIds.has(lesson.lesson_id)
                                            ? "text-green-600 dark:text-green-400"
                                            : "text-[var(--home-muted)]",
                                        )}
                                        aria-hidden
                                      />
                                      <div className="min-w-0 flex-1">
                                        <p className="text-sm font-medium text-[var(--home-fg)]">
                                          {i + 1}. {lesson.title}
                                        </p>
                                        {Array.isArray(lesson.learning_objectives) &&
                                        lesson.learning_objectives.length > 0 ? (
                                          <ul className="mt-1.5 list-disc space-y-0.5 pl-4 text-xs text-[var(--home-muted)]">
                                            {lesson.learning_objectives.map((obj, oi) => (
                                              <li key={`${lesson.lesson_id}-obj-${oi}`}>{obj}</li>
                                            ))}
                                          </ul>
                                        ) : null}
                                        {/* <p className="mt-1 text-[11px] text-[var(--home-muted)]">
                                          {lesson.content_available
                                            ? "Content ready"
                                            : "Content on first open"}
                                        </p> */}
                                      </div>
                                    </div>
                                  </button>
                                </li>
                              ))}
                            </ol>
                          </div>
                        </div>
                      </div>
                    </li>
                  ))}
                </ol>
                {modulesSorted.length === 0 ? (
                  <p className="mt-4 text-sm text-[var(--home-muted)]">No modules in this course yet.</p>
                ) : null}
              </section>

              {isCourseCompleted ? (
                <section className="mt-10 rounded-3xl border border-emerald-500/30 bg-emerald-50/70 p-6 shadow-[0_10px_24px_rgba(0,0,0,0.05)] dark:bg-emerald-950/20">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800 dark:text-emerald-300">
                    Final step
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-[var(--home-fg)]">
                    You finished the lessons for this level.
                  </h2>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--home-muted)]">
                    Take the course assessment to record your score and open the next lesson level.
                  </p>
                  <Button
                    type="button"
                    className="mt-5 bg-[var(--home-button-bg)] text-[var(--home-button-fg)] hover:bg-[var(--home-fg)]/90"
                    onClick={() => navigate(`/tutoring/course/${courseId}/assessment`)}
                  >
                    Start final assessment
                  </Button>
                </section>
              ) : null}
            </>
          ) : null}

          <p className="mt-10 text-center text-xs text-[var(--home-muted)]">
            <Link to="/tutoring" className="underline underline-offset-2 hover:text-[var(--home-fg)]">
              Return to tutoring home
            </Link>
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
