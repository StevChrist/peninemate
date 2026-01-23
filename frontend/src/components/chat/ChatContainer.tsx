"use client";

import { useEffect, useRef } from "react";
import { Message } from "@/types/chat";
import ChatBubble from "./ChatBubble";

interface ChatContainerProps {
  messages: Message[];
  isLoading: boolean;
}

export default function ChatContainer({ messages, isLoading }: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new message arrives
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-text/40 font-inter">
          <p>Start a conversation by asking about a movie...</p>
        </div>
      ) : (
        <>
          {messages.map((message) => (
            <ChatBubble key={message.id} message={message} />
          ))}
          
          {/* Loading bubble when AI is responding */}
          {isLoading && (
            <ChatBubble
              message={{
                id: "loading",
                role: "assistant",
                content: "",
                timestamp: new Date(),
              }}
              isLoading={true}
            />
          )}
        </>
      )}
      
      <div ref={bottomRef} />
    </div>
  );
}
