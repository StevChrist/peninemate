export default function LoadingDots() {
  return (
    <div className="flex gap-1 items-center py-3 px-4">
      <div className="w-2 h-2 bg-text/60 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
      <div className="w-2 h-2 bg-text/60 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
      <div className="w-2 h-2 bg-text/60 rounded-full animate-bounce"></div>
    </div>
  );
}
