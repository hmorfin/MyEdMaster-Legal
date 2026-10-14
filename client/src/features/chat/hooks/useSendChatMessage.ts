import { useState } from "react";
import type { ChatMessage } from "@/features/chat/types";
import { sendChatMessage } from "@/features/chat/api";

type UseSendChatMessageParams = {
  userId: string | null;
  chatId: string | undefined;
  onAppendMessages: (updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
  onSuccess: (llmMessageId: string) => void;
  onRestoreInput: (value: string) => void;
  onAfterSubmit: () => void;
  onDocumentReady?: (documentContext: object) => void;
};

export function useSendChatMessage({
  userId,
  chatId,
  onAppendMessages,
  onSuccess,
  onRestoreInput,
  onAfterSubmit,
  onDocumentReady,
}: UseSendChatMessageParams) {
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  async function submit(prompt: string, files: File[]) {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || sending || !chatId) return;

    if (!userId) {
      setSendError("No logged-in user found. Please log in again.");
      return;
    }

    const optimisticId = `optimistic-${crypto.randomUUID()}`;
    const documents =
      files.length > 0
        ? files.map((f) => ({
            document_id: "",
            file_name: f.name,
            status: "uploaded",
          }))
        : undefined;
    onAppendMessages((prev) => [
      ...prev,
      {
        id: optimisticId,
        role: "user",
        content: trimmedPrompt,
        ...(documents ? { documents } : {}),
      },
    ]);

    setSendError(null);
    setSending(true);
    onAfterSubmit();

    try {
      const { response, payload } = await sendChatMessage(userId, chatId, trimmedPrompt, files);

      if (!response.ok || payload?.status !== "success" || !payload.data) {
        setSendError(payload?.message ?? `Send failed (HTTP ${response.status}).`);
        onAppendMessages((prev) => prev.filter((m) => m.id !== optimisticId));
        onRestoreInput(trimmedPrompt);
        return;
      }

      const llmMessage: ChatMessage = {
        id: payload.data.chat_message_id,
        role: "llm",
        content: payload.data.response,
        knowledge_sources: payload.data.knowledge_sources ?? [],
      };

      onAppendMessages((prev) => [...prev, llmMessage]);
      onSuccess(llmMessage.id);
      if (payload.data.ready_to_generate && payload.data.document_context) {
        onDocumentReady?.(payload.data.document_context);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Network error while sending.";
      setSendError(message);
      onAppendMessages((prev) => prev.filter((m) => m.id !== optimisticId));
      onRestoreInput(trimmedPrompt);
    } finally {
      setSending(false);
    }
  }

  return { sending, sendError, setSendError, submit };
}
