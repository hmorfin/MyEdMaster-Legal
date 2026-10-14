import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ArrowLeft, Check, Lock } from "lucide-react";
import PageTransition from "@/components/PageTransition";
import { Button } from "@/components/ui/button";
import { getStoredUserId } from "@/lib/auth";
import { fetchCourseProgress, fetchCourses, fetchEnrolledCourses } from "@/features/courses/api";
import type { CourseProgressItem, CourseSummary } from "@/features/courses/types";
import { compareCourses, isCourseUnlocked } from "@/features/courses/progression";
import { cn } from "@/lib/utils";
import "@/features/home/styles/home.css";

export default function TutoringPage() {
  const navigate = useNavigate();
  const userId = getStoredUserId();

  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [enrolledCourseIds, setEnrolledCourseIds] = useState<Set<string>>(new Set());
  const [courseProgressById, setCourseProgressById] = useState<Record<string, number>>({});
  const [courseStatusById, setCourseStatusById] = useState<Record<string, CourseProgressItem["status"]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [enrolledStatusError, setEnrolledStatusError] = useState<string | null>(null);
  const [progressError, setProgressError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!userId) return;

    setLoading(true);
    setError(null);
    setEnrolledStatusError(null);
    setProgressError(null);

    const [coursesResult, enrolledResult, progressResult] = await Promise.all([
      fetchCourses({}),
      fetchEnrolledCourses(userId),
      fetchCourseProgress(userId),
    ]);

    if (!coursesResult.response.ok || coursesResult.payload?.status !== "success" || !coursesResult.payload.data) {
      setCourses([]);
      setError(coursesResult.payload?.message || `Could not load courses (HTTP ${coursesResult.response.status}).`);
      setLoading(false);
      return;
    }

    setCourses([...coursesResult.payload.data].sort(compareCourses));

    if (
      enrolledResult.response.ok &&
      enrolledResult.payload?.status === "success" &&
      enrolledResult.payload.data
    ) {
      setEnrolledCourseIds(new Set(enrolledResult.payload.data.map((e) => e.course_id)));
    } else {
      setEnrolledCourseIds(new Set());
      setEnrolledStatusError(
        enrolledResult.payload?.message ||
          `Could not load your enrollments (HTTP ${enrolledResult.response.status}).`,
      );
    }

    if (
      progressResult.response.ok &&
      progressResult.payload?.status === "success" &&
      progressResult.payload.data?.topics
    ) {
      const map: Record<string, number> = {};
      const statusMap: Record<string, CourseProgressItem["status"]> = {};
      for (const topic of progressResult.payload.data.topics) {
        for (const course of topic.courses || []) {
          map[course.course_id] = course.progress_percent;
          statusMap[course.course_id] = course.status;
        }
      }
      setCourseProgressById(map);
      setCourseStatusById(statusMap);
    } else {
      setCourseProgressById({});
      setCourseStatusById({});
      setProgressError(
        progressResult.payload?.message ||
          `Could not load course progress (HTTP ${progressResult.response.status}).`,
      );
    }

    setLoading(false);
  }, [userId]);

  useEffect(() => {
    void load();
  }, [load]);

  const sortedCourses = useMemo(() => [...courses].sort(compareCourses), [courses]);

  if (!userId) {
    return <Navigate to="/log-in" replace />;
  }

  return (
    <PageTransition>
      <div className="home-theme min-h-screen overflow-x-hidden bg-[var(--home-bg)] text-[var(--home-fg)]">
        <div className="mx-auto max-w-4xl px-6 py-10 md:py-16">
          <Button
            type="button"
            variant="ghost"
            className="mb-6 -ml-2 gap-2 text-[var(--home-muted)] hover:text-[var(--home-fg)]"
            onClick={() => navigate("/chat")}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to services
          </Button>

          <h1 className="text-3xl font-bold tracking-tight text-[var(--home-fg)] md:text-4xl">Tutoring</h1>
          <p className="mt-4 max-w-5xl border-l-2 border-[var(--home-fg)] pl-4 text-pretty text-[15px] leading-6 text-[var(--home-muted)] md:text-base md:leading-7">
            Finish a level, submit its final assessment, and the next level opens up here automatically.
          </p>

          {enrolledStatusError ? (
            <p className="mt-3 text-sm text-amber-700 dark:text-amber-400">{enrolledStatusError}</p>
          ) : null}
          {progressError ? (
            <p className="mt-2 text-sm text-amber-700 dark:text-amber-400">{progressError}</p>
          ) : null}

          <div className="mt-10">
            {loading ? (
              <p className="text-sm text-[var(--home-muted)]">Loading courses…</p>
            ) : error ? (
              <p className="text-sm text-red-600">{error}</p>
            ) : sortedCourses.length === 0 ? (
              <p className="text-sm text-[var(--home-muted)]">No courses found.</p>
            ) : (
              <ul className="grid gap-4 sm:grid-cols-1 md:grid-cols-2">
                {sortedCourses.map((course) => {
                  const isUnlocked = isCourseUnlocked(course, sortedCourses, userId);
                  const isEnrolled = enrolledCourseIds.has(course.course_id);
                  const progressPctRaw = courseProgressById[course.course_id];
                  const progressPct = Number.isFinite(progressPctRaw)
                    ? Math.max(0, Math.min(100, Math.round(progressPctRaw)))
                    : 0;
                  const status = courseStatusById[course.course_id];
                  const isCompleted = isEnrolled && (status === "completed" || progressPct === 100);

                  const cardClass = cn(
                    "flex h-full flex-col rounded-2xl border p-5 shadow-[0_2px_8px_rgba(0,0,0,0.03)] transition",
                    !isUnlocked
                      ? "border-slate-300 bg-slate-100/80 dark:border-slate-700 dark:bg-slate-900/40"
                      : isCompleted
                        ? "cursor-pointer border-emerald-500/90 bg-emerald-50/60 ring-2 ring-emerald-400/70 hover:brightness-[1.02] dark:border-emerald-600/80 dark:bg-emerald-950/25 dark:ring-emerald-500/50"
                        : "cursor-pointer border-amber-500/90 bg-amber-50/50 ring-2 ring-amber-400/70 hover:brightness-[1.02] dark:border-amber-600/80 dark:bg-amber-950/25 dark:ring-amber-500/50",
                  );

                  const body = (
                    <>
                      <p className="text-xs font-medium uppercase tracking-wide text-[var(--home-muted)]">
                        {course.legal_topic}
                      </p>
                      <p className="mt-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--home-muted)]">
                        {course.level}
                      </p>
                      <h2 className="mt-2 text-lg font-semibold text-[var(--home-fg)]">{course.title}</h2>
                      <p className="mt-2 flex-1 text-sm leading-relaxed text-[var(--home-muted)]">
                        {course.description}
                      </p>

                      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-[var(--home-muted)]">
                        <span>{course.module_count} modules</span>
                        {isUnlocked ? (
                          isCompleted ? (
                            <span className="font-medium text-emerald-800 dark:text-emerald-300">Completed</span>
                          ) : isEnrolled ? (
                            <span className="font-medium text-amber-800 dark:text-amber-300">In progress</span>
                          ) : (
                            <span className="font-medium text-[var(--home-fg)]">Available</span>
                          )
                        ) : (
                          <span className="font-medium text-slate-700 dark:text-slate-300">Locked</span>
                        )}
                      </div>

                      {isEnrolled ? (
                        <div className="mt-4">
                          <div className="flex items-center justify-between text-xs text-[var(--home-muted)]">
                            <span>Progress</span>
                            <span className="font-medium text-[var(--home-fg)]">{progressPct}%</span>
                          </div>
                          <div className="mt-2 h-2 w-full rounded-full bg-black/10 dark:bg-white/10">
                            <div
                              className={cn(
                                "h-2 rounded-full",
                                isCompleted ? "bg-emerald-500 dark:bg-emerald-400" : "bg-amber-500 dark:bg-amber-400",
                              )}
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>
                        </div>
                      ) : null}

                      <div className="mt-4 flex items-center justify-end border-t border-[var(--home-chip-border)] pt-4">
                        {isUnlocked ? (
                          isCompleted ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-600/30 bg-emerald-100/80 px-3 py-1.5 text-sm font-medium text-emerald-950 dark:border-emerald-500/40 dark:bg-emerald-950/50 dark:text-emerald-100">
                              <Check className="h-3.5 w-3.5" aria-hidden />
                              Completed
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-600/30 bg-amber-100/80 px-3 py-1.5 text-sm font-medium text-amber-950 dark:border-amber-500/40 dark:bg-amber-950/50 dark:text-amber-100">
                              <Check className="h-3.5 w-3.5" aria-hidden />
                              Open course
                            </span>
                          )
                        ) : (
                          <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-400/40 bg-slate-200/80 px-3 py-1.5 text-sm font-medium text-slate-800 dark:border-slate-600/40 dark:bg-slate-900/80 dark:text-slate-200">
                            <Lock className="h-3.5 w-3.5" aria-hidden />
                            Finish previous level first
                          </span>
                        )}
                      </div>
                    </>
                  );

                  return (
                    <li key={course.course_id}>
                      {isUnlocked ? (
                        <Link
                          to={`/tutoring/course/${course.course_id}`}
                          className={cn(
                            cardClass,
                            "block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--home-bg)]",
                          )}
                          aria-label={`Open ${course.title}, modules and lessons`}
                        >
                          {body}
                        </Link>
                      ) : (
                        <article className={cardClass}>{body}</article>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>
    </PageTransition>
  );
}
