import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { usePageTitleContext } from "@/components/PageTitleProvider";

const APP_NAME = "Broque";

function getTitle(pathname: string): string {
  if (pathname === "/" || pathname === "/home") return `${APP_NAME} | Home`;
  if (pathname === "/log-in") return `${APP_NAME} | Log In`;
  if (pathname === "/register") return `${APP_NAME} | Register`;
  if (pathname === "/onboarding") return `${APP_NAME} | Onboarding`;
  if (pathname === "/success") return `${APP_NAME} | Success`;
  if (pathname === "/tutoring") return `${APP_NAME} | Tutoring`;
  if (pathname.includes("/quiz")) return `${APP_NAME} | Quiz`;
  if (pathname.startsWith("/tutoring/course/")) return `${APP_NAME} | Course`;
  if (pathname.includes("/lesson/")) return `${APP_NAME} | Lesson`;
  if (pathname === "/chat" || pathname.startsWith("/chat/")) return `${APP_NAME} | Chat`;
  if (pathname === "/me") return `${APP_NAME} | Profile`;
  if (pathname === "/settings") return `${APP_NAME} | Settings`;
  return APP_NAME;
}

export default function RouteTitleManager() {
  const { pathname } = useLocation();
  const pageTitleContext = usePageTitleContext();

  useEffect(() => {
    if (pageTitleContext?.overrideTitle) {
      document.title = `${APP_NAME} | ${pageTitleContext.overrideTitle}`;
      return;
    }
    document.title = getTitle(pathname);
  }, [pageTitleContext?.overrideTitle, pathname]);

  return null;
}
