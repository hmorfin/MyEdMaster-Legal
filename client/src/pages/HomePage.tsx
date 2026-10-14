import { useMemo } from "react";
import PageTransition from "@/components/PageTransition";
import HomeNav from "@/features/home/components/HomeNav";
import HomeHero from "@/features/home/components/HomeHero";
import WhoItsForSection from "@/features/home/components/WhoItsForSection";
import { clearStoredUser, getStoredUserId } from "@/lib/auth";
import houseIcon from "@/assets/images/house-icon.png";
import workerIcon from "@/assets/images/worker-icon.png";
import everydayPersonIcon from "@/assets/images/everday-person-icon.png";
import "@/features/home/styles/home.css";

const WHO_ITS_FOR = [
  {
    iconSrc: houseIcon,
    title: "Tenants & Renters",
    description:
      "Illegal evictions, rent hikes, uninhabitable conditions. Know your rights before signing or fighting back.",
  },
  {
    iconSrc: workerIcon,
    title: "Workers",
    description:
      "Wrongful termination, unpaid wages, hostile workplaces. Get clarity without a high hourly consultation.",
  },
  {
    iconSrc: everydayPersonIcon,
    title: "Everyday People",
    description:
      "Small claims, contracts, traffic disputes. Legal language should not be a barrier to justice.",
  },
];

const EXAMPLE_QUESTIONS = [
  "Can my landlord enter without notice?",
  "Is my non-compete enforceable?",
  "What are my rights if I'm fired?",
  "How do I respond to a debt collector?",
];

export default function HomePage() {
  const hasUser = useMemo(() => Boolean(getStoredUserId()), []);

  const handleLogout = () => {
    clearStoredUser();
    window.location.reload();
  };

  const authPrimaryPath = hasUser ? "/chat" : "/log-in";

  return (
    <PageTransition>
      <div className="home-theme min-h-screen overflow-x-hidden bg-[var(--home-bg)] text-[var(--home-fg)]">
        <div className="relative">
          <HomeNav hasUser={hasUser} onLogout={handleLogout} />
          <HomeHero 
             authPrimaryPath={authPrimaryPath} 
             exampleQuestions={EXAMPLE_QUESTIONS} 
             />
          <WhoItsForSection items={WHO_ITS_FOR} />

          <footer className="px-6 py-10 text-center text-xs text-[var(--home-muted)]">
            METY Legal is not a law firm and does not provide legal advice. For informational purposes only.
          </footer>
        </div>
      </div>
    </PageTransition>
  );
}
