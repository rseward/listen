#!/usr/bin/env python3
"""
Improve transcribed text using AI models.

This script takes transcribed text as input and uses AI models (Gemini or Ollama)
to improve grammar, punctuation, and clarity while preserving the original meaning.
"""

import sys
import click
from .text_improver import TextImprover
from .logger import setup_logger

# Set up logger
logger = setup_logger(__name__)


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
    try:
        logger.debug(f"Improving text (length: {len(text)} chars)")
        improver = TextImprover(prompt)
        result = improver.improve(text)
        logger.info("Text improvement completed successfully")
        return result
    except Exception as e:
        logger.error(f"Failed to improve text: {e}", exc_info=True)
        raise


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
    logger.debug("Starting improve command")
    
    # Determine input source
    if stdin or (text is None and not sys.stdin.isatty()):
        # Read from stdin
        logger.debug("Reading text from stdin")
        transcribed_text = sys.stdin.read().strip()
    elif text:
        # Use command-line argument
        logger.debug("Using text from command-line argument")
        transcribed_text = text
    else:
        # No input provided
        logger.error("No text provided")
        click.echo("Error: No text provided. Use --help for usage information.", err=True)
        sys.exit(1)

    if not transcribed_text:
        logger.error("Empty text provided")
        click.echo("Error: Empty text provided.", err=True)
        sys.exit(1)

    # Improve the text
    display_text = transcribed_text[:50] + ("..." if len(transcribed_text) > 50 else "")
    click.echo(f"Improving text... {display_text}", err=True)
    
    try:
        improved_text = improve_text(transcribed_text, prompt)
    except Exception as e:
        logger.error(f"Text improvement failed: {e}", exc_info=True)
        click.echo(f"Error: Text improvement failed: {e}", err=True)
        sys.exit(1)

    # Output the improved text
    if raw:
        click.echo(improved_text)
    else:
        click.echo(f"{improved_text}")


if __name__ == "__main__":
    main()
