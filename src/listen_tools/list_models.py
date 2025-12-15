#!/usr/bin/env python3
"""
List available AI models from configured providers.

This utility queries the configured AI providers (Gemini, Ollama) and lists
the available models with their any-llm-sdk format strings.
"""

import os
import sys
import click
import httpx
from typing import List, Dict, Optional


def list_gemini_models() -> Optional[List[Dict[str, str]]]:
    """
    List available Gemini models.

    Returns:
        List of model info dicts, or None if not available
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        # List models
        models = []
        model_list = client.models.list()

        for model in model_list:
            # Get model name - the new SDK returns model IDs directly
            model_id = model.name if hasattr(model, 'name') else str(model)
            # Remove 'models/' prefix if present
            if model_id.startswith('models/'):
                model_id = model_id.replace('models/', '')

            # Format for any-llm-sdk (uses 'gemini' prefix)
            any_llm_format = f"gemini:{model_id}"

            # Get display name and description
            display_name = model.display_name if hasattr(model, 'display_name') else model_id
            description = model.description if hasattr(model, 'description') else ''

            models.append({
                'provider': 'Gemini',
                'name': display_name,
                'id': model_id,
                'any_llm_string': any_llm_format,
                'description': description
            })

        return models
    except ImportError:
        click.echo("Warning: google-genai not installed", err=True)
        return None
    except Exception as e:
        click.echo(f"Error listing Gemini models: {e}", err=True)
        return None


def list_ollama_models() -> Optional[List[Dict[str, str]]]:
    """
    List available Ollama models.

    Returns:
        List of model info dicts, or None if not available
    """
    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/api")

    try:
        response = httpx.get(f"{base_url}/tags", timeout=5)
        if response.status_code != 200:
            return None

        data = response.json()
        models = []

        for model in data.get('models', []):
            model_name = model.get('name', '')
            # Format for any-llm-sdk
            any_llm_format = f"ollama:{model_name}"

            models.append({
                'provider': 'Ollama',
                'name': model_name,
                'id': model_name,
                'any_llm_string': any_llm_format,
                'size': model.get('size', 0),
                'modified': model.get('modified_at', '')
            })

        return models
    except Exception as e:
        click.echo(f"Error listing Ollama models: {e}", err=True)
        return None


@click.command()
@click.option('--provider', '-p',
              type=click.Choice(['gemini', 'ollama', 'all'], case_sensitive=False),
              default='all',
              help='Which provider to list models from')
@click.option('--format', '-f',
              type=click.Choice(['table', 'list', 'json'], case_sensitive=False),
              default='table',
              help='Output format')
@click.option('--any-llm-only', '-a', is_flag=True,
              help='Show only the any-llm-sdk format strings')
def main(provider, format, any_llm_only):
    """
    List available AI models from configured providers.

    This utility queries Gemini and/or Ollama to show which models are available
    and their corresponding any-llm-sdk format strings.

    Examples:

        \b
        # List all available models
        list-models

        \b
        # List only Gemini models
        list-models --provider gemini

        \b
        # List only Ollama models
        list-models --provider ollama

        \b
        # Show only any-llm-sdk strings
        list-models --any-llm-only

        \b
        # JSON output
        list-models --format json

    Environment Variables:

        \b
        GEMINI_API_KEY       - API key for Google Gemini
        OPENAI_BASE_URL      - Custom Ollama URL (default: http://localhost:11434/api)
    """
    all_models = []

    # Collect models from requested providers
    if provider in ['gemini', 'all']:
        gemini_models = list_gemini_models()
        if gemini_models:
            all_models.extend(gemini_models)
        elif provider == 'gemini':
            click.echo("Error: Gemini API not available. Set GEMINI_API_KEY environment variable.", err=True)
            sys.exit(1)

    if provider in ['ollama', 'all']:
        ollama_models = list_ollama_models()
        if ollama_models:
            all_models.extend(ollama_models)
        elif provider == 'ollama':
            click.echo("Error: Ollama not available. Make sure it's running at the configured URL.", err=True)
            sys.exit(1)

    if not all_models:
        click.echo("No models available. Configure at least one provider:", err=True)
        click.echo("  - Set GEMINI_API_KEY for Gemini", err=True)
        click.echo("  - Start Ollama for local models", err=True)
        sys.exit(1)

    # Output based on format
    if any_llm_only:
        # Just list the any-llm-sdk strings
        for model in all_models:
            click.echo(model['any_llm_string'])
    elif format == 'json':
        import json
        click.echo(json.dumps(all_models, indent=2))
    elif format == 'list':
        for model in all_models:
            click.echo(f"{model['provider']}: {model['name']} ({model['any_llm_string']})")
    else:  # table format
        # Print header
        click.echo("\nAvailable AI Models:")
        click.echo("=" * 80)

        current_provider = None
        for model in sorted(all_models, key=lambda x: (x['provider'], x['name'])):
            if current_provider != model['provider']:
                current_provider = model['provider']
                click.echo(f"\n{current_provider}:")
                click.echo("-" * 80)

            click.echo(f"  Model: {model['name']}")
            click.echo(f"    any-llm-sdk: {model['any_llm_string']}")

            if 'description' in model and model['description']:
                # Truncate long descriptions
                desc = model['description']
                if len(desc) > 60:
                    desc = desc[:57] + "..."
                click.echo(f"    Description: {desc}")

            if 'size' in model:
                # Convert size to human-readable format
                size_bytes = model['size']
                if size_bytes > 1024**3:
                    size_str = f"{size_bytes / (1024**3):.1f} GB"
                elif size_bytes > 1024**2:
                    size_str = f"{size_bytes / (1024**2):.1f} MB"
                else:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                click.echo(f"    Size: {size_str}")

            click.echo()

        click.echo("=" * 80)
        click.echo(f"Total: {len(all_models)} models available\n")


if __name__ == "__main__":
    main()
