#!/usr/bin/env python3
"""
Improve transcribed text using AI models.

This script takes transcribed text as input and uses AI models (Gemini or Ollama)
to improve grammar, punctuation, and clarity while preserving the original meaning.
"""

import sys
import click
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


@click.command()
@click.argument('text', required=False)
@click.option('--prompt', '-p',
              default=DEFAULT_PROMPT,
              help='Custom prompt for the AI model')
@click.option('--raw', '-r', is_flag=True,
              help='Output raw text without "Improved:" prefix')
@click.option('--stdin', '-s', is_flag=True,
              help='Force reading from stdin even if text argument is provided')
@click.version_option(version='0.1.0', prog_name='improve')
def main(text, prompt, raw, stdin):
    """
    Improve transcribed text using AI models (Gemini or Ollama).

    Reads text from stdin or as a command-line argument and uses AI to fix
    grammar, punctuation, and clarity while preserving the original meaning.

    Examples:

        \b
        # From stdin
        echo "this needs improvement" | improve

        \b
        # From argument
        improve "um this is like a test you know"

        \b
        # Pipe from listen
        listen | improve

        \b
        # With custom prompt
        improve "text" --prompt "Make this more formal"

        \b
        # Raw output (no prefix)
        improve "text" --raw

    AI Service Priority:

        \b
        1. Gemini (if GEMINI_API_KEY environment variable is set)
        2. Ollama (if running locally at http://localhost:11434)
        3. Pass-through (returns original text if no service available)

    Environment Variables:

        \b
        GEMINI_API_KEY       - API key for Google Gemini
        OPENAI_BASE_URL      - Custom Ollama URL (default: http://localhost:11434/api)
    """
    # Determine input source
    if stdin or (text is None and not sys.stdin.isatty()):
        # Read from stdin
        transcribed_text = sys.stdin.read().strip()
    elif text:
        # Use command-line argument
        transcribed_text = text
    else:
        # No input provided
        click.echo("Error: No text provided. Use --help for usage information.", err=True)
        sys.exit(1)

    if not transcribed_text:
        click.echo("Error: Empty text provided.", err=True)
        sys.exit(1)

    # Improve the text
    improved_text = improve_text(transcribed_text, prompt)

    # Output the improved text
    if raw:
        click.echo(improved_text)
    else:
        click.echo(f"{improved_text}")


if __name__ == "__main__":
    main()
