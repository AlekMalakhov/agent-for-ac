"""Modifier Agent for applying targeted modifications to acceptance criteria."""

import logging

from src.agents.llm import get_llm_provider
from src.agents.prompts import format_prompt
from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def get_modification_type_description(intent: str) -> str:
    """
    Get human-readable description of modification type.

    Args:
        intent: The refiner intent type.

    Returns:
        str: Description of the modification type.
    """
    descriptions = {
        "modify_specific": "Modify specific criterion",
        "add_criterion": "Add new criterion",
        "remove_criterion": "Remove criterion",
    }
    return descriptions.get(intent, "Modify criteria")


def format_target_description(state: AgentState) -> str:
    """
    Format the target criterion description for the prompt.

    Args:
        state: Current workflow state.

    Returns:
        str: Description of what to target.
    """
    intent = state.get("refiner_intent", "")
    target = state.get("target_criterion")
    details = state.get("modification_details") or ""

    if intent == "modify_specific":
        if target and details:
            return f"Criterion #{target} - {details}"
        elif target:
            return f"Criterion #{target}"
        return f"Criteria matching: {details}"

    elif intent == "add_criterion":
        return f"Add new criterion about: {details}"

    elif intent == "remove_criterion":
        # IMPORTANT: Include details for better context
        if target and details:
            return f"Criterion #{target} - {details}"
        elif target:
            return f"Criterion #{target}"
        elif details:
            return f"Criteria matching: {details}"
        return "Remove the specified criterion"

    return details or "Apply the requested modification"


async def modifier_node(state: AgentState) -> dict:
    """
    Modifier Agent node for the workflow.

    Applies targeted modifications to existing acceptance criteria
    without full regeneration.

    Uses Claude 3.7 Sonnet for accurate modifications.

    Args:
        state: Current workflow state.

    Returns:
        dict: State updates including modified generated_ac.
    """
    intent = state.get("refiner_intent", "")
    current_ac = state.get("generated_ac", "")
    current_format = state.get("selected_format", "checklist")
    refinement_count = state.get("refinement_count", 0)

    logger.info(
        f"Modifier: applying {intent} modification, refinement count={refinement_count}"
    )

    if not current_ac:
        logger.warning("Modifier: no existing AC to modify")
        return {
            "error": "No acceptance criteria to modify",
            "current_agent": "modifier",
        }

    try:
        provider = get_llm_provider()
        model = provider.get_main_model()

        modification_type = get_modification_type_description(intent)
        target_description = format_target_description(state)

        # Ensure modification_details is never None
        modification_details = state.get("modification_details") or ""

        prompt = format_prompt(
            "modifier.txt",
            current_ac=current_ac,
            format=current_format,
            modification_type=modification_type,
            target_description=target_description,
            modification_details=modification_details,
        )

        # Debug logging
        logger.info(f"Modifier: sending prompt with modification_type='{modification_type}', target_description='{target_description}'")
        logger.debug(f"Modifier: full prompt:\n{prompt}")

        response = await model.ainvoke(prompt)
        modified_ac = response.content.strip()

        logger.info(f"Modifier: original AC length: {len(current_ac)}, modified AC length: {len(modified_ac)}")

        # Check if AC actually changed
        if modified_ac == current_ac:
            logger.warning("Modifier: AC content unchanged! LLM returned identical content.")

        logger.debug(f"Modifier: modified AC preview (first 500 chars):\n{modified_ac[:500]}")

        # Update chat history with success message
        chat_history = state.get("chat_history", []).copy()
        chat_history.append({
            "role": "assistant",
            "content": "I've updated the acceptance criteria based on your request."
        })

        return {
            "generated_ac": modified_ac,
            "refinement_count": refinement_count + 1,
            "chat_history": chat_history,
            "current_agent": "modifier",
            # Clear modification-specific fields
            "target_criterion": None,
            "modification_details": "",
        }

    except Exception as e:
        logger.error(f"Modifier error: {e}")
        return {
            "error": str(e),
            "current_agent": "modifier",
        }
