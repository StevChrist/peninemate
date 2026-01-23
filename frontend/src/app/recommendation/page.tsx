"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import ResultModal from "@/components/recommendation/ResultModal";
import { RecommendationFilters, MovieResult } from "@/types/recommendation";

export default function RecommendationPage() {
  const [filters, setFilters] = useState<RecommendationFilters>({
    genres: [],
    mood: [],
    theme: [],
    storyline: [],
    year: [],
    duration: [],
    durationComparison: "exact",
  });

  const [result, setResult] = useState<MovieResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [excludedMovies, setExcludedMovies] = useState<string[]>([]);

  const handleInputChange = (field: keyof RecommendationFilters, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [field]: value.split(",").map((v) => v.trim()).filter(Boolean),
    }));
  };

  const handleSearch = async () => {
    setIsLoading(true);
    
    try {
      const response = await fetch("http://localhost:8000/api/v1/recommend", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...filters,
          exclude: excludedMovies,
        }),
      });

      const data = await response.json();
      
      const movieResult: MovieResult = {
        title: data.title || "Unknown Movie",
        genre: data.genre || "N/A",
        duration: data.duration || 0,
        cast: data.cast || [],
        rating: data.rating || 0,
        region: data.region || "N/A",
      };

      setResult(movieResult);
    } catch (error) {
      console.error("Error fetching recommendation:", error);
      alert("Failed to get recommendation. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchMore = () => {
    if (result) {
      setExcludedMovies((prev) => [...prev, result.title]);
      setResult(null);
      setTimeout(() => handleSearch(), 100);
    }
  };

  const handleCloseModal = () => {
    setResult(null);
  };

  const handleDurationComparisonChange = (value: "over" | "less" | "exact") => {
    setFilters((prev) => ({
      ...prev,
      durationComparison: value,
    }));
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="pt-24 pb-8 px-clear">
        <div className="text-center mb-8">
          <h1 className="text-5xl font-oswald font-medium text-highlight">
            /Recommendation Movie
          </h1>
        </div>

        <div className="max-w-3xl mx-auto space-y-6">
          {/* Movie Genres */}
          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-48">Movie Genres</label>
            <input
              type="text"
              placeholder="Action, Drama, Comedy, Horror, Romance, ..."
              className="flex-1 px-4 py-3 rounded-lg bg-box/60 text-background placeholder:text-background/60 font-inter focus:outline-none focus:ring-2 focus:ring-highlight"
              onChange={(e) => handleInputChange("genres", e.target.value)}
            />
          </div>

          {/* Mood */}
          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-48">Mood</label>
            <input
              type="text"
              placeholder="Relaxed, Sad, Tense, Happy, Thinking, ..."
              className="flex-1 px-4 py-3 rounded-lg bg-box/60 text-background placeholder:text-background/60 font-inter focus:outline-none focus:ring-2 focus:ring-highlight"
              onChange={(e) => handleInputChange("mood", e.target.value)}
            />
          </div>

          {/* Theme */}
          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-48">Theme</label>
            <input
              type="text"
              placeholder="Friendship, Revenge, Family, Survival, Time Travel, ..."
              className="flex-1 px-4 py-3 rounded-lg bg-box/60 text-background placeholder:text-background/60 font-inter focus:outline-none focus:ring-2 focus:ring-highlight"
              onChange={(e) => handleInputChange("theme", e.target.value)}
            />
          </div>

          {/* Storyline */}
          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-48">Storyline</label>
            <input
              type="text"
              placeholder="Slow burn, Fast-paced, Heavy plot twist, ..."
              className="flex-1 px-4 py-3 rounded-lg bg-box/60 text-background placeholder:text-background/60 font-inter focus:outline-none focus:ring-2 focus:ring-highlight"
              onChange={(e) => handleInputChange("storyline", e.target.value)}
            />
          </div>

          {/* Year */}
          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-48">Year</label>
            <input
              type="text"
              placeholder="1999, 2000, 2001, ..."
              className="flex-1 px-4 py-3 rounded-lg bg-box/60 text-background placeholder:text-background/60 font-inter focus:outline-none focus:ring-2 focus:ring-highlight"
              onChange={(e) => handleInputChange("year", e.target.value)}
            />
          </div>

          {/* Duration */}
          <div className="flex items-center gap-4">
            <label className="text-text font-inter text-lg w-48">Duration (minute)</label>
            <div className="flex-1 space-y-2">
              <input
                type="text"
                placeholder="170 minute, 120 minute, ..."
                className="w-full px-4 py-3 rounded-lg bg-box/60 text-background placeholder:text-background/60 font-inter focus:outline-none focus:ring-2 focus:ring-highlight"
                onChange={(e) => handleInputChange("duration", e.target.value)}
              />
              
              <div className="flex gap-6 text-text font-inter">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="durationComparison"
                    value="over"
                    checked={filters.durationComparison === "over"}
                    onChange={(e) => handleDurationComparisonChange(e.target.value as "over")}
                    className="w-4 h-4"
                  />
                  over duration
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="durationComparison"
                    value="less"
                    checked={filters.durationComparison === "less"}
                    onChange={(e) => handleDurationComparisonChange(e.target.value as "less")}
                    className="w-4 h-4"
                  />
                  less than duration
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="durationComparison"
                    value="exact"
                    checked={filters.durationComparison === "exact"}
                    onChange={(e) => handleDurationComparisonChange(e.target.value as "exact")}
                    className="w-4 h-4"
                  />
                  exactly the same
                </label>
              </div>
            </div>
          </div>

          {/* Search Button */}
          <div className="flex justify-center pt-4">
            <button
              onClick={handleSearch}
              disabled={isLoading}
              className="px-12 py-3 bg-box/80 text-background rounded-lg font-inter font-medium hover:bg-box transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Searching..." : "Search"}
            </button>
          </div>
        </div>

      </main>

      {result && (
        <ResultModal
          result={result}
          onClose={handleCloseModal}
          onSearchMore={handleSearchMore}
        />
      )}
    </div>
  );
}
