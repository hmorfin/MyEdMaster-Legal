import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ChevronUp,
  Home,
  LogOut,
  Moon,
  MoreHorizontal,
  Pencil,
  Settings,
  Sun,
  Trash2,
  GraduationCap,
  UserCircle2,
  ChartArea,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import type { AppSidebarProps, ChatUser } from "@/features/chat/types";
import { CreateChatDialog } from "./CreateChatDialog";
import { clearStoredUser, getStoredUserId } from "@/lib/auth";
import { applyTheme, isDarkModeEnabled } from "@/lib/theme";
import { deleteChat, updateChat } from "@/features/chat/api";
import { useAsyncAction } from "@/hooks/use-async-action";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import metyMainLogo from "@/assets/images/Mety Main Logo.png";
import metyMainWhiteLogo from "@/assets/images/Mety Main Logo White.png";

function SidebarProfileMenu({ user }: { user: ChatUser | null }) {
  const [open, setOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(isDarkModeEnabled());
  const navigate = useNavigate();

  return (
    <div className="relative">
      {open ? (
        <div className="bg-sidebar absolute right-0 bottom-14 z-20 w-56 rounded-lg border border-sidebar-border p-2 shadow-lg">
          <div className="mb-2 px-2 py-1 text-xs text-sidebar-foreground/70">
            Account actions
          </div>
          <div className="space-y-1">
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={() => {
                navigate("/me");
                setOpen(false);
              }}
            >
              <UserCircle2 className="mr-2 h-4 w-4" />
              Profile
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={() => {
                navigate("/statistics");
                setOpen(false);
              }}
            >
              <ChartArea className="mr-2 h-4 w-4" />
              Statistics
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={() => {
                navigate("/settings");
                setOpen(false);
              }}
            >
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start"
              onClick={() => {
                const nextMode = darkMode ? "light" : "dark";
                applyTheme(nextMode);
                setDarkMode(nextMode === "dark");
                setOpen(false);
              }}
            >
              {darkMode ? (
                <Sun className="mr-2 h-4 w-4" />
              ) : (
                <Moon className="mr-2 h-4 w-4" />
              )}
              {darkMode ? "Light Mode" : "Dark Mode"}
            </Button>
            <Button
              variant="ghost"
              className="w-full justify-start !bg-[#1F1F1F] !text-white hover:!bg-[#2A2A2A]"
              onClick={() => {
                clearStoredUser();
                navigate("/");
                setOpen(false);
              }}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </Button>
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="hover:bg-sidebar-accent flex w-full items-center gap-3 rounded-md border border-sidebar-border p-2 text-left group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:gap-0"
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-300 text-xs font-semibold text-slate-900">
          {user?.initials ?? "U"}
        </div>
        <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
          <p className="truncate text-sm font-medium">
            {user?.name ?? "Loading user"}
          </p>
          <p className="truncate text-xs text-sidebar-foreground/70">
            {user?.email ?? ""}
          </p>
        </div>
        <ChevronUp className="h-4 w-4 group-data-[collapsible=icon]:hidden" />
      </button>
    </div>
  );
}

export default function AppSidebar({
  chats,
  documentChats,
  user,
  activeChatId,
  error,
  onChatCreated,
  createChatAutoOpen,
  onCreateChatAutoOpenConsumed,
  isServiceSelectionPage = false,
}: AppSidebarProps) {
  const navigate = useNavigate();
  const [renameChatId, setRenameChatId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [deleteChatTarget, setDeleteChatTarget] = useState<{
    id: string;
    title: string;
  } | null>(null);
  const [dotsMenuChatId, setDotsMenuChatId] = useState<string | null>(null);
  const dotsMenuRef = useRef<HTMLDivElement>(null);
  const { loading: savingRename, run: runRename } = useAsyncAction();
  const { loading: deletingChat, run: runDelete } = useAsyncAction();

  // Close dots menu when clicking outside
  useEffect(() => {
    if (dotsMenuChatId === null) return;
    function handleClickOutside(event: MouseEvent) {
      if (dotsMenuRef.current?.contains(event.target as Node)) return;
      setDotsMenuChatId(null);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dotsMenuChatId]);

  function openRenameDialog(chatId: string, currentTitle: string) {
    setDotsMenuChatId(null);
    setRenameChatId(chatId);
    setRenameValue(currentTitle);
    setRenameError(null);
  }

  function closeRenameDialog() {
    setRenameChatId(null);
    setRenameValue("");
    setRenameError(null);
  }

  function openDeleteDialog(chatId: string, chatTitle: string) {
    setDotsMenuChatId(null);
    setDeleteChatTarget({ id: chatId, title: chatTitle });
  }

  function closeDeleteDialog() {
    if (deletingChat) return;
    setDeleteChatTarget(null);
  }

  async function handleConfirmRename() {
    const userId = getStoredUserId();
    if (!userId || !renameChatId) {
      setRenameError("Unable to rename chat. Please log in again.");
      return;
    }

    const trimmed = renameValue.trim();
    if (!trimmed) {
      setRenameError("Chat name is required.");
      return;
    }

    await runRename(async () => {
      const { response, payload } = await updateChat(
        userId,
        renameChatId,
        trimmed,
      );
      if (!response.ok || payload?.status !== "success") {
        setRenameError(
          payload?.message || `Rename failed (HTTP ${response.status}).`,
        );
        return;
      }

      closeRenameDialog();
      // Trigger a refresh of the chat list from the parent layout.
      onChatCreated?.();
      // If we are currently on this chat, keep the route but title will refresh via useChatAppData.
      if (activeChatId === renameChatId) {
        navigate(`/chat/${renameChatId}`);
      }
    });
  }

  async function handleDeleteChat() {
    if (!deleteChatTarget) return;

    const userId = getStoredUserId();
    if (!userId) return;

    await runDelete(async () => {
      const { response, payload } = await deleteChat(
        userId,
        deleteChatTarget.id,
      );
      if (!response.ok || payload?.status !== "success") {
        console.error(
          payload?.message || `Delete failed (HTTP ${response.status}).`,
        );
        return;
      }
      const deletedChatId = deleteChatTarget.id;
      closeDeleteDialog();
      onChatCreated?.();
      if (activeChatId === deletedChatId) {
        navigate("/chat");
      }
    });
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="Home">
              <Link to="/" className="flex items-center gap-2">
                <Home className="h-4 w-4 shrink-0" />
                <span className="group-data-[collapsible=icon]:hidden">
                  <img
                    src={metyMainLogo}
                    alt="Mety"
                    className="h-3 w-auto object-contain dark:hidden"
                  />
                  <img
                    src={metyMainWhiteLogo}
                    alt="Mety"
                    className="hidden h-3 w-auto object-contain dark:block"
                  />
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          {!isServiceSelectionPage ? (
            <SidebarMenuItem>
              <CreateChatDialog
                onChatCreated={onChatCreated}
                autoOpen={createChatAutoOpen}
                onAutoOpenConsumed={onCreateChatAutoOpenConsumed}
              />
            </SidebarMenuItem>
          ) : null}
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="Tutorial">
              <Link to="/tutoring" className="flex items-center gap-2">
                <GraduationCap className="h-4 w-4 shrink-0" />
                <span className="group-data-[collapsible=icon]:hidden">
                  Tutorial
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {!isServiceSelectionPage ? (
        <SidebarContent>
          {documentChats.length > 0 && (
            <SidebarGroup className="group-data-[collapsible=icon]:hidden">
              <SidebarGroupLabel>Document Chats</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {documentChats.map((chat) => (
                    <SidebarMenuItem key={chat.id}>
                      <div className="flex items-center gap-1">
                        <ContextMenu>
                          <ContextMenuTrigger asChild>
                            <SidebarMenuButton
                              asChild
                              isActive={chat.id === activeChatId}
                              tooltip={chat.title}
                              className="flex-1"
                            >
                              <Link to={`/chat/${chat.id}`}>
                                <span className="truncate">{chat.title}</span>
                              </Link>
                            </SidebarMenuButton>
                          </ContextMenuTrigger>
                          <ContextMenuContent>
                            <ContextMenuItem onClick={() => openRenameDialog(chat.id, chat.title)}>
                              <Pencil className="mr-2 h-3 w-3" />
                              <span>Rename</span>
                            </ContextMenuItem>
                            <ContextMenuItem
                              className="text-red-600 focus:bg-red-50 dark:focus:bg-red-950"
                              onClick={() => openDeleteDialog(chat.id, chat.title)}
                            >
                              <Trash2 className="mr-2 h-3 w-3" />
                              <span>Delete</span>
                            </ContextMenuItem>
                          </ContextMenuContent>
                        </ContextMenu>
                        <div className="relative" ref={dotsMenuChatId === chat.id ? dotsMenuRef : undefined}>
                          <button
                            type="button"
                            className="inline-flex h-5 w-5 items-center justify-center rounded hover:bg-sidebar-accent text-sidebar-foreground/70"
                            aria-label="Chat options"
                            onClick={(e) => {
                              e.preventDefault();
                              setDotsMenuChatId((id) => id === chat.id ? null : chat.id);
                            }}
                          >
                            <MoreHorizontal className="h-3 w-3" />
                          </button>
                          {dotsMenuChatId === chat.id && (
                            <div className="bg-popover text-popover-foreground absolute right-0 top-full z-50 mt-1 min-w-[8rem] overflow-hidden rounded-md border p-1 shadow-md">
                              <button
                                type="button"
                                className="focus:bg-accent focus:text-accent-foreground flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-sidebar-accent"
                                onClick={() => openRenameDialog(chat.id, chat.title)}
                              >
                                <Pencil className="mr-2 h-3 w-3" />
                                <span>Rename</span>
                              </button>
                              <button
                                type="button"
                                className="focus:bg-red-50 dark:focus:bg-red-950 flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm text-red-600 outline-none hover:bg-red-50 dark:hover:bg-red-950"
                                onClick={() => openDeleteDialog(chat.id, chat.title)}
                              >
                                <Trash2 className="mr-2 h-3 w-3" />
                                <span>Delete</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )}

          <SidebarGroup className="group-data-[collapsible=icon]:hidden">
            <SidebarGroupLabel>Chat History</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {error ? (
                  <p className="px-2 py-1 text-xs text-red-600">{error}</p>
                ) : null}
                {chats.map((chat) => (
                  <SidebarMenuItem key={chat.id}>
                    <div className="flex items-center gap-1">
                      <ContextMenu>
                        <ContextMenuTrigger asChild>
                          <SidebarMenuButton
                            asChild
                            isActive={chat.id === activeChatId}
                            tooltip={chat.title}
                            className="flex-1"
                          >
                            <Link to={`/chat/${chat.id}`}>
                              <span className="truncate">{chat.title}</span>
                            </Link>
                          </SidebarMenuButton>
                        </ContextMenuTrigger>
                        <ContextMenuContent>
                          <ContextMenuItem onClick={() => openRenameDialog(chat.id, chat.title)}>
                            <Pencil className="mr-2 h-3 w-3" />
                            <span>Rename</span>
                          </ContextMenuItem>
                          <ContextMenuItem
                            className="text-red-600 focus:bg-red-50 dark:focus:bg-red-950"
                            onClick={() => openDeleteDialog(chat.id, chat.title)}
                          >
                            <Trash2 className="mr-2 h-3 w-3" />
                            <span>Delete</span>
                          </ContextMenuItem>
                        </ContextMenuContent>
                      </ContextMenu>
                      <div className="relative" ref={dotsMenuChatId === chat.id ? dotsMenuRef : undefined}>
                        <button
                          type="button"
                          className="inline-flex h-5 w-5 items-center justify-center rounded hover:bg-sidebar-accent text-sidebar-foreground/70"
                          aria-label="Chat options"
                          onClick={(e) => {
                            e.preventDefault();
                            setDotsMenuChatId((id) => id === chat.id ? null : chat.id);
                          }}
                        >
                          <MoreHorizontal className="h-3 w-3" />
                        </button>
                        {dotsMenuChatId === chat.id && (
                          <div className="bg-popover text-popover-foreground absolute right-0 top-full z-50 mt-1 min-w-[8rem] overflow-hidden rounded-md border p-1 shadow-md">
                            <button
                              type="button"
                              className="focus:bg-accent focus:text-accent-foreground flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-sidebar-accent"
                              onClick={() => openRenameDialog(chat.id, chat.title)}
                            >
                              <Pencil className="mr-2 h-3 w-3" />
                              <span>Rename</span>
                            </button>
                            <button
                              type="button"
                              className="focus:bg-red-50 dark:focus:bg-red-950 flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm text-red-600 outline-none hover:bg-red-50 dark:hover:bg-red-950"
                              onClick={() => openDeleteDialog(chat.id, chat.title)}
                            >
                              <Trash2 className="mr-2 h-3 w-3" />
                              <span>Delete</span>
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
      ) : null}
      {!isServiceSelectionPage ? (
        <SidebarFooter className="group-data-[collapsible=icon]:hidden">
          <SidebarProfileMenu user={user} />
        </SidebarFooter>
      ) : null}
      <SidebarRail />
      <Dialog
        open={renameChatId !== null}
        onOpenChange={(open) => {
          if (!open) closeRenameDialog();
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Rename chat</DialogTitle>
            <DialogDescription>
              Update the name of this chat so it is easier to recognize later.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Input
              value={renameValue}
              onChange={(event) => setRenameValue(event.target.value)}
              placeholder="Enter a new chat name"
            />
            {renameError ? (
              <p className="text-sm text-red-600">{renameError}</p>
            ) : null}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={closeRenameDialog}>
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleConfirmRename}
              disabled={savingRename}
            >
              {savingRename ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <AlertDialog
        open={deleteChatTarget !== null}
        onOpenChange={(open) => {
          if (!open) closeDeleteDialog();
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete chat?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. "
              {deleteChatTarget?.title ?? "This chat"}" will be permanently
              removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deletingChat}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void handleDeleteChat();
              }}
              disabled={deletingChat}
              className="bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-600"
            >
              {deletingChat ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Sidebar>
  );
}
