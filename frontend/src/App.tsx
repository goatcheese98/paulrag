import { useState, useEffect, useRef, useCallback } from "react";
import { Send, RotateCcw, Youtube, Sparkles } from "lucide-react";
import Message from "./components/Message";
import StatusBadge from "./components/StatusBadge";
import type { ChatMessage, Source, StatusResponse } from "./types";

// In production (Cloudflare Pages), set VITE_API_BASE_URL to your Railway backend URL.
// In development, leave it empty — the Vite proxy handles /api/* → localhost:8000.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const SUGGESTED_QUESTIONS = [
  "What is the difference between a fixed and variable rate mortgage?",
  "How does the stress test work in Canada?",
  "What is a HELOC and when should I use one?",
  "How much down payment do I need as a first-time buyer?",
  "What are mortgage penalties and how are they calculated?",
];

function uid() {
  return Math.random().toString(36).slice(2);
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/status`)
      .then((r) => r.json())
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setStatusLoading(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;

    const userMsg: ChatMessage = { id: uid(), role: "user", content: question.trim() };
    const assistantId = uid();
    const assistantMsg: ChatMessage = { id: assistantId, role: "assistant", content: "", isStreaming: true };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setIsLoading(true);

    const history = messages
      .filter((m) => !m.isStreaming)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), history }),
      });

      if (!res.ok || !res.body) throw new Error("Network error");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";
      let sources: Source[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const raw = decoder.decode(value, { stream: true });
        const lines = raw.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") continue;

          try {
            const evt = JSON.parse(payload);
            if (evt.type === "text") {
              accumulated += evt.content;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: accumulated } : m
                )
              );
            } else if (evt.type === "sources") {
              sources = evt.sources;
            }
          } catch {
            // partial JSON, skip
          }
        }
      }

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: accumulated, sources, isStreaming: false }
            : m
        )
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: "Sorry, I couldn't connect to the backend. Make sure the API server is running on port 8000.",
                isStreaming: false,
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const clearChat = () => {
    setMessages([]);
    inputRef.current?.focus();
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="flex-shrink-0 bg-white border-b border-gray-100 shadow-sm z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm">
              <Youtube className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold text-gray-900 leading-tight">Level Up Mortgages AI</h1>
              <p className="text-xs text-gray-500">Powered by Paul Davidescu's videos</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <StatusBadge status={status} loading={statusLoading} />
            {!isEmpty && (
              <button
                onClick={clearChat}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 border border-gray-200 hover:border-gray-300 px-2.5 py-1.5 rounded-lg transition-all"
              >
                <RotateCcw className="w-3 h-3" />
                New chat
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {isEmpty ? (
            /* Welcome screen */
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-400 to-brand-700 flex items-center justify-center shadow-lg mb-5">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Ask Level Up Channel Bot anything</h2>
              <p className="text-gray-500 max-w-md mb-8 text-sm leading-relaxed">
                Get answers about mortgages, home buying, refinancing, and real estate financing —
                backed by timestamps and links to Paul's YouTube videos.
              </p>

              <div className="grid gap-2 w-full max-w-lg">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    disabled={isLoading}
                    className="text-left text-sm px-4 py-3 bg-white border border-gray-200 rounded-xl hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {messages.map((msg) => (
                <Message key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input */}
      <footer className="flex-shrink-0 bg-white border-t border-gray-100 shadow-[0_-2px_12px_rgba(0,0,0,0.04)]">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <form onSubmit={handleSubmit} className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about mortgages, rates, refinancing…"
                rows={1}
                disabled={isLoading}
                className="w-full resize-none rounded-xl border border-gray-200 focus:border-brand-400 focus:ring-2 focus:ring-brand-100 outline-none px-4 py-3 text-sm text-gray-800 placeholder-gray-400 transition-all bg-gray-50 focus:bg-white disabled:opacity-60 max-h-32 overflow-y-auto"
                style={{ minHeight: "44px" }}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = Math.min(el.scrollHeight, 128) + "px";
                }}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="flex-shrink-0 w-11 h-11 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 hover:from-brand-600 hover:to-brand-800 text-white flex items-center justify-center shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <p className="text-center text-[11px] text-gray-400 mt-2">
            Answers are based on Paul Davidescu's videos. Always consult a licensed mortgage professional.
          </p>
        </div>
      </footer>
    </div>
  );
}
