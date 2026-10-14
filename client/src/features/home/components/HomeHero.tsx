import { useNavigate } from "react-router-dom";
import metyLogo from "@/assets/images/mety-logo.png";

type HomeHeroProps = {
  authPrimaryPath: string;
  exampleQuestions: string[];
};

export default function HomeHero({ authPrimaryPath, exampleQuestions }: HomeHeroProps) {
  const navigate = useNavigate();

  return (
    <section id="about" className="px-6 pb-10 pt-16 text-center md:px-8 md:pt-24">
      <div className="mx-auto max-w-6xl">
        <div className="mety-orbit mx-auto">
          <img src={metyLogo} alt="METY Legal logo" className="mety-orbit__image" />
        </div>

        <h1 className="mx-auto mt-8 max-w-5xl text-4xl font-black tracking-[-0.06em] text-[var(--home-fg)] md:text-7xl">
          Hey there! I am METY<sup className="align-super text-[0.45em]">®</sup> Legal
        </h1>

        <p className="mx-auto mt-6 max-w-4xl text-lg font-medium tracking-[-0.03em] text-[var(--home-fg)] md:text-3xl">
          Legal Guidance for those who can&apos;t afford a lawyer, but still deserve one.
        </p>

        <div
          id="tutorial"
          className="mx-auto mt-10 flex max-w-[1720px] flex-col items-center gap-3 md:flex-row md:flex-nowrap md:justify-center"
        >
          {exampleQuestions.map((question) => (
            <button
              key={question}
              onClick={() => navigate(authPrimaryPath)}
              className="w-full rounded-xl border border-[var(--home-chip-border)] bg-[var(--home-chip-bg)] px-5 py-3 text-left text-sm font-medium whitespace-nowrap text-[var(--home-chip-fg)] shadow-[0_2px_8px_rgba(0,0,0,0.03)] transition-transform hover:translate-y-[-1px] md:w-auto md:flex-1 md:text-base"
            >
              <span className="mr-3 text-[var(--home-chip-fg)]/80">&bull;</span>
              {question}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
