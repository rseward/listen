#!/usr/bin/env python3
"""
Improve transcribed text using AI models.

This script takes transcribed text as input and uses AI models (Gemini or Ollama)
to improve grammar, punctuation, and clarity while preserving the original meaning.
"""

import sys
from .text_improver import TextImprover


DEFAULT_PROMPT = """
# Context
 You are an agent that improves transcribed text by correcting grammar, punctuation, and clarity while preserving the original meaning.

# Instructions
- Fix grammar and punctuation errors
- Improve sentence structure and flow
- Maintain the original meaning and intent
- Keep it concise and readable
- Return only the improved text

# Input Format
The transcribed text will be provided as a string.

# Output Format
Return only the improved, cleaned-up version of the transcribed text.
"""


def improve_text(text: str, prompt: str = DEFAULT_PROMPT) -> str:
    """
    Improve the given text using AI.

    Args:
        text: The text to improve
        prompt: The system prompt for the AI model

    Returns:
        The improved text
    """
    improver = TextImprover(prompt)
    return improver.improve(text)


def main():
    """Main entry point for the improve command."""
    # Read from text from standard input or command line arguments
    if len(sys.argv) > 1:
        transcribed_text = sys.argv[1]
    else:
        transcribed_text = sys.stdin.read().strip()

    improved_text = improve_text(transcribed_text)

    # Output the improved text
    print(f"Improved: {improved_text}")


if __name__ == "__main__":
    main()
