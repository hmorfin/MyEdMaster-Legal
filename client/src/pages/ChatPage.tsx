import { useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import ChatMessageList from "@/features/chat/components/ChatMessageList";
import ChatComposer from "@/features/chat/components/ChatComposer";
import { useChatMessagesData } from "@/features/chat/useChatMessagesData";
import type { ChatMessage } from "@/features/chat/types";
import { getStoredUserId } from "@/lib/auth";
import { useSendChatMessage } from "@/features/chat/hooks/useSendChatMessage";
import { useMessageClipboard } from "@/features/chat/hooks/useMessageClipboard";
import type { ChatLayoutOutletContext } from "@/components/ChatLayout";
import { generateDocument, getDocuments, updateDocument} from "@/features/chat/api";
import ReactMarkdown from "react-markdown";

const PDF_MIME = "application/pdf";

function isPdfFile(file: File) {
  return file.type === PDF_MIME || (file.type === "" && /\.pdf$/i.test(file.name));
}

function DocumentRenderer({ content }: { content: string }) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none text-foreground">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}

export default function ChatPage() {
  const { chatId } = useParams();
  const { requestCreateChatDialog } = useOutletContext<ChatLayoutOutletContext>();
  const userId = getStoredUserId();
  const { messages: seedMessages, isLoading, error } = useChatMessagesData(chatId);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [typingMessageId, setTypingMessageId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [sendingChatId, setSendingChatId] = useState<string | null>(null);
  const [readyToGenerate, setReadyToGenerate] = useState(false);
  const [documentContext, setDocumentContext] = useState<object>({});
  const [generatingDocument, setGeneratingDocument] = useState(false);
  const [generatedDocument, setGeneratedDocument] = useState<{
    document_id: string;
    title: string;
    content_markdown: string;
  } | null>(null);
  const [editingDocument, setEditingDocument] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [savingDocument, setSavingDocument] = useState(false);

  const { copiedMessageId, copyMessageText } = useMessageClipboard();

  const { sending, sendError, setSendError, submit } = useSendChatMessage({
    userId,
    chatId,
    onAppendMessages: setMessages,
    onSuccess: (llmMessageId) => setTypingMessageId(llmMessageId),
    onRestoreInput: (value) => setInput(value),
    onAfterSubmit: () => {
      setInput("");
      setAttachedFiles([]);
    },
    onDocumentReady: (ctx) => {
      setDocumentContext(ctx);
      setReadyToGenerate(true);
    },
  });

  const isResponding = sending || typingMessageId !== null;

  useEffect(() => {
    setMessages(seedMessages);
    setTypingMessageId(null);
  }, [seedMessages]);

  useEffect(() => {
    if (!chatId || !userId) return;
    getDocuments(userId, chatId).then(({ payload }) => {
      if (payload?.status === "success" && payload.data && payload.data.length > 0) {
        const latest = payload.data[0];
        if (latest.content_markdown) {
          setGeneratedDocument({
            document_id: latest.document_id,
            title: latest.title,
            content_markdown: latest.content_markdown ?? "",
          });
        }
      }
    }).catch(() => {});
  }, [chatId, userId]);

  function handleAttachFiles(files: FileList | null) {
    setFileError(null);
    if (!files?.length) {
      setAttachedFiles([]);
      return;
    }
    const fileArray = Array.from(files);
    if (!fileArray.every(isPdfFile)) {
      setFileError("Only PDF files are accepted. Please upload PDF documents only.");
      setAttachedFiles([]);
      return;
    }
    setAttachedFiles((prev) => [...prev, ...fileArray]);
  }

  function handleOpenFilePicker() {
    setFileError(null);
    const inputNode = document.getElementById("chat-file-input") as HTMLInputElement | null;
    inputNode?.click();
  }

  async function handleCopyMessage(message: ChatMessage) {
    const copied = await copyMessageText(message.id, message.content);
    if (!copied) {
      setSendError("Unable to copy message text.");
    }
  }

  async function handleSubmitPrompt() {
    if (!chatId) {
      setSendError("Please create a chat session before sending your first message.");
      requestCreateChatDialog();
      return;
    }
    setSendingChatId(chatId);
    try {
      await submit(input, attachedFiles);
    } finally {
      setSendingChatId(null);
    }
  }

  async function handleGenerateDocument() {
    if (!chatId || !userId) return;
    setGeneratingDocument(true);
    try {
      const { payload } = await generateDocument(userId, chatId, documentContext);
      if (payload?.status === "success" && payload.data) {
        setGeneratedDocument({
          document_id: payload.data.document_id,
          title: payload.data.title,
          content_markdown: payload.data.content_markdown,
        });
        setReadyToGenerate(false);
      }
    } finally {
      setGeneratingDocument(false);
    }
  }

  async function handleSaveDocument() {
    if (!chatId || !userId || !generatedDocument) return;
    setSavingDocument(true);
    try {
      const { payload } = await updateDocument(userId, chatId, generatedDocument.document_id, editContent);
      if (payload?.status === "success") {
        setGeneratedDocument((prev) => prev ? { ...prev, content_markdown: editContent } : null);
        setEditingDocument(false);
      }
    } finally {
      setSavingDocument(false);
    }
  }

  return (
    <div className="relative flex h-full min-h-0 bg-background text-foreground">
      <main className={`flex flex-col min-h-0 transition-all duration-300 ${generatedDocument || generatingDocument ? "w-1/2 border-r border-border" : "w-full"}`}>
        <ChatMessageList
          messages={messages}
          chatId={chatId}
          isLoading={isLoading}
          error={error}
          sending={sendingChatId === chatId}
          typingMessageId={typingMessageId}
          copiedMessageId={copiedMessageId}
          onTypingComplete={(id) =>
            setTypingMessageId((current) => (current === id ? null : current))
          }
          onCopyMessage={handleCopyMessage}
        />

        {readyToGenerate && (
          <div className="mx-4 mb-3 rounded-xl border border-border bg-muted/50 p-4 flex items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              All context gathered. Ready to generate your document.
            </p>
            <button
              onClick={handleGenerateDocument}
              disabled={generatingDocument}
              className="rounded-lg bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:opacity-50"
            >
              {generatingDocument ? "Generating..." : "Generate Document"}
            </button>
          </div>
        )}

        <ChatComposer
          input={input}
          attachedFiles={attachedFiles}
          fileError={fileError}
          sendError={sendError}
          sending={isResponding}
          onInputChange={setInput}
          onSubmitPrompt={handleSubmitPrompt}
          onAttachFiles={handleAttachFiles}
          onRemoveAttachedFile={(index) =>
            setAttachedFiles((prev) => prev.filter((_, i) => i !== index))
          }
          onOpenFilePicker={handleOpenFilePicker}
        />
      </main>

      {generatingDocument && !generatedDocument && (
        <div className="w-1/2 flex flex-col min-h-0 bg-background border-l border-border absolute right-0 top-0 bottom-0">
          <div className="flex items-center justify-between border-b border-border px-6 py-3">
            <div className="h-4 w-48 rounded bg-muted animate-pulse" />
          </div>
          <div className="flex-1 overflow-y-auto px-8 py-6 space-y-3">
            <div className="h-6 w-3/4 rounded bg-muted animate-pulse" />
            <div className="h-4 w-full rounded bg-muted animate-pulse" />
            <div className="h-4 w-full rounded bg-muted animate-pulse" />
            <div className="h-4 w-5/6 rounded bg-muted animate-pulse" />
            <div className="h-6 w-1/2 rounded bg-muted animate-pulse mt-4" />
            <div className="h-4 w-full rounded bg-muted animate-pulse" />
            <div className="h-4 w-full rounded bg-muted animate-pulse" />
            <div className="h-4 w-2/3 rounded bg-muted animate-pulse" />
            <div className="h-6 w-1/2 rounded bg-muted animate-pulse mt-4" />
            <div className="h-4 w-full rounded bg-muted animate-pulse" />
            <div className="h-4 w-4/5 rounded bg-muted animate-pulse" />
          </div>
        </div>
      )}

      {generatedDocument && (
        <div className="w-1/2 flex flex-col min-h-0 bg-background">
          <div className="flex items-center justify-between border-b border-border px-6 py-3">
            <h2 className="text-sm font-semibold truncate">{generatedDocument.title}</h2>
            <div className="flex items-center gap-3">
              {!editingDocument ? (
                <>
                  <button
                    onClick={() => {
                      setEditContent(generatedDocument.content_markdown);
                      setEditingDocument(true);
                    }}
                    className="text-xs text-muted-foreground hover:text-foreground underline"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => window.open(`/api/v1/chats/${userId}/${chatId}/documents/${generatedDocument.document_id}/download/?t=${Date.now()}`, "_blank")}
                    className="text-xs text-muted-foreground hover:text-foreground underline"
                  >
                    Download PDF
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleSaveDocument}
                    disabled={savingDocument}
                    className="text-xs text-foreground hover:opacity-80 underline disabled:opacity-50"
                  >
                    {savingDocument ? "Saving..." : "Save"}
                  </button>
                  <button
                    onClick={() => setEditingDocument(false)}
                    className="text-xs text-muted-foreground hover:text-foreground underline"
                  >
                    Cancel
                  </button>
                </>
              )}
              <button
                onClick={() => setGeneratedDocument(null)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto px-8 py-6">
            {editingDocument ? (
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-full min-h-[600px] resize-none bg-background text-foreground text-sm font-mono border border-border rounded-lg p-4 focus:outline-none focus:ring-2 focus:ring-foreground/20"
              />
            ) : (
              <DocumentRenderer content={generatedDocument.content_markdown} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}