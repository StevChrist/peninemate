export interface RecommendationFilters {
  genres: string[];
  mood: string[];
  theme: string[];
  storyline: string[];
  year: string[];
  duration: string[];
  durationComparison: "over" | "less" | "exact";
}

export interface MovieResult {
  title: string;
  genre: string;
  duration: number;
  cast: string[];
  rating: number;
  region: string;
  overview?: string;
}
