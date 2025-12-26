"""Generator Agent for creating acceptance criteria."""

import logging

from src.agents.llm import get_llm_provider
from src.agents.prompts import format_prompt
from src.agents.state import AgentState

logger = logging.getLogger(__name__)

# Maximum generation attempts before giving up
MAX_GENERATION_ATTEMPTS = 2


def format_gathered_info(gathered_information: list[dict]) -> str:
    """
    Format gathered Q&A pairs for prompt inclusion.

    Args:
        gathered_information: List of Q&A dicts.

    Returns:
        str: Formatted string of Q&A pairs.
    """
    if not gathered_information:
        return "No additional context available."

    formatted = []
    for i, qa in enumerate(gathered_information, 1):
        formatted.append(f"Q{i}: {qa.get('question', 'N/A')}")
        formatted.append(f"A{i}: {qa.get('answer', 'N/A')}")
        formatted.append("")

    return "\n".join(formatted)


def format_previous_feedback(evaluator_feedback: str | None) -> str:
    """
    Format evaluator feedback for retry prompt.

    Args:
        evaluator_feedback: Feedback from previous evaluation.

    Returns:
        str: Formatted feedback section.
    """
    if not evaluator_feedback:
        return ""

    return f"""
IMPORTANT: This is a retry based on previous evaluation feedback.
Please address the following issues:

{evaluator_feedback}

Focus on improving the specific areas mentioned above.
"""


async def generator_node(state: AgentState) -> dict:
    """
    Generator Agent node for the workflow.

    Generates acceptance criteria based on ticket information
    and gathered context.

    Uses Claude 3.7 Sonnet for high-quality output.

    Args:
        state: Current workflow state.

    Returns:
        dict: State updates including generated_ac.
    """
    generation_attempts = state.get("generation_attempts", 0)
    selected_format = state.get("selected_format") or "checklist"

    logger.info(
        f"Generator: attempt {generation_attempts + 1}, format={selected_format}"
    )

    try:
        provider = get_llm_provider()
        model = provider.get_main_model()

        gathered_info_str = format_gathered_info(state.get("gathered_information", []))
        previous_feedback = format_previous_feedback(state.get("evaluator_feedback"))

        prompt = format_prompt(
            "generator.txt",
            title=state["ticket_title"],
            description=state["ticket_description"],
            gathered_info=gathered_info_str,
            format=selected_format,
            previous_feedback=previous_feedback,
        )

        response = await model.ainvoke(prompt)

        logger.info(f"Generator produced AC with length: {len(response.content)}")

        return {
            "generated_ac": response.content,
            "generation_attempts": generation_attempts + 1,
            "current_agent": "generator",
        }

    except Exception as e:
        logger.error(f"Generator error: {e}")
        return {
            "error": str(e),
            "generation_attempts": generation_attempts + 1,
            "current_agent": "generator",
        }
