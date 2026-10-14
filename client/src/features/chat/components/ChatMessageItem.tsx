import { cn } from "@/lib/utils";
import { FileText } from "lucide-react";
import type { ChatMessage } from "@/features/chat/types";
import TypewriterText from "@/features/chat/components/TypewriterText";
import MessageCopyButton from "@/features/chat/components/MessageCopyButton";

type ChatMessageItemProps = {
  message: ChatMessage;
  isTyping: boolean;
  copied: boolean;
  onTypingComplete: () => void;
  onCopy: () => void;
};

export default function ChatMessageItem({
  message,
  isTyping,
  copied,
  onTypingComplete,
  onCopy,
}: ChatMessageItemProps) {
  return (
    <article className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
      <div className="max-w-2xl">
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm leading-relaxed",
            message.role === "user"
              ? "bg-[#060606] text-white dark:bg-[#1c1c1e] dark:text-white"
              : "border border-slate-200 bg-slate-50 text-slate-900 dark:border-[#3a3a3c] dark:bg-[#2c2c2e] dark:text-slate-100"
          )}
        >
          {message.role === "user" && message.documents && message.documents.length > 0 ? (
            <div className="-mx-1 -my-0.5 flex flex-col gap-3 px-1 py-1">
              <div className="flex flex-col gap-2 rounded-xl bg-white/15 p-3">
                {message.documents.map((doc) => (
                  <div
                    key={doc.document_id || doc.file_name}
                    className="flex items-center gap-3 rounded-lg"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-red-500/90 text-white">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium" title={doc.file_name}>
                        {doc.file_name}
                      </p>
                      <p className="mt-0.5 text-xs opacity-90">PDF</p>
                    </div>
                  </div>
                ))}
              </div>
              <span className="whitespace-pre-wrap">{message.content}</span>
            </div>
          ) : message.role === "llm" ? (
            <TypewriterText text={message.content} shouldAnimate={isTyping} onComplete={onTypingComplete} />
          ) : (
            <span className="whitespace-pre-wrap">{message.content}</span>
          )}
        </div>

        {message.role === "llm" ? (
          <div className="mt-1 flex flex-col gap-1 px-1">
            {message.knowledge_sources && message.knowledge_sources.length > 0 && (
              <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-[#3a3a3c] dark:bg-[#2c2c2e]">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Legal References
                </p>
                <ul className="flex flex-col gap-2">
                  {message.knowledge_sources.map((src, i) => (
                    <li key={i} className="text-[12px] text-slate-700 dark:text-slate-300">
                      <span className="font-medium text-slate-900 dark:text-white">{src.source}</span>
                      <span className="ml-2 rounded bg-slate-200 px-1 py-0.5 text-[10px] dark:bg-[#3a3a3c]">
                        {(src.score * 100).toFixed(0)}% match
                      </span>
                      <p className="mt-0.5 line-clamp-2 text-slate-500 dark:text-slate-400">{src.text}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex items-center justify-between gap-2">
              <p className="text-[11px] text-slate-500 dark:text-white">
                ⓘ METY is not a law firm and does not provide legal advice. For informational purposes only.
              </p>
              <MessageCopyButton copied={copied} onCopy={onCopy} />
            </div>
          </div>
        ) : (
          <div className="mt-1 flex justify-end">
            <MessageCopyButton copied={copied} onCopy={onCopy} />
          </div>
        )}
      </div>
    </article>
  );
}
