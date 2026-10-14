export type CourseLevel = "beginner" | "intermediate" | "advanced";

export type CourseSummary = {
  course_id: string;
  legal_topic: string;
  level: string;
  title: string;
  description: string;
  module_count: number;
  pass_threshold: number;
};

export type ListCoursesResponse = {
  status: "success" | "error";
  count?: number;
  data?: CourseSummary[];
  message?: string;
};

export type EnrolledCourseItem = {
  enrollment_id: string;
  course_id: string;
  legal_topic: string;
  level: string;
  title: string;
  status: string;
  progress_percent: number;
  lessons_completed: number;
  lessons_total: number;
  enrolled_at: string;
};

export type EnrolledCoursesResponse = {
  status: "success" | "error";
  count?: number;
  data?: EnrolledCourseItem[];
  message?: string;
};

export type EnrollResponse = {
  status: "success" | "error";
  data?: {
    enrollment_id: string;
    course_id: string;
    course_title: string;
    already_enrolled: boolean;
    enrolled_at: string;
  };
  message?: string;
};

export type LessonSummary = {
  lesson_id: string;
  title: string;
  order: number;
  learning_objectives: string[];
  content_available: boolean;
};

export type ModuleSummary = {
  module_id: string;
  title: string;
  order: number;
  lessons: LessonSummary[];
};

export type CourseDetail = {
  course_id: string;
  legal_topic: string;
  level: string;
  title: string;
  description: string;
  pass_threshold: number;
  modules: ModuleSummary[];
};

export type CourseDetailResponse = {
  status: "success" | "error";
  data?: CourseDetail;
  message?: string;
};

export type LessonContent = {
  lesson_id: string;
  title: string;
  module_title: string;
  course_title: string;
  legal_topic: string;
  level: string;
  learning_objectives: string[];
  content: string;
  completed: boolean;
};

export type LessonContentResponse = {
  status: "success" | "error";
  data?: LessonContent;
  message?: string;
};

export type LessonCompleteResponse = {
  status: "success" | "error";
  data?: {
    lesson_id: string;
    completed: boolean;
    course_progress: number;
  };
  message?: string;
};

export type CourseProgressItem = {
  course_id: string;
  level: string;
  title: string;
  status: string;
  progress_percent: number;
  lessons_completed: number;
  lessons_total: number;
};

export type TopicProgress = {
  legal_topic: string;
  mastery_score: number;
  courses: CourseProgressItem[];
};

export type LearningProgressResponse = {
  status: "success" | "error";
  data?: {
    user_id: string;
    topics: TopicProgress[];
  };
  message?: string;
};

export type AssessmentScope = "lesson" | "module" | "course";

export type AssessmentQuestion = {
  index: number;
  question: string;
  options: string[];
};

export type GenerateAssessmentResponse = {
  status: "success" | "error";
  data?: {
    assessment_id: string;
    scope: AssessmentScope;
    title: string;
    questions: AssessmentQuestion[];
  };
  message?: string;
};

export type AssessmentResult = {
  index: number;
  question: string;
  options: string[];
  user_answer: number | null;
  correct_answer: number;
  is_correct: boolean;
  explanation: string;
};

export type SubmitAssessmentResponse = {
  status: "success" | "error";
  data?: {
    assessment_id: string;
    score: number;
    passed: boolean;
    correct: number;
    total: number;
    next_action: "retry" | "next_lesson" | "next_module" | "unlock_next_level";
    feedback: string;
    results: AssessmentResult[];
  };
  message?: string;
};

export type ModuleProgressItem = {
  module_id: string;
  title: string;
  order: number;
  lessons_total: number;
  lessons_completed: number;
  progress_percent: number;
  assessment_passed: boolean;
};

export type ModuleProgressResponse = {
  status: "success" | "error";
  data?: {
    course_id: string;
    course_title: string;
    user_id: string;
    modules: ModuleProgressItem[];
  };
  message?: string;
};
