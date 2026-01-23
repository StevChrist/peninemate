"use client";

import { useRouter } from "next/navigation";
import { MovieResult } from "@/types/recommendation";
import { X, ArrowLeft } from "lucide-react";

interface ResultModalProps {
  result: MovieResult | null;
  onClose: () => void;
  onSearchMore: () => void;
}

export default function ResultModal({ result, onClose, onSearchMore }: ResultModalProps) {
  const router = useRouter();

  if (!result) return null;

  const handleWatchMovie = () => {
    const searchQuery = encodeURIComponent(`${result.title} watch`);
    window.open(`https://www.google.com/search?q=${searchQuery}`, "_blank");
  };

  const handleAskBot = () => {
    // Navigate to Ask Bot with movie title context
    router.push(`/ask?q=${encodeURIComponent(`Tell me about ${result.title}`)}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-clear">
      {/* Backdrop blur */}
      <div 
        className="absolute inset-0 bg-background/80 backdrop-blur-md"
        onClick={onClose}
      />

      {/* Modal content */}
      <div className="relative bg-box/40 backdrop-blur-xl border-2 border-box rounded-3xl w-full max-w-3xl p-8 shadow-2xl">
        {/* Back button */}
        <button
          onClick={onClose}
          className="absolute top-6 left-6 p-2 rounded-full bg-highlight/20 hover:bg-highlight/30 transition-colors"
        >
          <ArrowLeft className="w-6 h-6 text-highlight" />
        </button>

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-6 right-6 p-2 rounded-full hover:bg-text/10 transition-colors"
        >
          <X className="w-6 h-6 text-text" />
        </button>

        {/* Title */}
        <h2 className="text-4xl font-oswald text-highlight text-center mb-8">
          /Result
        </h2>

        {/* Movie Details */}
        <div className="space-y-4 mb-8">
          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-32">Title</label>
            <div className="flex-1 bg-box/60 rounded-lg px-4 py-3 text-background/80 font-inter">
              {result.title}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-32">Genre</label>
            <div className="flex-1 bg-box/60 rounded-lg px-4 py-3 text-background/80 font-inter">
              {result.genre}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-32">Duration</label>
            <div className="flex-1 bg-box/60 rounded-lg px-4 py-3 text-background/80 font-inter">
              {result.duration} minutes
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-32">Cast</label>
            <div className="flex-1 bg-box/60 rounded-lg px-4 py-3 text-background/80 font-inter">
              {result.cast.join(", ")}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-32">Rating</label>
            <div className="flex-1 bg-box/60 rounded-lg px-4 py-3 text-background/80 font-inter">
              ⭐ {result.rating}/10
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-32">Region</label>
            <div className="flex-1 bg-box/60 rounded-lg px-4 py-3 text-background/80 font-inter">
              {result.region}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center gap-4">
          <button
            onClick={handleWatchMovie}
            className="px-8 py-3 bg-background text-text rounded-lg font-inter hover:bg-background/80 transition-colors"
          >
            Movie
          </button>
          
          <button
            onClick={handleAskBot}
            className="px-8 py-3 bg-background text-text rounded-lg font-inter hover:bg-background/80 transition-colors"
          >
            Ask Bot
          </button>
          
          <button
            onClick={onSearchMore}
            className="px-8 py-3 bg-background text-text rounded-lg font-inter hover:bg-background/80 transition-colors"
          >
            Search More
          </button>
        </div>
      </div>
    </div>
  );
}
