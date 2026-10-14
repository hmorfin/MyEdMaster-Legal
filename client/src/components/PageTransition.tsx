import type { ReactNode } from "react";

type PageTransitionProps = {
  children: ReactNode;
};

export default function PageTransition({ children }: PageTransitionProps) {
  return <div className="animate-in fade-in duration-300">{children}</div>;
}

