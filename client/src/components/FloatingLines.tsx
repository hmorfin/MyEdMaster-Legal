import type { CSSProperties } from "react";

type FloatingLinesProps = {
  linesGradient?: [string, string];
  animationSpeed?: number;
  mixBlendMode?: CSSProperties["mixBlendMode"];
};

export default function FloatingLines({
  linesGradient = ["#d4b25a", "#8b6a1f"],
  animationSpeed = 1,
  mixBlendMode = "normal",
}: FloatingLinesProps) {
  const duration = `${Math.max(6, 16 / Math.max(animationSpeed, 0.2))}s`;

  return (
    <div
      className="floating-lines-container h-full w-full"
      style={{
        mixBlendMode,
        backgroundImage: `repeating-linear-gradient(
          180deg,
          ${linesGradient[0]}22 0px,
          ${linesGradient[1]}22 1px,
          transparent 1px,
          transparent 22px
        )`,
        backgroundSize: "100% 140%",
        animation: `floating-lines ${duration} linear infinite`,
      }}
    />
  );
}
