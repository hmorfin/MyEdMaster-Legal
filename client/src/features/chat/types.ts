export type ChatListItem = {
  id: string;
  title: string;
  updatedAt: string;
  mode?: string;
};

export type ChatUser = {
  id: string;
  name: string;
  email: string;
  initials: string;
};

export type ChatAppData = {
  user: ChatUser;
  chats: ChatListItem[];
  documentChats: ChatListItem[];
};

export type ChatRole = "user" | "llm";

export type KnowledgeSource = {
  text: string;
  score: number;
  source: string;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  documents?: { document_id: string; file_name: string; status: string }[];
  knowledge_sources?: KnowledgeSource[];
};

export type AppSidebarProps = {
  chats: ChatListItem[];
  documentChats: ChatListItem[];
  user: ChatUser | null;
  activeChatId?: string;
  isLoading: boolean;
  error: string | null;
  onChatCreated: () => void;
  createChatAutoOpen?: number;
  onCreateChatAutoOpenConsumed?: () => void;
  isServiceSelectionPage?: boolean;
};