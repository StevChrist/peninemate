"""
LLM Client for Qwen 2.5 via Ollama
Generates natural language answers for movie questions
"""

import logging
import requests
import json
from typing import Optional

logger = logging.getLogger(__name__)


class QwenClient:
    """Client for Qwen 2.5 3B Instruct model via Ollama"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:3b-instruct"
        self._check_model()
    
    def _check_model(self):
        """Check if model is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                if any(m['name'] == self.model for m in models):
                    logger.info(f"✅ {self.model} ready")
                    return
            logger.warning(f"⚠️ {self.model} not found. Install with: ollama pull {self.model}")
        except Exception as e:
            logger.error(f"❌ Ollama connection failed: {e}")
    
    def generate_answer(
        self,
        question: str,
        context: str = "",
        conversation_history: str = "",
        max_tokens: int = 500
    ) -> str:
        """
        Generate natural language answer using Qwen 2.5
        
        Args:
            question: User's question
            context: Movie information context
            conversation_history: Previous conversation messages
            max_tokens: Maximum response length
        
        Returns:
            Generated answer string
        """
        # Build prompt
        system_prompt = """You are PenineMate, a helpful movie recommendation assistant. 
Answer questions about movies based on the provided information.
Be concise, friendly, and informative.
If asked about cast, directors, or crew, list them clearly.
If the information is not available, say so politely."""
        
        # Build user prompt
        user_prompt = f"""Question: {question}

Movie Information:
{context}
"""
        
        if conversation_history:
            user_prompt = f"""Previous Conversation:
{conversation_history}

{user_prompt}"""
        
        # Call Ollama API
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": max_tokens,
                        "top_p": 0.9
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip()
                
                if not answer:
                    return "I couldn't generate an answer. Please try rephrasing your question."
                
                return answer
            else:
                logger.error(f"❌ Ollama API error: {response.status_code}")
                return "Sorry, I'm having trouble generating an answer right now."
                
        except requests.exceptions.Timeout:
            logger.error("❌ Ollama API timeout")
            return "The request took too long. Please try again."
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            return "Sorry, I encountered an error while generating the answer."


# Singleton instance
_llm_client = None


def get_llm_client() -> QwenClient:
    """Get singleton LLM client"""
    global _llm_client
    if _llm_client is None:
        _llm_client = QwenClient()
    return _llm_client
