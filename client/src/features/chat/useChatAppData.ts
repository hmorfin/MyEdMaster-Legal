import { useEffect, useRef, useState } from "react";
import type { ChatAppData, ChatListItem, ChatUser } from "@/features/chat/types";
import { getStoredUserId, getStoredUserEmail } from "@/lib/auth";
import { fetchUserChats } from "@/features/chat/api";

type UseChatAppDataResult = {
  data: ChatAppData | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
};

function buildChatUser(userId: string, email: string): ChatUser {
  const prefix = email.split("@")[0] ?? "";
  const parts = prefix.split(/[._\-]/);
  const initials =
    parts.length >= 2
      ? (parts[0][0] ?? "") + (parts[1][0] ?? "")
      : prefix.slice(0, 2) ?? "??";
  return {
    id: userId,
    name: prefix,
    email,
    initials: initials.toUpperCase(),
  };
}

function formatUpdatedAt(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffMins < 1) return "now";
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;
  return date.toLocaleDateString();
}

export function useChatAppData(): UseChatAppDataResult {
  const [data, setData] = useState<ChatAppData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const hasLoadedOnce = useRef(false);

  const refetch = () => setTick((n) => n + 1);

  useEffect(() => {
    let isCancelled = false;

    async function loadData() {
      if (!hasLoadedOnce.current) setIsLoading(true);
      setError(null);

      const userId = getStoredUserId();
      const email = getStoredUserEmail() ?? "";

      if (!userId) {
        if (!isCancelled) {
          setError("No logged-in user found.");
          setIsLoading(false);
        }
        return;
      }

      try {
        const { response, payload } = await fetchUserChats(userId);

        if (!response.ok || payload?.status !== "success" || !payload.data) {
          if (!isCancelled) {
            setError(payload?.message ?? `Failed to load chats (HTTP ${response.status}).`);
          }
          return;
        }

        const allChats: ChatListItem[] = payload.data.chats.map((c) => ({
          id: c.chat_id,
          title: c.chat_name,
          updatedAt: formatUpdatedAt(c.updated_at),
          mode: c.mode,
        }));

        const chats = allChats.filter((c) => c.mode !== "document");
        const documentChats = allChats.filter((c) => c.mode === "document");

        if (!isCancelled) {
          hasLoadedOnce.current = true;
          setData({ user: buildChatUser(userId, email), chats, documentChats });
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : "Failed to load chats.");
        }
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    }

    void loadData();
    return () => { isCancelled = true; };
  }, [tick]);

  return { data, isLoading, error, refetch };
}
