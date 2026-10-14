import type { CourseSummary } from "@/features/courses/types";

export const COURSE_LEVELS = ["beginner", "intermediate", "advanced"] as const;

type StoredCourseAssessment = {
  score: number;
  passed: boolean;
  saved_at: string;
};

export function getCourseAssessmentStorageKey(userId: string, courseId: string): string {
  return `legal_chatbot_course_assessment_${userId}_${courseId}`;
}

export function readStoredCourseAssessment(
  userId: string,
  courseId: string,
): StoredCourseAssessment | null {
  try {
    const raw = localStorage.getItem(getCourseAssessmentStorageKey(userId, courseId));
    if (!raw) return null;
    return JSON.parse(raw) as StoredCourseAssessment;
  } catch {
    return null;
  }
}

export function writeStoredCourseAssessment(
  userId: string,
  courseId: string,
  assessment: { score: number; passed: boolean },
): void {
  try {
    localStorage.setItem(
      getCourseAssessmentStorageKey(userId, courseId),
      JSON.stringify({
        score: assessment.score,
        passed: assessment.passed,
        saved_at: new Date().toISOString(),
      } satisfies StoredCourseAssessment),
    );
  } catch {
    // Ignore localStorage failures and keep the in-memory UI flow working.
  }
}

export function compareCourses(a: CourseSummary, b: CourseSummary): number {
  const topicCompare = a.legal_topic.localeCompare(b.legal_topic);
  if (topicCompare !== 0) return topicCompare;

  return COURSE_LEVELS.indexOf(a.level as (typeof COURSE_LEVELS)[number]) -
    COURSE_LEVELS.indexOf(b.level as (typeof COURSE_LEVELS)[number]);
}

export function isCourseUnlocked(
  course: CourseSummary,
  allCourses: CourseSummary[],
  userId: string,
): boolean {
  if (course.level === "beginner") return true;

  const currentLevelIndex = COURSE_LEVELS.indexOf(course.level as (typeof COURSE_LEVELS)[number]);
  if (currentLevelIndex <= 0) return true;

  const previousLevel = COURSE_LEVELS[currentLevelIndex - 1];
  const previousCourse = allCourses.find(
    (candidate) =>
      candidate.legal_topic === course.legal_topic && candidate.level === previousLevel,
  );

  if (!previousCourse) return true;

  return readStoredCourseAssessment(userId, previousCourse.course_id) !== null;
}

export function getNextLevelCourse(
  course: CourseSummary,
  allCourses: CourseSummary[],
): CourseSummary | null {
  const currentLevelIndex = COURSE_LEVELS.indexOf(course.level as (typeof COURSE_LEVELS)[number]);
  if (currentLevelIndex < 0 || currentLevelIndex >= COURSE_LEVELS.length - 1) {
    return null;
  }

  const nextLevel = COURSE_LEVELS[currentLevelIndex + 1];
  return (
    allCourses.find(
      (candidate) =>
        candidate.legal_topic === course.legal_topic && candidate.level === nextLevel,
    ) ?? null
  );
}
