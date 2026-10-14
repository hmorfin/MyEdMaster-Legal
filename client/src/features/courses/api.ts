import { API_BASE_URL } from "@/lib/api";
import type {
  AssessmentScope,
  CourseDetailResponse,
  CourseLevel,
  GenerateAssessmentResponse,
  LearningProgressResponse,
  EnrolledCoursesResponse,
  EnrollResponse,
  LessonContentResponse,
  LessonCompleteResponse,
  ListCoursesResponse,
  SubmitAssessmentResponse,
  ModuleProgressResponse,
} from "@/features/courses/types";

function coursesUrl(params: { level?: CourseLevel; topic?: string }): string {
  const base = `${API_BASE_URL.replace(/\/+$/, "")}/courses/`;
  const search = new URLSearchParams();
  if (params.level) search.set("level", params.level);
  if (params.topic?.trim()) search.set("topic", params.topic.trim());
  const q = search.toString();
  return q ? `${base}?${q}` : base;
}

export async function fetchCourses(options: {
  level?: CourseLevel;
  topic?: string;
}): Promise<{ response: Response; payload: ListCoursesResponse | null }> {
  const response = await fetch(coursesUrl({ level: options.level, topic: options.topic }), {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const payload = (await response.json().catch(() => null)) as ListCoursesResponse | null;
  return { response, payload };
}

function coursesBase(): string {
  return `${API_BASE_URL.replace(/\/+$/, "")}/courses`;
}

export async function fetchEnrolledCourses(
  userId: string,
): Promise<{ response: Response; payload: EnrolledCoursesResponse | null }> {
  const response = await fetch(`${coursesBase()}/enrolled/${encodeURIComponent(userId)}/`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const payload = (await response.json().catch(() => null)) as EnrolledCoursesResponse | null;
  return { response, payload };
}

export async function enrollInCourse(
  courseId: string,
  userId: string,
): Promise<{ response: Response; payload: EnrollResponse | null }> {
  const response = await fetch(
    `${coursesBase()}/${encodeURIComponent(courseId)}/enroll/${encodeURIComponent(userId)}/`,
    {
      method: "POST",
      headers: { Accept: "application/json" },
    },
  );
  const payload = (await response.json().catch(() => null)) as EnrollResponse | null;
  return { response, payload };
}

export async function fetchCourseDetail(
  courseId: string,
): Promise<{ response: Response; payload: CourseDetailResponse | null }> {
  const response = await fetch(`${coursesBase()}/${encodeURIComponent(courseId)}/`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  const payload = (await response.json().catch(() => null)) as CourseDetailResponse | null;
  return { response, payload };
}

export async function fetchLessonContent(
  lessonId: string,
  userId: string,
): Promise<{ response: Response; payload: LessonContentResponse | null }> {
  const response = await fetch(
    `${coursesBase()}/lessons/${encodeURIComponent(lessonId)}/${encodeURIComponent(userId)}/`,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    },
  );
  const payload = (await response.json().catch(() => null)) as LessonContentResponse | null;
  return { response, payload };
}

export async function completeLesson(
  lessonId: string,
  userId: string,
): Promise<{ response: Response; payload: LessonCompleteResponse | null }> {
  const response = await fetch(
    `${coursesBase()}/lessons/${encodeURIComponent(lessonId)}/complete/${encodeURIComponent(userId)}/`,
    {
      method: "POST",
      headers: { Accept: "application/json" },
    },
  );

  const payload = (await response.json().catch(() => null)) as LessonCompleteResponse | null;
  return { response, payload };
}

export async function fetchCourseProgress(
  userId: string,
): Promise<{ response: Response; payload: LearningProgressResponse | null }> {
  const response = await fetch(`${coursesBase()}/progress/${encodeURIComponent(userId)}/`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  const payload = (await response.json().catch(() => null)) as LearningProgressResponse | null;
  return { response, payload };
}

export async function generateAssessment(
  userId: string,
  scope: AssessmentScope,
  targetId: string,
): Promise<{ response: Response; payload: GenerateAssessmentResponse | null }> {
  const response = await fetch(`${coursesBase()}/assessments/generate/${encodeURIComponent(userId)}/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      scope,
      target_id: targetId,
    }),
  });

  const payload = (await response.json().catch(() => null)) as GenerateAssessmentResponse | null;
  return { response, payload };
}

export async function submitAssessment(
  assessmentId: string,
  userId: string,
  answers: Record<string, number>,
): Promise<{ response: Response; payload: SubmitAssessmentResponse | null }> {
  const response = await fetch(
    `${coursesBase()}/assessments/${encodeURIComponent(assessmentId)}/submit/${encodeURIComponent(userId)}/`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ answers }),
    },
  );

  const payload = (await response.json().catch(() => null)) as SubmitAssessmentResponse | null;
  return { response, payload };
}

export async function fetchModuleProgress(
  courseId: string,
  userId: string,
): Promise<{ response: Response; payload: ModuleProgressResponse | null }> {
  const response = await fetch(
    `${coursesBase()}/${encodeURIComponent(courseId)}/progress/${encodeURIComponent(userId)}/modules/`,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    },
  );
  const payload = (await response.json().catch(() => null)) as ModuleProgressResponse | null;
  return { response, payload };
}
