import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { ArrowRight, LogOut, Moon, Sun } from "lucide-react";
import { applyTheme, isDarkModeEnabled } from "@/lib/theme";
import metyMainLogo from "@/assets/images/Mety Main Logo.png";
import metyMainWhiteLogo from "@/assets/images/Mety Main Logo White.png";

type HomeNavProps = {
  hasUser: boolean;
  onLogout: () => void;
};

export default function HomeNav({ hasUser, onLogout }: HomeNavProps) {
  const navigate = useNavigate();
  const [darkMode, setDarkMode] = useState(isDarkModeEnabled());
  const logoSrc = darkMode ? metyMainWhiteLogo : metyMainLogo;
  const navItems = [
    { label: "About", href: "#about" },
    { label: "Tutorial", href: "#tutorial" },
    { label: "Tech", href: "#tech" },
    { label: "Contact", href: "#contact" },
  ];

  return (
    <header className="px-4 pt-8 md:px-8 md:pt-10">
      <nav
        className="mx-auto flex max-w-[820px] items-center justify-between rounded-[30px] border px-5 py-3 shadow-[0_8px_30px_rgba(0,0,0,0.04)] backdrop-blur-sm md:px-8"
        style={{
          backgroundColor: "var(--home-nav-bg)",
          borderColor: "var(--home-nav-border)",
        }}
      >
        <button
          onClick={() => navigate("/")}
          className="inline-flex items-center text-[var(--home-fg)]"
          aria-label="METY home"
        >
          <img src={logoSrc} alt="" className="h-5 w-auto object-contain md:h-5" aria-hidden="true" />
        </button>
        <div className="hidden items-center gap-10 text-[15px] text-[var(--home-muted)] md:flex">
          {navItems.map((item) => (
            <a key={item.label} href={item.href} className="transition-colors hover:text-[var(--home-fg)]">
              {item.label}
            </a>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const nextTheme = darkMode ? "light" : "dark";
              applyTheme(nextTheme);
              setDarkMode(nextTheme === "dark");
            }}
            className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border transition-colors hover:text-[var(--home-fg)]"
            style={{ borderColor: "var(--home-nav-border)" }}
            aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
          {hasUser ? (
            <>
            <button
              onClick={onLogout}
              className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border text-[var(--home-muted)] transition-colors hover:text-[var(--home-fg)]"
              style={{ borderColor: "var(--home-nav-border)" }}
              aria-label="Log out"
            >
              <LogOut className="h-4 w-4" />
            </button>
            <button
              onClick={() => navigate("/chat")}
              className="inline-flex h-12 w-12 items-center justify-center rounded-2xl text-sm font-semibold transition-transform hover:translate-y-[-1px] md:h-auto md:w-auto md:gap-2 md:px-5 md:py-3"
              style={{ backgroundColor: "var(--home-button-bg)", color: "var(--home-button-fg)" }}
              aria-label="Open App"
            >
              <span className="hidden md:inline">Open App</span>
              <ArrowRight className="h-4 w-4" />
            </button>
            </>
          ) : (
            <>
              <button
                onClick={() => navigate("/register")}
                className="hidden items-center rounded-2xl border px-5 py-3 text-sm font-semibold text-[var(--home-fg)] transition-colors hover:bg-black/5 dark:hover:bg-white/10 md:inline-flex"
                style={{ borderColor: "var(--home-nav-border)" }}
              >
                Register
              </button>
              <button
                onClick={() => navigate("/log-in")}
                className="inline-flex items-center gap-2 rounded-2xl px-5 py-3 text-sm font-semibold transition-transform hover:translate-y-[-1px]"
                style={{ backgroundColor: "var(--home-button-bg)", color: "var(--home-button-fg)" }}
              >
                Login
                <ArrowRight className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
