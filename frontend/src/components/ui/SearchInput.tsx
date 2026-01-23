"use client";

import { useState } from "react";
import { Search, ArrowRight } from "lucide-react";

interface SearchInputProps {
  placeholder?: string;
  onSubmit?: (query: string) => void;
}

export default function SearchInput({ 
  placeholder = "the film whose ship sank",
  onSubmit 
}: SearchInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && onSubmit) {
      onSubmit(query);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl">
      <div className="relative">
        {/* Search Icon */}
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-background w-5 h-5" />
        
        {/* Input */}
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="w-full pl-12 pr-14 py-4 rounded-full bg-box text-background placeholder:text-background/60 font-inter focus:outline-none focus:ring-2 focus:ring-highlight transition-all"
        />
        
        {/* Submit Button */}
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-background text-text p-2 rounded-full hover:bg-highlight hover:text-background transition-colors"
        >
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </form>
  );
}
