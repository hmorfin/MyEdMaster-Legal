import { useEffect, useState } from "react";
import type { ChatMessage } from "@/features/chat/types";
import { getStoredUserId } from "@/lib/auth";
import { fetchChatMessages } from "@/features/chat/api";

type UseChatMessagesDataResult = {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
};

export function useChatMessagesData(chatId: string | undefined): UseChatMessagesDataResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!chatId) {
      setMessages([]);
      setIsLoading(false);
      setError(null);
      return;
    }

    let isCancelled = false;

    async function loadMessages() {
      setIsLoading(true);
      setError(null);
      setMessages([]);

      const userId = getStoredUserId();
      if (!userId) {
        if (!isCancelled) {
          setError("No logged-in user found.");
          setIsLoading(false);
        }
        return;
      }

      try {
        const { response, payload } = await fetchChatMessages(userId, chatId!);

        if (!response.ok || payload?.status !== "success" || !payload.data) {
          if (!isCancelled) {
            setError(payload?.message ?? `Failed to load messages (HTTP ${response.status}).`);
          }
          return;
        }

        const mapped: ChatMessage[] = payload.data.chat_messages.map((m) => ({
          id: m.chat_message_id,
          role: m.role,
          content: m.content,
          ...(m.documents ? { documents: m.documents } : {}),
        }));

        if (!isCancelled) setMessages(mapped);
      } catch (err: unknown) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : "Failed to load messages.");
        }
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    void loadMessages();
    return () => { isCancelled = true; };
  }, [chatId]);

  return { messages, isLoading, error };
}
