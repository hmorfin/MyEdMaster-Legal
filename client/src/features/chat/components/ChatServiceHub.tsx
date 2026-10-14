import { useNavigate } from "react-router-dom";
import { GraduationCap, MessagesSquare, FileText } from "lucide-react";

export default function ChatServiceHub() {
  const navigate = useNavigate();

  return (
    <div className="grid gap-4 md:grid-cols-3 md:gap-6">
      <button
        type="button"
        onClick={() => navigate("/tutoring")}
        className="group flex flex-col items-start gap-4 rounded-2xl border border-border bg-card p-6 text-left shadow-sm transition-transform hover:translate-y-[-2px] md:p-8"
      >
        <span
          className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-muted"
          aria-hidden
        >
          <GraduationCap className="h-6 w-6 text-foreground" />
        </span>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-foreground md:text-xl">Tutoring service</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground md:text-base">
            Guided learning and support on legal topics.
          </p>
        </div>
        <span className="text-sm font-medium text-foreground group-hover:underline">Enter tutoring →</span>
      </button>

      <button
        type="button"
        onClick={() => navigate("/chat/session")}
        className="group flex flex-col items-start gap-4 rounded-2xl border border-border bg-card p-6 text-left shadow-sm transition-transform hover:translate-y-[-2px] md:p-8"
      >
        <span
          className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-muted"
          aria-hidden
        >
          <MessagesSquare className="h-6 w-6 text-foreground" />
        </span>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-foreground md:text-xl">Chat session</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground md:text-base">
            Open the legal assistant to interact.
          </p>
        </div>
        <span className="text-sm font-medium text-foreground group-hover:underline">Open chat →</span>
      </button>

      <button
        type="button"
        onClick={() => navigate("/chat/document")}
        className="group flex flex-col items-start gap-4 rounded-2xl border border-border bg-card p-6 text-left shadow-sm transition-transform hover:translate-y-[-2px] md:p-8"
      >
        <span
          className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-muted"
          aria-hidden
        >
          <FileText className="h-6 w-6 text-foreground" />
        </span>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-foreground md:text-xl">Generate a document</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground md:text-base">
            Create tailored legal contracts and agreements specific to your situation.
          </p>
        </div>
        <span className="text-sm font-medium text-foreground group-hover:underline">Create document →</span>
      </button>
    </div>
  );
}