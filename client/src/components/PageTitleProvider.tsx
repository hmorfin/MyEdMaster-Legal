import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type PageTitleContextValue = {
  overrideTitle: string | null;
  setOverrideTitle: (title: string | null) => void;
};

const PageTitleContext = createContext<PageTitleContextValue | null>(null);

export function PageTitleProvider({ children }: { children: ReactNode }) {
  const [overrideTitle, setOverrideTitle] = useState<string | null>(null);
  const value = useMemo(() => ({ overrideTitle, setOverrideTitle }), [overrideTitle]);
  return <PageTitleContext.Provider value={value}>{children}</PageTitleContext.Provider>;
}

export function usePageTitleOverride(title: string | null) {
  const context = useContext(PageTitleContext);
  useEffect(() => {
    if (!context) return;
    context.setOverrideTitle(title);
    return () => context.setOverrideTitle(null);
  }, [context, title]);
}

export function usePageTitleContext() {
  return useContext(PageTitleContext);
}
