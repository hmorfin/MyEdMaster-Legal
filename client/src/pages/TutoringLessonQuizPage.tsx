import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Circle, RotateCcw, Sparkles, Target } from "lucide-react";
import PageTransition from "@/components/PageTransition";
import { Button } from "@/components/ui/button";
import { fetchModuleProgress, generateAssessment, fetchLessonContent, submitAssessment } from "@/features/courses/api";
import type { AssessmentQuestion, AssessmentResult, LessonContent } from "@/features/courses/types";
import { getStoredUserId } from "@/lib/auth";
import { cn } from "@/lib/utils";
import "@/features/home/styles/home.css";

const OPTION_LETTERS = ["A", "B", "C", "D", "E", "F"];

function scoreTone(score: number | null): string {
  if (score === null) return "text-[var(--home-fg)]";
  if (score >= 80) return "text-emerald-700 dark:text-emerald-300";
  if (score >= 60) return "text-amber-700 dark:text-amber-300";
  return "text-rose-700 dark:text-rose-300";
}

export default function TutoringLessonQuizPage() {
  const { courseId, lessonId } = useParams<{ courseId: string; lessonId: string }>();
  const navigate = useNavigate();
  const userId = getStoredUserId();

  const [lesson, setLesson] = useState<LessonContent | null>(null);
  const [lessonLoading, setLessonLoading] = useState(true);
  const [lessonError, setLessonError] = useState<string | null>(null);

  const [quizLoading, setQuizLoading] = useState(true);
  const [quizError, setQuizError] = useState<string | null>(null);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);

  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [results, setResults] = useState<AssessmentResult[] | null>(null);
  const [score, setScore] = useState<number | null>(null);
  const [passed, setPassed] = useState<boolean | null>(null);
  const [feedback, setFeedback] = useState<string>("");
  const [nextAction, setNextAction] = useState<string>("");
  const [courseCompleted, setCourseCompleted] = useState(false);

  const answeredCount = useMemo(() => Object.keys(answers).length, [answers]);
  const canSubmit = questions.length > 0 && answeredCount === questions.length && !results;

  const loadLesson = useCallback(async () => {
    if (!lessonId || !userId) return;

    setLessonLoading(true);
    setLessonError(null);

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

  const loadQuiz = useCallback(async () => {
    if (!lessonId || !userId) return;

    setQuizLoading(true);
    setQuizError(null);
    setSubmitError(null);
    setAssessmentId(null);
    setQuestions([]);
    setAnswers({});
    setResults(null);
    setScore(null);
    setPassed(null);
    setFeedback("");
    setNextAction("");

    const { response, payload } = await generateAssessment(userId, "lesson", lessonId);
    if (!response.ok || payload?.status !== "success" || !payload.data) {
      setQuizError(payload?.message || `Could not generate quiz (HTTP ${response.status}).`);
      setQuizLoading(false);
      return;
    }

    setAssessmentId(payload.data.assessment_id);
    setQuestions(payload.data.questions);
    setQuizLoading(false);
  }, [lessonId, userId]);

  useEffect(() => {
    void loadLesson();
    void loadQuiz();
  }, [loadLesson, loadQuiz]);

  useEffect(() => {
    if (!courseId || !userId) return;
    const resolvedCourseId = courseId;
    const resolvedUserId = userId;

    let cancelled = false;

    async function loadCourseCompletion() {
      const { response, payload } = await fetchModuleProgress(resolvedCourseId, resolvedUserId);
      if (!response.ok || payload?.status !== "success" || !payload.data) {
        if (!cancelled) setCourseCompleted(false);
        return;
      }

      const isComplete =
        payload.data.modules.length > 0 &&
        payload.data.modules.every((module) => module.lessons_total > 0 && module.lessons_completed === module.lessons_total);

      if (!cancelled) setCourseCompleted(isComplete);
    }

    void loadCourseCompletion();
    return () => {
      cancelled = true;
    };
  }, [courseId, userId]);

  const handleSelectAnswer = useCallback((questionIndex: number, optionIndex: number) => {
    setAnswers((prev) => ({
      ...prev,
      [String(questionIndex)]: optionIndex,
    }));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!assessmentId || !userId || !canSubmit) return;

    setSubmitting(true);
    setSubmitError(null);

    const { response, payload } = await submitAssessment(assessmentId, userId, answers);
    if (!response.ok || payload?.status !== "success" || !payload.data) {
      setSubmitError(payload?.message || `Could not submit quiz (HTTP ${response.status}).`);
      setSubmitting(false);
      return;
    }

    setResults(payload.data.results);
    setScore(payload.data.score);
    setPassed(payload.data.passed);
    setFeedback(payload.data.feedback);
    setNextAction(payload.data.next_action);
    setSubmitting(false);
  }, [answers, assessmentId, canSubmit, userId]);

  if (!userId) {
    return <Navigate to="/log-in" replace />;
  }

  if (!courseId || !lessonId) {
    return <Navigate to="/tutoring" replace />;
  }

  return (
    <PageTransition>
      <div className="home-theme min-h-screen overflow-x-hidden bg-[var(--home-bg)] text-[var(--home-fg)]">
        <div className="mx-auto max-w-4xl px-6 py-10 md:py-16">
          <Button
            type="button"
            variant="ghost"
            className="mb-6 -ml-2 gap-2 text-[var(--home-muted)] hover:text-[var(--home-fg)]"
            onClick={() => navigate(`/tutoring/course/${courseId}/lesson/${lessonId}`)}
          >
            <ArrowLeft className="h-4 w-4" />
            Back to lesson
          </Button>

          <div className="rounded-[28px] border border-[var(--home-chip-border)] bg-[linear-gradient(135deg,rgba(255,248,233,0.95),rgba(255,255,255,0.95))] p-6 shadow-[0_18px_50px_rgba(0,0,0,0.08)] dark:bg-[linear-gradient(135deg,rgba(44,37,24,0.92),rgba(24,24,24,0.92))]">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-100/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                  <Sparkles className="h-3.5 w-3.5" aria-hidden />
                  Lesson quiz
                </p>
                <h1 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl">
                  {lesson?.title || "Practice what you just learned"}
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--home-muted)] md:text-base">
                  {lesson?.course_title
                    ? `${lesson.course_title} · ${lesson.module_title}`
                    : "A quick checkpoint to lock in the tutorial before moving on."}
                </p>
              </div>

              <div className="grid min-w-[220px] gap-3 sm:grid-cols-2 md:grid-cols-1">
                <div className="rounded-2xl border border-[var(--home-chip-border)] bg-white/70 p-4 dark:bg-black/15">
                  <p className="text-xs uppercase tracking-wide text-[var(--home-muted)]">Answered</p>
                  <p className="mt-1 text-2xl font-semibold">
                    {answeredCount}
                    <span className="ml-1 text-sm font-medium text-[var(--home-muted)]">/ {questions.length || "?"}</span>
                  </p>
                </div>
                <div className="rounded-2xl border border-[var(--home-chip-border)] bg-white/70 p-4 dark:bg-black/15">
                  <p className="text-xs uppercase tracking-wide text-[var(--home-muted)]">Score</p>
                  <p className={cn("mt-1 text-2xl font-semibold", scoreTone(score))}>
                    {score === null ? "--" : `${score}%`}
                  </p>
                </div>
              </div>
            </div>

            {lessonError ? <p className="mt-4 text-sm text-amber-700 dark:text-amber-300">{lessonError}</p> : null}

            {!lessonLoading && lesson && !lesson.completed ? (
              <p className="mt-4 text-sm text-amber-700 dark:text-amber-300">
                This quiz works best right after you finish the lesson. You can still try it now, but the normal flow is lesson first, quiz second.
              </p>
            ) : null}
          </div>

          {quizLoading ? (
            <p className="mt-8 text-sm text-[var(--home-muted)]">Generating your lesson quiz…</p>
          ) : quizError ? (
            <div className="mt-8 rounded-2xl border border-red-300 bg-red-50/80 p-5 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
              <p className="text-sm">{quizError}</p>
              <Button type="button" variant="outline" className="mt-4" onClick={() => void loadQuiz()}>
                Try again
              </Button>
            </div>
          ) : (
            <>
              <div className="mt-8 space-y-5">
                {questions.map((question) => {
                  const selectedAnswer = answers[String(question.index)];
                  const questionResult = results?.find((item) => item.index === question.index) ?? null;

                  return (
                    <section
                      key={question.index}
                      className="rounded-3xl border border-[var(--home-chip-border)] bg-[var(--home-chip-bg)] p-5 shadow-[0_10px_24px_rgba(0,0,0,0.05)]"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--home-muted)]">
                            Question {question.index + 1}
                          </p>
                          <h2 className="mt-2 text-lg font-semibold leading-7 text-[var(--home-fg)]">
                            {question.question}
                          </h2>
                        </div>
                        {questionResult ? (
                          questionResult.is_correct ? (
                            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-100/80 px-3 py-1 text-xs font-medium text-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200">
                              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                              Correct
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-100/80 px-3 py-1 text-xs font-medium text-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
                              <Circle className="h-3.5 w-3.5" aria-hidden />
                              Review
                            </span>
                          )
                        ) : null}
                      </div>

                      <div className="mt-4 grid gap-3">
                        {question.options.map((option, optionIndex) => {
                          const isSelected = selectedAnswer === optionIndex;
                          const isCorrect = questionResult?.correct_answer === optionIndex;
                          const isWrongSelection = Boolean(questionResult) && isSelected && !isCorrect;

                          return (
                            <button
                              key={`${question.index}-${optionIndex}`}
                              type="button"
                              disabled={Boolean(results)}
                              onClick={() => handleSelectAnswer(question.index, optionIndex)}
                              className={cn(
                                "flex w-full items-start gap-3 rounded-2xl border px-4 py-3 text-left transition",
                                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--home-bg)]",
                                results
                                  ? "cursor-default"
                                  : "hover:border-amber-500/60 hover:bg-amber-50/60 dark:hover:bg-amber-950/20",
                                isSelected
                                  ? "border-amber-500 bg-amber-50/90 dark:bg-amber-950/25"
                                  : "border-[var(--home-chip-border)] bg-white/70 dark:bg-black/10",
                                isCorrect && results
                                  ? "border-emerald-500 bg-emerald-50/80 dark:bg-emerald-950/25"
                                  : "",
                                isWrongSelection ? "border-rose-500 bg-rose-50/80 dark:bg-rose-950/25" : "",
                              )}
                            >
                              <span
                                className={cn(
                                  "mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                                  isSelected
                                    ? "border-current bg-white/80 text-[var(--home-fg)] dark:bg-black/20"
                                    : "border-[var(--home-chip-border)] text-[var(--home-muted)]",
                                )}
                              >
                                {OPTION_LETTERS[optionIndex] ?? optionIndex + 1}
                              </span>
                              <span className="text-sm leading-6 text-[var(--home-fg)]">{option}</span>
                            </button>
                          );
                        })}
                      </div>

                      {questionResult?.explanation ? (
                        <div className="mt-4 rounded-2xl border border-[var(--home-chip-border)] bg-white/70 p-4 text-sm leading-6 text-[var(--home-muted)] dark:bg-black/10">
                          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--home-muted)]">
                            Explanation
                          </p>
                          <p className="mt-2 whitespace-pre-wrap">{questionResult.explanation}</p>
                        </div>
                      ) : null}
                    </section>
                  );
                })}
              </div>

              {submitError ? (
                <p className="mt-4 text-sm text-red-600" role="alert">
                  {submitError}
                </p>
              ) : null}

              {results ? (
                <section className="mt-8 rounded-3xl border border-[var(--home-chip-border)] bg-[var(--home-chip-bg)] p-6 shadow-[0_10px_24px_rgba(0,0,0,0.05)]">
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--home-muted)]">
                        Quiz results
                      </p>
                      <h2 className={cn("mt-2 text-3xl font-bold tracking-tight", scoreTone(score))}>
                        {score === null ? "--" : `${score}%`}
                      </h2>
                      <p className="mt-2 text-sm text-[var(--home-muted)]">
                        {passed ? "Strong work. You cleared this checkpoint." : "You’re close. A retry after review should feel much easier."}
                      </p>
                    </div>

                    <div className="rounded-2xl border border-[var(--home-chip-border)] bg-white/70 p-4 dark:bg-black/10">
                      <p className="inline-flex items-center gap-2 text-sm font-medium text-[var(--home-fg)]">
                        <Target className="h-4 w-4" aria-hidden />
                        Next action: <span className="capitalize">{nextAction.replaceAll("_", " ")}</span>
                      </p>
                    </div>
                  </div>

                  {feedback ? (
                    <div className="mt-5 rounded-2xl border border-[var(--home-chip-border)] bg-white/70 p-4 text-sm leading-6 text-[var(--home-fg)] dark:bg-black/10">
                      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--home-muted)]">
                        Feedback
                      </p>
                      <p className="mt-2 whitespace-pre-wrap">{feedback}</p>
                    </div>
                  ) : null}

                  <div className="mt-6 flex flex-wrap gap-3">
                    <Button
                      type="button"
                      className="bg-[var(--home-button-bg)] text-[var(--home-button-fg)] hover:bg-[var(--home-fg)]/90"
                      onClick={() => void loadQuiz()}
                    >
                      <RotateCcw className="h-4 w-4" aria-hidden />
                      Retry with a new quiz
                    </Button>
                    {courseCompleted ? (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => navigate(`/tutoring/course/${courseId}/assessment`)}
                      >
                        Take final course assessment
                      </Button>
                    ) : null}
                    <Button type="button" variant="outline" onClick={() => navigate(`/tutoring/course/${courseId}`)}>
                      Back to course
                    </Button>
                  </div>
                </section>
              ) : (
                <div className="mt-8 flex flex-col gap-3 rounded-3xl border border-[var(--home-chip-border)] bg-[var(--home-chip-bg)] p-5 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium text-[var(--home-fg)]">
                      Answer all {questions.length} questions to unlock your score and feedback.
                    </p>
                    <p className="mt-1 text-xs text-[var(--home-muted)]">
                      You’re at {answeredCount}/{questions.length} right now.
                    </p>
                  </div>
                  <Button
                    type="button"
                    disabled={!canSubmit || submitting}
                    className="bg-[var(--home-button-bg)] text-[var(--home-button-fg)] hover:bg-[var(--home-fg)]/90"
                    onClick={() => void handleSubmit()}
                  >
                    {submitting ? "Scoring quiz…" : "Submit quiz"}
                  </Button>
                </div>
              )}
            </>
          )}

          <p className="mt-10 text-center text-xs text-[var(--home-muted)]">
            <Link
              to={`/tutoring/course/${courseId}/lesson/${lessonId}`}
              className="underline underline-offset-2 hover:text-[var(--home-fg)]"
            >
              Return to lesson
            </Link>
          </p>
        </div>
      </div>
    </PageTransition>
  );
}
