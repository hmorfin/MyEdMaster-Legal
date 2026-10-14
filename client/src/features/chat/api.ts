import { API_BASE_URL } from "@/lib/api";

export type BackendChat = {
  chat_id: string;
  chat_name: string;
  mode?: string;
  created_at: string;
  updated_at: string;
};

export type ChatListResponse = {
  status: "success" | "error";
  data?: {
    user_id: string;
    chats: BackendChat[];
  };
  message?: string;
};

export type SelfAssessmentData = {
  legal_domain: string;
  branch: string;
  baseline_familiarity: string;
  primary_intent: string;
  self_assessment_status: string;
  global_highlights: string[];
  example_text: string;
  empty_template: {
    title: string;
    sections: {
      heading: string;
      prompt: string;
      placeholders: string[];
    }[];
  } | null;
};

export type CreateChatResponse = {
  status: "success" | "error";
  data?: {
    chat_id: string;
    chat_name: string;
    created_at: string;
    updated_at: string;
    user_inputs: {
      legal_situation: string;
      prior_experience: string;
      desired_outcome: string;
      jurisdiction: string;
    };
    self_assessment_data: SelfAssessmentData;
  };
  message?: string;
};

export type UpdateChatResponse = {
  status: "success" | "error";
  data?: {
    chat_id: string;
    chat_name: string;
    user_id: string;
    created_at: string;
    updated_at: string;
  };
  message?: string;
};

export type DeleteChatResponse = {
  status: "success" | "error";
  data?: {
    chat_id: string;
    user_id: string;
  };
  message?: string;
};

export type BackendMessage = {
  chat_message_id: string;
  role: "user" | "llm";
  content: string;
  created_at: string;
  documents?: { document_id: string; file_name: string; status: string }[];
};

export type ChatMessagesResponse = {
  status: "success" | "error";
  data?: {
    user_id: string;
    chat_id: string;
    chat_messages: BackendMessage[];
  };
  message?: string;
};

export type SendChatMessageResponse = {
  status: "success" | "error";
  data?: {
    chat_message_id: string;
    response: string;
    ready_to_generate?: boolean;
    document_context?: object;
    knowledge_sources?: { text: string; score: number; source: string }[];  // 加这行
  };
  message?: string;
};

function chatsBase(): string {
  return `${API_BASE_URL.replace(/\/+$/, "")}/chats`;
}

export async function fetchUserChats(userId: string): Promise<{ response: Response; payload: ChatListResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/`);
  const payload = (await response.json().catch(() => null)) as ChatListResponse | null;
  return { response, payload };
}

export async function createChat(
  userId: string,
  legalSituation: string,
  priorExperience: string,
  desiredOutcome: string,
  jurisdiction: string
): Promise<{ response: Response; payload: CreateChatResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      legal_situation: legalSituation,
      prior_experience: priorExperience,
      desired_outcome: desiredOutcome,
      jurisdiction: jurisdiction,
    }),
  });
  const payload = (await response.json().catch(() => null)) as CreateChatResponse | null;
  return { response, payload };
}

export async function updateChat(
  userId: string,
  chatId: string,
  chatName: string
): Promise<{ response: Response; payload: UpdateChatResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/${chatId}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_name: chatName }),
  });
  const payload = (await response.json().catch(() => null)) as UpdateChatResponse | null;
  return { response, payload };
}

export async function deleteChat(
  userId: string,
  chatId: string
): Promise<{ response: Response; payload: DeleteChatResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/${chatId}/`, {
    method: "DELETE",
  });
  const payload = (await response.json().catch(() => null)) as DeleteChatResponse | null;
  return { response, payload };
}

export async function fetchChatMessages(
  userId: string,
  chatId: string
): Promise<{ response: Response; payload: ChatMessagesResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/${chatId}/messages/`);
  const payload = (await response.json().catch(() => null)) as ChatMessagesResponse | null;
  return { response, payload };
}

export async function sendChatMessage(
  userId: string,
  chatId: string,
  query: string,
  files: File[]
): Promise<{ response: Response; payload: SendChatMessageResponse | null }> {
  const formData = new FormData();
  formData.append("query", query);
  for (const file of files) {
    formData.append("documents", file);
  }

  const response = await fetch(`${chatsBase()}/${userId}/${chatId}/messages/`, {
    method: "POST",
    body: formData,
  });

  const payload = (await response.json().catch(() => null)) as SendChatMessageResponse | null;
  return { response, payload };
}

export type DimensionInput = {
  examples: string;
  uncertainties: string;
};

export type SubmitSelfAssessmentResponse = {
  status: "success" | "error";
  data?: {
    chat_id: string;
    self_assessment_status: string;
    priority: {
      top_dimension: string;
      top_label_in_top_dimension: string;
      dimension_scores: Record<string, number>;
      dimension_counts: Record<string, Record<string, number>>;
    };
  };
  message?: string;
};

export type SkipSelfAssessmentResponse = {
  status: "success" | "error";
  data?: {
    chat_id: string;
    self_assessment_status: string;
  };
  message?: string;
};

export async function submitSelfAssessment(
  userId: string,
  chatId: string,
  facts: DimensionInput,
  strategies: DimensionInput,
  procedures: DimensionInput,
  rationales: DimensionInput
): Promise<{ response: Response; payload: SubmitSelfAssessmentResponse | null }> {
  const response = await fetch(
    `${chatsBase()}/${userId}/${chatId}/self-assessment/submit/`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ facts, strategies, procedures, rationales }),
    }
  );
  const payload = (await response.json().catch(() => null)) as SubmitSelfAssessmentResponse | null;
  return { response, payload };
}

export async function skipSelfAssessment(
  userId: string,
  chatId: string
): Promise<{ response: Response; payload: SkipSelfAssessmentResponse | null }> {
  const response = await fetch(
    `${chatsBase()}/${userId}/${chatId}/self-assessment/skip/`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    }
  );
  const payload = (await response.json().catch(() => null)) as SkipSelfAssessmentResponse | null;
  return { response, payload };
}

export type CreateDocumentChatResponse = {
  status: "success" | "error";
  data?: {
    chat_id: string;
    chat_name: string;
    mode: string;
    created_at: string;
    updated_at: string;
  };
  message?: string;
};

export type GenerateDocumentResponse = {
  status: "success" | "error";
  data?: {
    document_id: string;
    title: string;
    document_type: string;
    version: number;
    content_markdown: string;
    storage_path: string | null;
    created_at: string;
  };
  message?: string;
};

export type GetDocumentsResponse = {
  status: "success" | "error";
  data?: {
    document_id: string;
    title: string;
    document_type: string;
    version: number;
    content_markdown?: string;
    storage_path: string | null;
    created_at: string;
  }[];
  message?: string;
};

export async function createDocumentChat(
  userId: string,
  documentType: string,
  jurisdiction: string
): Promise<{ response: Response; payload: CreateDocumentChatResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/documents/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_type: documentType,
      jurisdiction: jurisdiction,
    }),
  });
  const payload = (await response.json().catch(() => null)) as CreateDocumentChatResponse | null;
  return { response, payload };
}

export async function generateDocument(
  userId: string,
  chatId: string,
  documentContext: object
): Promise<{ response: Response; payload: GenerateDocumentResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/${chatId}/generate-document/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_context: documentContext }),
  });
  const payload = (await response.json().catch(() => null)) as GenerateDocumentResponse | null;
  return { response, payload };
}

export async function getDocuments(
  userId: string,
  chatId: string
): Promise<{ response: Response; payload: GetDocumentsResponse | null }> {
  const response = await fetch(`${chatsBase()}/${userId}/${chatId}/documents/`);
  const payload = (await response.json().catch(() => null)) as GetDocumentsResponse | null;
  return { response, payload };
}

export async function updateDocument(userId: string, chatId: string, documentId: string, contentMarkdown: string) {
  const response = await fetch(
    `/api/v1/chats/${userId}/${chatId}/documents/${documentId}/`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content_markdown: contentMarkdown }),
    }
  );
  const payload = await response.json().catch(() => null);
  return { response, payload };
}