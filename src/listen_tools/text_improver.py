

import os
import json
import httpx
import any_llm

def gemini_available() -> bool:
    # Check if Gemini API is available
    try:
        import google.generativeai as genai

        apikey = os.getenv("GEMINI_API_KEY", None)
        if apikey is None:
            return False

        # Try to initialize the API to make sure it's fully functional
        genai.configure(api_key=apikey)
        return True
    except (ImportError, Exception):
        return False

def ollama_available() -> bool:
    # Check if Ollama API is available
    try:
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/api")

        # Try to make a simple request to check if Ollama is running
        response = httpx.get(f"{base_url}/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


class TextImprover(object):
    """
    Simple class to improve transcribed text using available AI services.
    """
    def __init__(self, prompt):
        self.model = None
        self.base_url = None
        self.prompt = prompt
        
        if gemini_available():
            self.model = "google:models/gemini-2.0-flash-exp"
        elif ollama_available():
            self.model = "ollama:gemma3:latest"

        #assert self.model is not None, "No AI service available in environment - check GEMINI_API_KEY or OPENAI_BASE_URL (and ensure Ollama is running at http://localhost:11434)"

        self.base_url = os.getenv("OPENAI_BASE_URL", None)



    def improve(self, text: str) -> str:
        # If no model is available, return original text
        if self.model is None:
            return text

        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": text}
        ]

        improved = text
        if self.base_url is not None:
            response = any_llm.completion(
                model=self.model,
                messages=messages,
                api_base=self.base_url
            )
        else:
            # Fallback to local model when base_url is not set
            response = any_llm.completion(
                model=self.model,
                messages=messages
            )

        if response is not None:
            improved = response.choices[0].message.content

        return improved
