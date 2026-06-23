"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import ChatPanel from "@/components/ChatPanel";
import DocumentSidebar from "@/components/DocumentSidebar";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/lib/useAuth";

export default function Home() {
  const { session, loading, user } = useAuth();
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("chat_session_id");
    if (stored) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time read of browser storage on mount
      setSessionId(stored);
    } else {
      const next = crypto.randomUUID();
      localStorage.setItem("chat_session_id", next);
      setSessionId(next);
    }
  }, []);

  useEffect(() => {
    if (!loading && !session) router.push("/login");
  }, [loading, session, router]);

  if (loading || !session || !sessionId) return null;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <h1 className="font-semibold">PDF Chatbot</h1>
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <span>{user?.email}</span>
          <button onClick={() => supabase.auth.signOut()} className="underline">
            Log out
          </button>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden">
        <DocumentSidebar selectedIds={selectedIds} onSelectionChange={setSelectedIds} />
        <ChatPanel sessionId={sessionId} documentIds={selectedIds} />
      </div>
    </div>
  );
}
