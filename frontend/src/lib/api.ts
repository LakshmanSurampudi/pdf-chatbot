import { supabase } from "./supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

async function authHeader() {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Not authenticated");
  return { Authorization: `Bearer ${token}` };
}

export interface DocumentItem {
  id: string;
  filename: string;
  page_count: number;
  uploaded_at: string;
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const headers = await authHeader();
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_URL}/documents`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "Upload failed");
  return res.json();
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const headers = await authHeader();
  const res = await fetch(`${API_URL}/documents`, { headers });
  if (!res.ok) throw new Error("Failed to load documents");
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const headers = await authHeader();
  await fetch(`${API_URL}/documents/${id}`, { method: "DELETE", headers });
}

export interface SourceItem {
  document_id: string;
  filename: string;
  page: number;
  excerpt: string;
}

export async function streamChat(
  sessionId: string,
  question: string,
  documentIds: string[],
  onSources: (sources: SourceItem[]) => void,
  onToken: (token: string) => void
): Promise<void> {
  const headers = await authHeader();
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, question, document_ids: documentIds }),
  });
  if (!res.ok || !res.body) throw new Error("Chat request failed");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = JSON.parse(line.slice(6));
      if (payload.type === "sources") onSources(payload.sources);
      if (payload.type === "token") onToken(payload.content);
    }
  }
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources: SourceItem[];
  created_at: string;
}

export async function getHistory(sessionId: string): Promise<ChatMessage[]> {
  const headers = await authHeader();
  const res = await fetch(`${API_URL}/chat/${sessionId}/history`, { headers });
  if (!res.ok) throw new Error("Failed to load history");
  return res.json();
}
