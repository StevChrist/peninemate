"""
LLM Client for OpenAI
Enhanced with:
- classify_query_enhanced() for detailed intent detection
- generate_answer() for natural language answer generation
"""

import logging
import os
import json
from typing import Optional, Dict, List
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI language models"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.model = model or os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"✅ OpenAI client initialized with model: {self.model}")
    
    
    def classify_query_enhanced(self, query: str, history: str = "") -> Dict:
        """Enhanced classification for intent detection and entity extraction"""
        
        prompt = f"""Analyze this movie question and extract intent:

Question: "{query}"
Conversation History: {history}

CLASSIFICATION RULES:

1. **GENERAL MOVIE MENTION** (just movie title, no specific question):
   - Examples: "Titanic", "Inception", "The Matrix"
   - Return: {{"query_type": "movie_info", "movie_title": "[Title]", "needs_context": false, "search_query": "[Title]", "genre": null, "specific_entity": null}}

2. **FRANCHISE/SERIES COUNT** (keywords: how many, berapa banyak, all movies, semua film):
   - Examples: "How many Deadpool films?", "All Avengers movies", "Berapa banyak film Spiderman"
   - Return: {{"query_type": "franchise", "movie_title": "[Franchise Name]", "needs_context": false, "search_query": "[Franchise]", "genre": null, "specific_entity": null}}

3. **PLOT/DESCRIPTION REQUEST** (keywords: description, plot, story, about, tentang, cerita, deskripsi):
   - Examples: "What is the description", "Tell me about the plot", "Cerita filmnya", "What is the film about"
   - Return: {{"query_type": "plot", "movie_title": "[extract from history]", "needs_context": true, "search_query": "[movie]", "genre": null, "specific_entity": null}}

4. **CAST REQUEST** (keywords: cast, actor, pemain, aktor, pemeran, starring):
   - Examples: "Who is the cast", "Siapa pemainnya", "Who stars in"
   - Return: {{"query_type": "cast", "movie_title": "[extract]", "needs_context": true, "search_query": "[movie]", "genre": null, "specific_entity": null}}

5. **DIRECTOR REQUEST** (keywords: director, sutradara, disutradarai, directed by):
   - Examples: "Who directed", "Siapa sutradaranya"
   - Return: {{"query_type": "director", "movie_title": "[extract]", "needs_context": true, "search_query": "[movie]", "genre": null, "specific_entity": null}}

6. **RECOMMENDATION REQUEST** (keywords: recommend, suggest, rekomendasikan, berikan, carikan):
   - Extract genre if mentioned (romantis→Romance, aksi→Action, komedi→Comedy, horor→Horror, thriller→Thriller)
   - Return: {{"query_type": "recommendation", "movie_title": null, "needs_context": false, "search_query": "[genre] movies", "genre": "[Genre]", "specific_entity": null}}

7. **YEAR REQUEST** (keywords: when, year, kapan, tahun, rilis, released):
   - Examples: "When was it made", "What year", "Kapan rilis"
   - Return: {{"query_type": "year", "movie_title": "[extract]", "needs_context": true, "search_query": "[movie]", "genre": null, "specific_entity": null}}

8. **LOCATION/WHERE REQUEST** (keywords: where, dimana, location, lokasi, filmed, shot, made at):
   - Examples: "Where was it made", "Where was it filmed", "Dimana filmnya dibuat"
   - Return: {{"query_type": "location", "movie_title": "[extract]", "needs_context": true, "search_query": "[movie]", "genre": null, "specific_entity": null}}

9. **RATING REQUEST** (keywords: rating, score, bagus, nilai, review):
   - Return: {{"query_type": "rating", "movie_title": "[extract]", "needs_context": true, "search_query": "[movie]", "genre": null, "specific_entity": null}}

**Important**: 
- For "how many X films" questions, use "franchise" type and extract franchise name
- For context questions (that film, this film, filmnya, the film, it), extract movie title from history
- "Where" questions are about FILMING LOCATION (not release year or country)
- If user just mentions a movie name without question, use "movie_info"
- Return ONLY valid JSON, no explanation

Return JSON:"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a movie query classifier. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean JSON if wrapped in markdown
            if result.startswith("```json"):
                result = result.replace("```json", "").replace("```", "").strip()
            if result.endswith("```"):
                result = result.replace("```", "").strip()
            
            classification = json.loads(result)
            
            logger.info(f"🧠 LLM Classification: query_type={classification.get('query_type')}, "
                       f"movie_title={classification.get('movie_title')}, "
                       f"genre={classification.get('genre')}")
            
            return classification
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}, raw response: {result[:200]}")
            return self._fallback_classification(query, history)
        except Exception as e:
            logger.error(f"❌ LLM classification error: {e}")
            return self._fallback_classification(query, history)
    
    
    def generate_answer(
        self, 
        question: str, 
        intent: str, 
        movie_data: Dict, 
        language: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Generate natural language answer using LLM
        
        Args:
            question: User's original question
            intent: Query intent (cast/director/plot/year/rating/location/recommendation)
            movie_data: Movie information dict
            language: 'id' or 'en'
            conversation_history: Recent conversation messages
        """
        
        # Build conversation context
        context = ""
        if conversation_history:
            for msg in conversation_history[-2:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:150]
                context += f"{role}: {content}\n"
        
        # Format movie data
        movie_str = json.dumps(movie_data, indent=2, ensure_ascii=False)
        
        lang_instruction = "Indonesian" if language == "id" else "English"
        
        # Build intent-specific instructions
        intent_instructions = {
            'movie_info': 'Provide: Title (Year) followed by full plot description (2-3 sentences)',
            'general_info': 'Provide: Title (Year) followed by full plot description (2-3 sentences)',
            'unknown': 'Provide: Title (Year) followed by full plot description (2-3 sentences)',
            'specific_movie_question': 'Provide: Title (Year) followed by full plot description (2-3 sentences)',
            'franchise': 'List ALL movies in the franchise found in movie_data. Format: "There are [X] [Franchise] movies: 1. [Title] ([Year]), 2. [Title] ([Year]), etc." Be comprehensive and list all available.',
            
            # ✅ UPDATED - Plot dengan title
            'plot': 'Format: "[Title] ([Year]). [Plot description in 2-3 sentences]". ALWAYS start with the movie title and year, then provide the full plot description.',
            
            'cast': 'List the main cast members (up to 8 actors). Format: "The cast of [Title] ([Year]) includes [names]."',
            'director': 'Mention the director(s) of the film. Format: "[Title] ([Year]) was directed by [names]."',
            'year': 'State the release year. Format: "[Title] was released in [year]."',
            'location': 'IMPORTANT: We do not have filming location data. Apologize politely and explain we only have plot, cast, director, year, and rating information available. Offer to provide one of those instead.',
            'rating': 'Provide the rating and brief quality assessment. Format: "[Title] ([Year]) has a rating of [X]/10."',
            'recommendation': 'Explain why this is a good recommendation (mention genre, plot, rating)'
        }
        
        instruction = intent_instructions.get(intent, intent_instructions['movie_info'])
        
        prompt = f"""Answer this movie question naturally in {lang_instruction}:

    **User Question**: "{question}"

    **Intent**: {intent}

    **What to provide**: {instruction}

    **Movie Data**:
    {movie_str}

    **Recent Conversation**:
    {context if context else "None"}

    **STRICT RULES**:
    1. For "movie_info" intent: MUST start with "Title (Year)" then give description
    2. For "plot" intent: MUST start with "Title (Year)." then give description (NOT just description alone)
    3. For "cast" intent: List all available cast members
    4. For "location" intent: Apologize and suggest other available information
    5. Answer directly and naturally (don't say "based on the data")
    6. Use conversational tone
    7. Keep answer concise but complete
    8. If data is missing, acknowledge it gracefully
    9. ALWAYS include the movie title when describing a movie

    **Language**: {lang_instruction}

    Generate answer:"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a helpful movie information assistant. Answer in {lang_instruction} only. Follow the intent instructions exactly. Always include movie title in your response."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=350,
                temperature=0.7
            )
            
            # ✅ Access response correctly
            answer = response.choices[0].message.content.strip()
            logger.info(f"✅ LLM Answer generated: {len(answer)} chars")
            return answer
            
        except Exception as e:
            logger.error(f"❌ LLM answer generation error: {e}")
            # Fallback to rule-based
            return self._generate_simple_answer(movie_data, intent, language)
    
    
    def _fallback_classification(self, question: str, history: str = "") -> Dict:
        """Fallback classification using heuristics"""
        
        question_lower = question.lower().strip()
        
        # Detect context need
        context_indicators = [
            "that film", "that movie", "this film", "this movie",
            "it ", "its ", "the cast", "the director", "the film",
            "film ini", "film itu", "filmnya"
        ]
        needs_context = any(ind in question_lower for ind in context_indicators)
        
        # Detect query type
        if any(w in question_lower for w in ["description", "plot", "story", "cerita", "sinopsis", "tentang", "about"]):
            query_type = "plot"
        elif any(w in question_lower for w in ["cast", "actor", "pemain", "aktor", "pemeran", "starring"]):
            query_type = "cast"
        elif any(w in question_lower for w in ["director", "sutradara", "disutradarai", "directed"]):
            query_type = "director"
        elif any(w in question_lower for w in ["when", "year", "kapan", "tahun", "rilis", "released"]):
            query_type = "year"
        elif any(w in question_lower for w in ["where", "dimana", "location", "lokasi", "filmed", "shot"]):
            query_type = "location"
        elif any(w in question_lower for w in ["rating", "score", "nilai", "bagus", "review"]):
            query_type = "rating"
        elif any(w in question_lower for w in ["recommend", "suggestion", "rekomendasikan", "berikan", "carikan"]):
            query_type = "recommendation"
        else:
            query_type = "movie_info"
        
        # Extract movie title (simple heuristic)
        import re
        words = question.split()
        capitalized = [w for w in words if w and len(w) > 2 and w.isupper() and w not in ["I", "The", "A", "Who", "What", "When", "Where"]]
        movie_title = " ".join(capitalized) if capitalized else None
        
        logger.info(f"⚠️ Using fallback classification: {query_type}")
        
        return {
            "query_type": query_type,
            "movie_title": movie_title,
            "needs_context": needs_context,
            "search_query": movie_title or question,
            "genre": None,
            "specific_entity": None
        }
    
    
    def _generate_simple_answer(self, movie_data: Dict, intent: str, language: str) -> str:
        """Simple rule-based answer as final fallback"""
        
        title = movie_data.get('title', 'Unknown')
        year = movie_data.get('year', '')
        year_str = f" ({year})" if year else ""
        overview = movie_data.get('overview', '')
        cast = movie_data.get('cast', [])
        directors = movie_data.get('directors', [])
        rating = movie_data.get('rating', 0)
        
        if language == "id":
            # Indonesian responses
            if intent == "location":
                return f"Maaf, saya tidak memiliki informasi tentang lokasi pengambilan gambar untuk film {title}{year_str}. Saya dapat memberikan informasi tentang sinopsis, pemain, sutradara, tahun rilis, atau rating film. Apakah Anda ingin mengetahui salah satunya?"
            elif intent == "plot":
                if overview:
                    return f"{title}{year_str}. {overview}"  # ← Add title
                else:
                    return f"Maaf, saya tidak memiliki deskripsi untuk {title}{year_str}." if language == "id" else f"I don't have a description for {title}{year_str}."
            elif intent == "cast":
                if cast:
                    return f"Pemain dalam film {title}{year_str} termasuk {', '.join(cast[:5])}."
                return f"Informasi pemain untuk {title}{year_str} tidak tersedia."
            elif intent == "director":
                if directors:
                    return f"Film {title}{year_str} disutradarai oleh {', '.join(directors)}."
                return f"Informasi sutradara untuk {title}{year_str} tidak tersedia."
            elif intent == "year":
                return f"Film {title} dirilis pada tahun {year}." if year else f"Informasi tahun untuk {title} tidak tersedia."
            elif intent == "rating":
                return f"Film {title}{year_str} memiliki rating {rating}/10." if rating > 0 else f"Informasi rating untuk {title}{year_str} tidak tersedia."
            else:
                # movie_info
                if overview:
                    return f"{title}{year_str}. {overview}"
                return f"{title}{year_str}"
        else:
            # English responses
            if intent == "location":
                return f"I'm sorry, I don't have information about where {title}{year_str} was filmed. However, I can provide information about the plot, cast, director, release year, or rating. Would you like to know about any of these?"
            elif intent == "plot":
                return overview if overview else f"Description for {title}{year_str} is not available."
            elif intent == "cast":
                if cast:
                    return f"The cast of {title}{year_str} includes {', '.join(cast[:5])}."
                return f"Cast information for {title}{year_str} is not available."
            elif intent == "director":
                if directors:
                    return f"{title}{year_str} was directed by {', '.join(directors)}."
                return f"Director information for {title}{year_str} is not available."
            elif intent == "year":
                return f"{title} was released in {year}." if year else f"Year information for {title} is not available."
            elif intent == "rating":
                return f"{title}{year_str} has a rating of {rating}/10." if rating > 0 else f"Rating information for {title}{year_str} is not available."
            else:
                # movie_info
                if overview:
                    return f"{title}{year_str}. {overview}"
                return f"{title}{year_str}"


# Singleton instance
_llm_client = None

def get_llm_client() -> OpenAIClient:
    """Get singleton LLM client"""
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAIClient()
    return _llm_client
