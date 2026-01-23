export interface Movie {
  tmdb_id: number;
  title: string;
  year: number;
  overview?: string;
  popularity?: number;
  box_office_worldwide?: number;
}

export interface QuestionRequest {
  question: string;
}

export interface QuestionResponse {
  answer: string;
  movies: Movie[];
  source: 'keyword' | 'semantic' | 'api' | 'director_search' | 'actor_search';
  confidence?: number;
}

export interface SearchParams {
  q: string;
  year?: number;
  limit?: number;
}
