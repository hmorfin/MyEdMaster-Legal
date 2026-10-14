import { PlusIcon, SendIcon, X } from "lucide-react";
import { Button } from "@/components/ui/button";

type ChatComposerProps = {
  input: string;
  attachedFiles: File[];
  fileError: string | null;
  sendError: string | null;
  sending: boolean;
  onInputChange: (value: string) => void;
  onSubmitPrompt: () => void;
  onAttachFiles: (files: FileList | null) => void;
  onRemoveAttachedFile: (index: number) => void;
  onOpenFilePicker: () => void;
};

export default function ChatComposer({
  input,
  attachedFiles,
  fileError,
  sendError,
  sending,
  onInputChange,
  onSubmitPrompt,
  onAttachFiles,
  onRemoveAttachedFile,
  onOpenFilePicker,
}: ChatComposerProps) {
  const hasAttachments = attachedFiles.length > 0;
  const disabled = sending;

  return (
    <section className="shrink-0 space-y-3 bg-background px-4 py-4 md:px-6">
      <form
        className="space-y-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-[#3a3a3c] dark:bg-[#1c1c1e]"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmitPrompt();
        }}
      >
        <input
          type="file"
          multiple
          accept=".pdf,application/pdf"
          className="hidden"
          id="chat-file-input"
          disabled={disabled}
          onChange={(event) => {
            onAttachFiles(event.target.files);
            event.target.value = "";
          }}
        />

        {hasAttachments ? (
          <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-[#3a3a3c] dark:bg-[#111113]">
            {attachedFiles.map((file, index) => (
              <span
                key={`${file.name}-${file.size}-${index}`}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-700 dark:border-[#3a3a3c] dark:bg-[#2c2c2e] dark:text-slate-200"
              >
                <span className="max-w-[120px] truncate" title={file.name}>
                  {file.name}
                </span>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onRemoveAttachedFile(index)}
                  className="shrink-0 rounded p-0.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-300 dark:text-slate-500 dark:hover:bg-slate-700 dark:hover:text-slate-100 dark:focus:ring-slate-600"
                  aria-label={`Remove ${file.name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            ))}
          </div>
        ) : null}

        <textarea
          value={input}
          disabled={disabled}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (disabled) return;
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSubmitPrompt();
            }
          }}
          placeholder={disabled ? "Wait for the current response to finish..." : "Ask your legal question..."}
          className="min-h-24 w-full resize-none rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-[#3a3a3c] dark:bg-[#111113] dark:text-slate-100 dark:placeholder:text-white dark:focus:border-[#5a5a5e]"
        />

        {fileError ? (
          <p className="text-xs text-red-600" role="alert">
            {fileError}
          </p>
        ) : null}
        {sendError ? (
          <p className="text-xs text-red-600" role="alert">
            {sendError}
          </p>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="icon-sm"
              variant="outline"
              aria-label="Add attachments (PDF only)"
              disabled={disabled}
              onClick={onOpenFilePicker}
            >
              <PlusIcon className="h-4 w-4" />
            </Button>
            <span className="text-xs text-slate-500 dark:text-white">
              <strong>PDFs</strong> only
            </span>
          </div>

          <Button type="submit" disabled={!input.trim() || disabled}>
            {sending ? (
              <>
                <span className="sr-only">Buffering response</span>
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#007AFF] [animation-delay:0ms]" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#007AFF] [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#007AFF] [animation-delay:300ms]" />
              </>
            ) : (
              <>
                <SendIcon className="h-4 w-4" /> Send
              </>
            )}
          </Button>
        </div>
      </form>
    </section>
  );
}
