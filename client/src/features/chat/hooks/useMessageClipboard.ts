import { useEffect, useRef, useState } from "react";
import removeMd from "remove-markdown";

export function useMessageClipboard() {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const copyResetTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (copyResetTimerRef.current) {
        window.clearTimeout(copyResetTimerRef.current);
      }
    };
  }, []);

  async function copyMessageText(messageId: string, content: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(removeMd(content));
      setCopiedMessageId(messageId);

      if (copyResetTimerRef.current) {
        window.clearTimeout(copyResetTimerRef.current);
      }

      copyResetTimerRef.current = window.setTimeout(() => {
        setCopiedMessageId((current) => (current === messageId ? null : current));
      }, 1400);

      return true;
    } catch {
      return false;
    }
  }

  return { copiedMessageId, copyMessageText };
}