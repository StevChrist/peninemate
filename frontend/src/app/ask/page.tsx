"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import Header from "@/components/layout/Header";
import ChatContainer from "@/components/chat/ChatContainer";
import ChatInput from "@/components/chat/ChatInput";
import { Message } from "@/types/chat";

export default function AskBotPage() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const initialQueryProcessed = useRef(false); // ✅ Guard untuk prevent double execution

  // Check if there's a query from home page search
  useEffect(() => {
    const query = searchParams.get("q");
    if (query && !initialQueryProcessed.current) {
      initialQueryProcessed.current = true;
      handleSendMessage(query);
    }
  }, [searchParams]); // ✅ Proper dependency

  const handleSendMessage = async (content: string) => {
    if (isLoading || !content.trim()) return; // ✅ Tambah validation

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: content.trim(),
      timestamp: new Date(),
    };

    // ✅ Update messages FIRST, sehingga bisa diambil untuk history
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // ✅ Prepare conversation history AFTER user message added
      // Use functional update to get latest state
      const conversationHistory = [...messages, userMessage].slice(-10).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Call backend API with conversation history
      const response = await fetch("http://localhost:8000/api/v1/qa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: content.trim(),
          conversation_history: conversationHistory
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Add AI response
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer || "Sorry, I couldn't find an answer.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMessage]);

    } catch (error) {
      console.error("Error fetching answer:", error);
      // Add error message
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
      {/* Header */}
      <Header />

      {/* Main Content - Full width with proper spacing */}
      <main className="flex-1 flex flex-col justify-center clear-space py-8 max-w-7xl mx-auto w-full">
        {/* Page Title - Only title, no subtitle */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-oswald font-medium text-highlight">
            /PenineBot
          </h1>
        </div>

        {/* Chat Box - Wider box */}
        <div className="flex-1 bg-box/5 backdrop-blur-sm rounded-2xl shadow-2xl border border-box/30 overflow-hidden flex flex-col max-h-[500px]">
          <ChatContainer messages={messages} isLoading={isLoading} />
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
        </div>
      </main>

      {/* No Footer */}
    </div>
  );
}
