"use client";

import { useState, useEffect, useRef, Suspense } from "react";
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

  useEffect(() => {
    const query = searchParams.get("q");
    if (query && !initialQueryProcessed.current) {
      initialQueryProcessed.current = true;
      handleSendMessage(query);
    }
  }, [searchParams]);

  const handleSendMessage = async (content: string) => {
    if (isLoading || !content.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const conversationHistory = [...messages, userMessage].slice(-10).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      console.log(`🔗 Calling API: ${API_URL}/api/v1/qa`); // ✅ Debug log

      // ✅ Use dynamic API_URL
      const response = await fetch(`${API_URL}/api/v1/qa`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: content.trim(),
          conversation_history: conversationHistory
        }),
      });

      console.log(`✅ Response status: ${response.status}`); // ✅ Debug log

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("📦 Response data:", data); // ✅ Debug log

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer || "Sorry, I couldn't find an answer.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMessage]);

    } catch (error) {
      console.error("❌ Error fetching answer:", error); // ✅ Better error log
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, there was an error processing your request. Please try again.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  
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
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
        </div>
      </main>
    </div>
  );
}

export default function AskBotPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-highlight mx-auto mb-4"></div>
          <p className="text-text-secondary">Loading chat...</p>
        </div>
      </div>
    }>
      <AskBotPageContent />
    </Suspense>
  );
}
