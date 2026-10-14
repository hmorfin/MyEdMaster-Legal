import { useMemo, useState } from "react";
import { Navigate, Outlet, useLocation, useParams } from "react-router-dom";
import AppSidebar from "@/components/AppSidebar";
import { useChatAppData } from "@/features/chat/useChatAppData";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { getStoredUserId } from "@/lib/auth";
import { usePageTitleOverride } from "@/components/PageTitleProvider";
import { Download } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

export type ChatLayoutOutletContext = {
  requestCreateChatDialog: () => void;
};

export default function ChatLayout() {
  const { pathname } = useLocation();
  const { chatId } = useParams();
  const { data, isLoading, error, refetch } = useChatAppData();
  const userId = getStoredUserId();
  const [createChatAutoOpen, setCreateChatAutoOpen] = useState(0);

  if (!userId) {
    return <Navigate to="/log-in" replace />;
  }

  const isServiceSelectionPage = pathname === "/chat" || pathname === "/chat/";

  const pageTitle = useMemo(() => {
    if (isServiceSelectionPage) return "Choose a service";
    if (!chatId) return "New Chat";
    const selectedChat = data?.chats.find((chat) => chat.id === chatId);
    return selectedChat?.title ?? "Chat";
  }, [chatId, data, isServiceSelectionPage]);

  usePageTitleOverride(pageTitle);

  function requestCreateChatDialog() {
    setCreateChatAutoOpen((prev) => prev + 1);
  }

  return (
    <SidebarProvider>
      <AppSidebar
        chats={data?.chats ?? []}
        documentChats={data?.documentChats ?? []}
        user={data?.user ?? null}
        activeChatId={chatId}
        isLoading={isLoading}
        error={error}
        onChatCreated={refetch}
        createChatAutoOpen={createChatAutoOpen}
        isServiceSelectionPage={isServiceSelectionPage}
      />
      <SidebarInset className="flex h-screen flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background px-4">
          {!isServiceSelectionPage ? <SidebarTrigger /> : null}
          <h1 className="text-sm font-semibold">{pageTitle}</h1>
          {chatId && (
            <a
              href={`${API_BASE_URL}/chats/${userId}/${chatId}/export/`}
              download={`chat-${chatId}.txt`}
              className="ml-auto flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 dark:hover:bg-[#2c2c2e]"
            >
              <Download className="h-3.5 w-3.5" />
              Export
            </a>
          )}
        </header>
        <div className="flex-1 min-h-0 overflow-hidden">
          <Outlet context={{ requestCreateChatDialog } satisfies ChatLayoutOutletContext} />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
