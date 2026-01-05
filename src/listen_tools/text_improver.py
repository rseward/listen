

import os
import json
import httpx
import any_llm
from .logger import setup_logger

# Set up logger
logger = setup_logger(__name__)


def gemini_available() -> bool:
    # Check if Gemini API is available
    try:
        from google import genai

        apikey = os.getenv("GEMINI_API_KEY", None)
        if apikey is None:
            logger.debug("Gemini not available: GEMINI_API_KEY not set")
            return False

        # Try to initialize the client to make sure it's fully functional
        client = genai.Client(api_key=apikey)
        logger.info("Gemini API is available and initialized")
        return True
    except ImportError as e:
        logger.debug(f"Gemini not available: Import error - {e}")
        return False
    except Exception as e:
        logger.warning(f"Gemini initialization failed: {e}")
        return False

def ollama_available() -> bool:
    # Check if Ollama API is available
    try:
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/api")

        # Try to make a simple request to check if Ollama is running
        logger.debug(f"Checking Ollama availability at {base_url}")
        response = httpx.get(f"{base_url}/tags", timeout=5)
        if response.status_code == 200:
            logger.info(f"Ollama API is available at {base_url}")
            return True
        else:
            logger.debug(f"Ollama returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.debug(f"Ollama not available: {e}")
        return False


class TextImprover(object):
    """
    Simple class to improve transcribed text using available AI services.
    """
    def __init__(self, prompt):
        logger.debug("Initializing TextImprover")
        self.model = None
        self.base_url = None
        self.prompt = prompt
        
        if gemini_available():
            self.model = "gemini:gemini-2.0-flash-exp"
            logger.info(f"Using Gemini model: {self.model}")
        elif ollama_available():
            self.model = "ollama:gemma3:latest"
            logger.info(f"Using Ollama model: {self.model}")
        else:
            logger.warning("No AI service available - will pass through text unchanged")

        #assert self.model is not None, "No AI service available in environment - check GEMINI_API_KEY or OPENAI_BASE_URL (and ensure Ollama is running at http://localhost:11434)"

        self.base_url = os.getenv("OPENAI_BASE_URL", None)
        if self.base_url:
            logger.debug(f"Using custom API base URL: {self.base_url}")



    def improve(self, text: str) -> str:
        # If no model is available, return original text
        if self.model is None:
            logger.debug("No model available, returning original text")
            return text

        logger.debug(f"Improving text with model {self.model} (text length: {len(text)} chars)")
        
        messages = [
            {"role": "system", "content": self.prompt},
            {"role": "user", "content": text}
        ]

        improved = text
        try:
            if self.base_url is not None:
                logger.debug(f"Calling API with custom base URL: {self.base_url}")
                response = any_llm.completion(
                    model=self.model,
                    messages=messages,
                    api_base=self.base_url
                )
            else:
                # Fallback to local model when base_url is not set
                logger.debug("Calling API with default configuration")
                response = any_llm.completion(
                    model=self.model,
                    messages=messages
                )

            if response is not None:
                improved = response.choices[0].message.content
                logger.debug(f"Text improvement successful (output length: {len(improved)} chars)")
            else:
                logger.warning("API returned None response, using original text")
        except Exception as e:
            logger.error(f"Error during text improvement: {e}", exc_info=True)
            logger.debug("Returning original text due to error")

        return improved
