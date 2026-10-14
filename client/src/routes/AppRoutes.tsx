import { Route, Routes } from "react-router-dom";
import ChatLayout from "@/components/ChatLayout";
import ChatPage from "@/pages/ChatPage";
import HomePage from "@/pages/HomePage";
import OnboardingPage from "@/pages/OnboardingPage";
import SuccessPage from "@/pages/SuccessPage";
import LoginPage from "@/pages/LogInPage";
import RegisterPage from "@/pages/RegisterPage";
import RouteTitleManager from "@/components/RouteTitleManager";
import UserProfilePage from "@/pages/UserProfilePage";
import SettingsPage from "@/pages/SettingsPage";
import { PageTitleProvider } from "@/components/PageTitleProvider";
import SelfAssessmentPage from "@/pages/SelfAssessmentPage";
import TutoringPage from "@/pages/TutoringPage";
import TutoringCoursePage from "@/pages/TutoringCoursePage";
import TutoringCourseAssessmentPage from "@/pages/TutoringCourseAssessmentPage";
import TutoringLessonPage from "@/pages/TutoringLessonPage";
import TutoringLessonQuizPage from "@/pages/TutoringLessonQuizPage";
import ChatEntryPage from "@/pages/ChatEntryPage";
import StatisticsPage from "@/pages/StatisticsPage";
import DocumentChatEntryPage from "@/pages/DocumentChatEntryPage";

export default function AppRoutes() {
  return (
    <PageTitleProvider>
      <RouteTitleManager />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/tutoring/course/:courseId" element={<TutoringCoursePage />} />
        <Route path="/tutoring/course/:courseId/assessment" element={<TutoringCourseAssessmentPage />} />
        <Route path="/tutoring/course/:courseId/lesson/:lessonId" element={<TutoringLessonPage />} />
        <Route path="/tutoring/course/:courseId/lesson/:lessonId/quiz" element={<TutoringLessonQuizPage />} />
        <Route path="/tutoring" element={<TutoringPage />} />
        <Route path="/log-in" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/success" element={<SuccessPage />} />
        <Route path="/chat" element={<ChatLayout />}>
          <Route index element={<ChatEntryPage />} />
          <Route path="session" element={<ChatPage />} />
          <Route path=":chatId" element={<ChatPage />} />
          <Route path="document" element={<DocumentChatEntryPage />} />
        </Route>
        <Route path="/me" element={<UserProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/chat/:chatId/self-assessment" element={<SelfAssessmentPage />} />
        <Route path="/statistics" element={<StatisticsPage />} />
      </Routes>
    </PageTitleProvider>
  );
}
