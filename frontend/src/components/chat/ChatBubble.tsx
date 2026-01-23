import { Message } from "@/types/chat";
import LoadingDots from "@/components/ui/LoadingDots";

interface ChatBubbleProps {
  message: Message;
  isLoading?: boolean;
}

export default function ChatBubble({ message, isLoading = false }: ChatBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-[70%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-highlight text-background font-inter"
            : "bg-box/20 text-text font-inter backdrop-blur-sm"
        }`}
      >
        {isLoading ? (
          <LoadingDots />
        ) : (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        )}
        
        <span className="text-xs opacity-60 mt-1 block">
          {message.timestamp.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
}
