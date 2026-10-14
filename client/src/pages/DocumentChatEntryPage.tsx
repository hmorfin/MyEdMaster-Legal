import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getStoredUserId } from "@/lib/auth";
import { createDocumentChat } from "@/features/chat/api";

const DOCUMENT_TYPES = [
  "Roommate Agreement",
  "Non-Disclosure Agreement",
  "Independent Contractor Agreement",
  "Lease Agreement",
  "Employment Offer Letter",
  "Service Agreement",
  "Bill of Sale",
  "Promissory Note",
  "Power of Attorney",
  "Other",
];

export default function DocumentChatEntryPage() {
  const navigate = useNavigate();
  const [documentType, setDocumentType] = useState("");
  const [customType, setCustomType] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    const userId = getStoredUserId();
    if (!userId) return;

    const finalType = documentType === "Other" ? customType.trim() : documentType;
    if (!finalType) {
      setError("Please select or enter a document type.");
      return;
    }
    if (!jurisdiction.trim()) {
      setError("Please enter your jurisdiction.");
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const { payload } = await createDocumentChat(userId, finalType, jurisdiction.trim());
      if (payload?.status === "success" && payload.data) {
        navigate(`/chat/${payload.data.chat_id}`);
      } else {
        setError(payload?.message ?? "Failed to create document chat.");
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="flex h-full min-h-0 flex-col overflow-y-auto bg-background text-foreground">
      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col justify-center px-6 py-10 md:px-10 md:py-16">
        <h2 className="mb-2 text-center text-xl font-semibold tracking-tight md:text-2xl">
          Generate a Legal Document
        </h2>
        <p className="mb-8 text-center text-sm text-muted-foreground md:text-base">
          Tell us what you need and we'll guide you through creating a tailored document.
        </p>

        <div className="space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium">Document Type</label>
            <select
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-foreground/20"
            >
              <option value="">Select a document type...</option>
              {DOCUMENT_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          {documentType === "Other" && (
            <div>
              <label className="mb-1.5 block text-sm font-medium">Describe the document</label>
              <input
                type="text"
                value={customType}
                onChange={(e) => setCustomType(e.target.value)}
                placeholder="e.g. Pet custody agreement"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-foreground/20"
              />
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium">Jurisdiction</label>
            <select
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-foreground/20"
            >
              <option value="">Select a state...</option>
              {[
                "Alabama","Alaska","Arizona","Arkansas","California","Colorado",
                "Connecticut","Delaware","Florida","Georgia","Hawaii","Idaho",
                "Illinois","Indiana","Iowa","Kansas","Kentucky","Louisiana",
                "Maine","Maryland","Massachusetts","Michigan","Minnesota",
                "Mississippi","Missouri","Montana","Nebraska","Nevada",
                "New Hampshire","New Jersey","New Mexico","New York",
                "North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
                "Pennsylvania","Rhode Island","South Carolina","South Dakota",
                "Tennessee","Texas","Utah","Vermont","Virginia","Washington",
                "West Virginia","Wisconsin","Wyoming","Federal"
              ].map((state) => (
                <option key={state} value={state}>{state}</option>
              ))}
            </select>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="button"
            onClick={handleStart}
            disabled={creating}
            className="w-full rounded-lg bg-foreground px-4 py-2.5 text-sm font-medium text-background hover:opacity-90 disabled:opacity-50"
          >
            {creating ? "Starting..." : "Start Document Chat"}
          </button>
        </div>
      </div>
    </main>
  );
}