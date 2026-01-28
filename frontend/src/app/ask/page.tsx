"use client";

import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Header from "@/components/layout/Header";
import ChatContainer from "@/components/chat/ChatContainer";
import ChatInput from "@/components/chat/ChatInput";
import { Message } from "@/types/chat";

// Separate component that uses useSearchParams
function AskBotPageContent() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const initialQueryProcessed = useRef(false);

  // ✅ Dynamic API URL - auto-detect environment
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // ✅ FIX: Wrap with useCallback to satisfy useEffect dependency
  const handleSendMessage = useCallback(
    async (content: string) => {
      if (isLoading || !content.trim()) return;

      // Add user message
      const userMessage: Message = {
        id: Date.now().toString(),
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        // Build conversation history (last 10 messages)
        const conversationHistory = [...messages, userMessage]
          .slice(-10)
          .map((msg) => ({
            role: msg.role,
            content: msg.content,
          }));

        console.log(`🔗 Calling API: ${API_URL}/api/v1/qa`);

        // Call backend API
        const response = await fetch(`${API_URL}/api/v1/qa`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: content.trim(),
            conversation_history: conversationHistory,
          }),
        });

        console.log(`✅ Response status: ${response.status}`);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log("📦 Response data:", data);

        // Extract answer
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content:
            data.answer || data.message || "Sorry, I couldn't find an answer.",
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, aiMessage]);
      } catch (error: unknown) {
        console.error("❌ Error fetching answer:", error);

        // ✅ Specific error messages
        let errorMsg = "Sorry, there was an error processing your request.";

        // ✅ Type guard for Error object
        if (error instanceof Error) {
          if (error.message.includes("Failed to fetch")) {
            errorMsg =
              "❌ Could not connect to server. Please check if the backend is running at " +
              API_URL;
          } else if (error.message.includes("500")) {
            errorMsg =
              "❌ Server error. The question might be too complex. Try rephrasing it.";
          } else if (error.message.includes("404")) {
            errorMsg = "❌ API endpoint not found. Check backend configuration.";
          } else if (error.message.includes("timeout")) {
            errorMsg = "❌ Request timeout. The server took too long to respond.";
          }
        }

        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: errorMsg,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, messages, API_URL]
  );

  useEffect(() => {
    const query = searchParams.get("q");
    if (query && !initialQueryProcessed.current) {
      initialQueryProcessed.current = true;
      handleSendMessage(query);
    }
  }, [searchParams, handleSendMessage]);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />

      <main className="flex-1 flex flex-col justify-center clear-space py-8 max-w-7xl mx-auto w-full">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-oswald font-medium text-highlight">
            /PenineBot
          </h1>
        </div>

        <div className="flex-1 bg-box/5 backdrop-blur-sm rounded-2xl shadow-2xl border border-box/30 overflow-hidden flex flex-col max-h-[500px]">
          <ChatContainer messages={messages} isLoading={isLoading} />
          <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
        </div>

        {/* Debug Info (remove in production) */}
        {process.env.NODE_ENV === "development" && (
          <div className="mt-4 p-4 bg-gray-800 rounded text-xs text-gray-400 max-w-4xl w-full mx-auto">
            <strong>Debug Info:</strong>
            <div>API URL: {API_URL}</div>
            <div>Messages: {messages.length}</div>
            <div>Loading: {isLoading ? "Yes" : "No"}</div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function AskBotPage() {
  return (
    <Suspense
      fallback={
        <div
          className="min-h-screen flex items-center justify-center"
          style={{ color: "var(--text)" }}
        >
          Loading chat...
        </div>
      }
    >
      <AskBotPageContent />
    </Suspense>
  );
}
