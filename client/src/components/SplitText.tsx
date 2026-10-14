import { useEffect } from "react";

type SplitTextProps = {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
  onLetterAnimationComplete?: () => void;
};

export default function SplitText({
  text,
  className,
  delay = 0,
  duration = 0.3,
  onLetterAnimationComplete,
}: SplitTextProps) {
  useEffect(() => {
    if (!onLetterAnimationComplete) return;
    const timeout = window.setTimeout(
      onLetterAnimationComplete,
      Math.max(0, text.length * delay + duration * 1000),
    );
    return () => window.clearTimeout(timeout);
  }, [delay, duration, onLetterAnimationComplete, text.length]);

  return (
    <span className={className} style={{ animationDuration: `${duration}s` }}>
      {text}
    </span>
  );
}

