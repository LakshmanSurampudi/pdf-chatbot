"use client";

import { useEffect, useRef, useState } from "react";

import { ChatMessage, getHistory, SourceItem, streamChat } from "@/lib/api";

interface Props {
  sessionId: string;
  documentIds: string[];
}

export default function ChatPanel({ sessionId, documentIds }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getHistory(sessionId).then(setMessages).catch(() => {});
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || documentIds.length === 0 || sending) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: question,
      sources: [],
      created_at: new Date().toISOString(),
    };
    const assistantMessage: ChatMessage = {
      role: "assistant",
      content: "",
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setQuestion("");
    setSending(true);

    try {
      await streamChat(
        sessionId,
        userMessage.content,
        documentIds,
        (sources: SourceItem[]) => {
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...next[next.length - 1], sources };
            return next;
          });
        },
        (token: string) => {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + token };
            return next;
          });
        }
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {documentIds.length === 0 && (
          <p className="text-sm text-gray-500">Select at least one document to start chatting.</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block max-w-2xl rounded-lg px-4 py-2 text-sm ${
                msg.role === "user" ? "bg-black text-white" : "bg-gray-100"
              }`}
            >
              {msg.content || (msg.role === "assistant" && sending ? "..." : "")}
            </div>
            {msg.sources.length > 0 && (
              <div className="mt-2 space-y-1 text-left">
                {msg.sources.map((s, j) => (
                  <details key={j} className="rounded border bg-yellow-50 p-2 text-xs">
                    <summary className="cursor-pointer font-medium">
                      {s.filename} — page {s.page}
                    </summary>
                    <p className="mt-1 text-gray-700">{s.excerpt}</p>
                  </details>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSend} className="flex gap-2 border-t p-4">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your documents..."
          disabled={documentIds.length === 0 || sending}
          className="flex-1 rounded border px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={documentIds.length === 0 || sending}
          className="rounded bg-black px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
