import axios from 'axios';
import { QuestionRequest, QuestionResponse } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const askQuestion = async (question: string): Promise<QuestionResponse> => {
  const { data } = await api.post<QuestionResponse>('/qa', { question });
  return data;
};

export const searchMovies = async (query: string, limit = 5) => {
  const { data } = await api.get('/movies/search', {
    params: { q: query, limit },
  });
  return data;
};
