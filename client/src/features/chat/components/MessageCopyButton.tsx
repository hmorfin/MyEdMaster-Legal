import { Check, Copy } from "lucide-react";

type MessageCopyButtonProps = {
  copied: boolean;
  onCopy: () => void;
};

export default function MessageCopyButton({ copied, onCopy }: MessageCopyButtonProps) {
  return (
    <button
      type="button"
      onClick={onCopy}
      className="inline-flex h-6 w-6 items-center justify-center rounded-md text-black transition-colors hover:bg-black/10 dark:text-white dark:hover:bg-white/10"
      aria-label={copied ? "Copied" : "Copy message"}
      title={copied ? "Copied" : "Copy"}
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}
