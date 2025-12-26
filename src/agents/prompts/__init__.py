"""Prompt loading utilities for agents."""

from pathlib import Path

# Directory containing prompt template files
PROMPTS_DIR = Path(__file__).parent


def load_prompt(prompt_name: str) -> str:
    """
    Load a prompt template from file.

    Args:
        prompt_name: Name of the prompt file (e.g., "orchestrator.txt")

    Returns:
        str: The prompt template content.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
    """
    prompt_path = PROMPTS_DIR / prompt_name

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8")


def format_prompt(prompt_name: str, **kwargs: str) -> str:
    """
    Load and format a prompt template with provided values.

    Args:
        prompt_name: Name of the prompt file (e.g., "orchestrator.txt")
        **kwargs: Key-value pairs to format the template.

    Returns:
        str: The formatted prompt.

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
        KeyError: If a required placeholder is missing from kwargs.
    """
    template = load_prompt(prompt_name)
    return template.format(**kwargs)
