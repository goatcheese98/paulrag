import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, ChevronDown, ChevronUp, Copy, Check } from "lucide-react";
import { useState } from "react";
import SourceCard from "./SourceCard";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
}

export default function Message({ message }: Props) {
  const [showSources, setShowSources] = useState(true);
  const [copied, setCopied] = useState(false);
  const isAssistant = message.role === "assistant";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-2 sm:gap-3 animate-slide-up ${isAssistant ? "items-start" : "items-start justify-end"}`}>
      {/* Avatar — assistant left */}
      {isAssistant && (
        <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm mt-0.5">
          <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
        </div>
      )}

      <div className={`flex flex-col gap-2 min-w-0 max-w-[88%] sm:max-w-[85%] ${isAssistant ? "" : "items-end"}`}>
        {/* Bubble */}
        <div
          className={
            isAssistant
              ? "relative group bg-white border border-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm w-full"
              : "bg-gradient-to-br from-brand-600 to-brand-700 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm"
          }
        >
          {isAssistant ? (
            <div className="prose-chat text-sm">
              {message.isStreaming && !message.content ? (
                <span className="flex items-center gap-2 text-gray-400">
                  <span className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:300ms]" />
                  </span>
                  Thinking…
                </span>
              ) : (
                <>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                  {message.isStreaming && (
                    <span className="inline-block w-0.5 h-4 bg-brand-500 animate-blink ml-0.5 align-text-bottom" />
                  )}
                </>
              )}

              {/* Copy button — visible on hover when streaming is done */}
              {!message.isStreaming && message.content && (
                <button
                  onClick={handleCopy}
                  title="Copy response"
                  className="absolute top-2.5 right-2.5 p-1.5 rounded-lg text-gray-300 hover:text-gray-500 hover:bg-gray-100 opacity-0 group-hover:opacity-100 transition-all"
                >
                  {copied
                    ? <Check className="w-3.5 h-3.5 text-brand-500" />
                    : <Copy className="w-3.5 h-3.5" />
                  }
                </button>
              )}
            </div>
          ) : (
            <p className="text-sm leading-relaxed break-words">{message.content}</p>
          )}
        </div>

        {/* Sources */}
        {isAssistant && message.sources && message.sources.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setShowSources((v) => !v)}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-brand-600 transition-colors mb-2 ml-1"
            >
              {showSources ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {message.sources.length} source{message.sources.length !== 1 ? "s" : ""} from Paul's videos
            </button>
            {showSources && (
              <div className="grid gap-2 grid-cols-1 sm:grid-cols-2">
                {message.sources.map((src, i) => (
                  <SourceCard key={src.url} source={src} index={i + 1} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Avatar — user right */}
      {!isAssistant && (
        <div className="flex-shrink-0 w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-gray-200 flex items-center justify-center shadow-sm mt-0.5">
          <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-600" />
        </div>
      )}
    </div>
  );
}
