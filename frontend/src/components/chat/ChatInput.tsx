"use client";

import { useState, KeyboardEvent, FormEvent } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (message: string) => void | Promise<void>;
  isLoading?: boolean;
}

export default function ChatInput({ onSendMessage, isLoading = false }: ChatInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleSend = () => {
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue("");
    }
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    handleSend();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="px-6 py-4 border-t border-box/20">
      <div className="flex gap-2 items-center">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isLoading ? "Waiting for response..." : "Type your message..."}
          disabled={isLoading}
          className="flex-1 px-4 py-3 rounded-full bg-box/10 text-text placeholder:text-text/40 font-inter focus:outline-none focus:ring-2 focus:ring-highlight disabled:opacity-50 disabled:cursor-not-allowed"
        />
        
        <button
          type="submit"
          disabled={isLoading || !inputValue.trim()}
          className="p-3 rounded-full bg-highlight text-background hover:bg-highlight/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </form>
  );
}
