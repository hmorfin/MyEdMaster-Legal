type AudienceItem = {
  iconSrc: string;
  title: string;
  description: string;
};

export default function WhoItsForSection({ items }: { items: AudienceItem[] }) {
  return (
    <section id="tech" className="mx-auto max-w-6xl px-6 pb-8 pt-8 md:px-8 md:pt-12">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {items.map(({ iconSrc, title, description }) => (
          <div
            key={title}
            className="rounded-[28px] border bg-[var(--home-card)] p-8 shadow-[0_8px_24px_rgba(0,0,0,0.03)]"
            style={{ borderColor: "var(--home-nav-border)" }}
          >
            <div className="mb-8 inline-flex items-center gap-3 rounded-full border border-[var(--home-pill-border)] bg-[var(--home-pill-bg)] px-6 py-4 text-[15px] font-medium text-[var(--home-muted)]">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[var(--home-pill-icon-bg)] text-[var(--home-fg)]">
                <img src={iconSrc} alt="" className="h-5 w-5 object-contain" aria-hidden="true" />
              </span>
              {title}
            </div>
            <p className="text-2xl font-medium tracking-[-0.04em] text-[var(--home-fg)]">{description}</p>
          </div>
        ))}
      </div>
      <div id="contact" className="h-12" />
    </section>
  );
}
