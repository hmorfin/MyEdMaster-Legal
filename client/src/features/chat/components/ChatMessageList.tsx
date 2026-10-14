import { useRef, useEffect, useState, useCallback } from "react";
import { ChevronDown } from "lucide-react";
import type { ChatMessage } from "@/features/chat/types";
import ChatMessageItem from "@/features/chat/components/ChatMessageItem";

type ChatMessageListProps = {
  messages: ChatMessage[];
  chatId?: string;
  isLoading: boolean;
  error: string | null;
  sending: boolean;
  typingMessageId: string | null;
  copiedMessageId: string | null;
  onTypingComplete: (id: string) => void;
  onCopyMessage: (message: ChatMessage) => void;
};

export default function ChatMessageList({
  messages,
  chatId,
  isLoading,
  error,
  sending,
  typingMessageId,
  copiedMessageId,
  onTypingComplete,
  onCopyMessage,
}: ChatMessageListProps) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const userScrolledUp = useRef(false);
  const animFrameRef = useRef<number | null>(null);

  const SCROLL_THRESHOLD = 80;

  function isNearBottom() {
    const el = scrollerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < SCROLL_THRESHOLD;
  }

  function scrollToBottom() {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth",
    });
    setShowScrollToBottom(false);
    userScrolledUp.current = false;
  }

  function handleScroll() {
    if (!scrollerRef.current) return;
    const near = isNearBottom();
    setShowScrollToBottom(!near);
    if (!near && typingMessageId) {
      userScrolledUp.current = true;
    }
    if (near) {
      userScrolledUp.current = false;
    }
  }

  useEffect(() => {
    userScrolledUp.current = false;
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth",
    });
    setShowScrollToBottom(false);
  }, [messages, sending]);

  const scheduleScroll = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    animFrameRef.current = requestAnimationFrame(() => {
      if (!userScrolledUp.current && scrollerRef.current) {
        scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
      }
    });
  }, []);

  useEffect(() => {
    if (!typingMessageId) return;
    const el = scrollerRef.current;
    if (!el) return;

    const observer = new MutationObserver(() => {
      scheduleScroll();
    });
    observer.observe(el, { childList: true, subtree: true, characterData: true });

    return () => {
      observer.disconnect();
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [typingMessageId, scheduleScroll]);

  return (
    <div className="relative min-h-0 flex-1">
      <section
        ref={scrollerRef}
        className="min-h-0 h-full space-y-4 overflow-y-auto bg-background px-4 py-5 md:px-6"
        onScroll={handleScroll}
      >
        {isLoading ? <p className="text-sm text-slate-500 dark:text-white">Loading chat messages...</p> : null}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        {!isLoading && !error && chatId && messages.length === 0 ? (
          <div className="flex min-h-[42vh] items-center justify-center">
            <p className="text-center text-lg font-medium text-slate-500 dark:text-white">
              No messages yet. Ask your first question below.
            </p>
          </div>
        ) : null}

        {messages.map((message) => (
          <ChatMessageItem
            key={message.id}
            message={message}
            isTyping={typingMessageId === message.id}
            copied={copiedMessageId === message.id}
            onTypingComplete={() => onTypingComplete(message.id)}
            onCopy={() => onCopyMessage(message)}
          />
        ))}

      {sending ? (
        <article className="flex justify-start" aria-live="polite" aria-busy="true">
          <div className="flex items-center gap-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 dark:border-[#3a3a3c] dark:bg-[#2c2c2e] dark:text-slate-200">
            <span className="sr-only">Assistant is responding</span>
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#060606] dark:bg-white [animation-delay:0ms]" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#060606] dark:bg-white [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#060606] dark:bg-white [animation-delay:300ms]" />
          </div>
        </article>
      ) : null}

      </section>

      {showScrollToBottom ? (
        <button
          type="button"
          onClick={scrollToBottom}
          className="absolute bottom-5 left-1/2 z-10 flex h-10 w-10 -translate-x-1/2 items-center justify-center rounded-full border border-slate-200 bg-white shadow-md transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 dark:border-[#1c1c1e] dark:bg-[#060606] dark:hover:bg-[#111111]"
          aria-label="Scroll to bottom"
        >
          <ChevronDown className="h-5 w-5 text-slate-700 dark:text-white" />
        </button>
      ) : null}
    </div>
  );
}