import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

type TypewriterTextProps = {
  text: string;
  shouldAnimate: boolean;
  typingSpeed?: number;
  onComplete?: () => void;
};

function stripIncompleteMarkdown(text: string): string {
  let result = text;
  const boldCount = (result.match(/\*\*/g) || []).length;
  if (boldCount % 2 !== 0) {
    result = result.slice(0, result.lastIndexOf("**"));
  }
  const italicCount = (result.match(/(?<!\*)\*(?!\*)/g) || []).length;
  if (italicCount % 2 !== 0) {
    result = result.slice(0, result.lastIndexOf("*"));
  }
  result = result.replace(/#{1,6}\s*$/, "");
  const codeBlockCount = (result.match(/```/g) || []).length;
  if (codeBlockCount % 2 !== 0) {
    result = result.slice(0, result.lastIndexOf("```"));
  }
  const inlineCodeCount = (result.match(/(?<!`)`(?!`)/g) || []).length;
  if (inlineCodeCount % 2 !== 0) {
    result = result.slice(0, result.lastIndexOf("`"));
  }
  return result;
}

export default function TypewriterText({
  text,
  shouldAnimate,
  typingSpeed = 16,
  onComplete,
}: TypewriterTextProps) {
  const [displayedText, setDisplayedText] = useState(shouldAnimate ? "" : text);

  useEffect(() => {
    if (!shouldAnimate) {
      setDisplayedText(text);
      return;
    }

    setDisplayedText("");
    let currentIndex = 0;
    const intervalId = window.setInterval(() => {
      currentIndex += 1;
      setDisplayedText(text.slice(0, currentIndex));

      if (currentIndex >= text.length) {
        window.clearInterval(intervalId);
        onComplete?.();
      }
    }, typingSpeed);

    return () => window.clearInterval(intervalId);
  }, [onComplete, shouldAnimate, text, typingSpeed]);

  const isTyping = shouldAnimate && displayedText.length < text.length;
  const safeText = isTyping ? stripIncompleteMarkdown(displayedText) : displayedText;

  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="mb-2 ml-4 list-disc">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal">{children}</ol>,
          li: ({ children }) => <li className="mb-1">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          h1: ({ children }) => <h1 className="mb-2 text-base font-bold">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 text-sm font-bold">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 text-sm font-semibold">{children}</h3>,
          code: ({ children }) => <code className="rounded bg-slate-200 px-1 py-0.5 text-xs dark:bg-slate-700">{children}</code>,
        }}
      >
        {safeText}
      </ReactMarkdown>
    </div>
  );
}