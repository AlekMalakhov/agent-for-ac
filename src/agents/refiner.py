"""Refiner Agent for classifying user intent in chat refinement mode."""

import json
import logging

from src.agents.llm import get_llm_provider
from src.agents.prompts import format_prompt
from src.agents.state import AgentState, RefinerResponse

logger = logging.getLogger(__name__)

# Maximum refinement iterations before suggesting approval
MAX_REFINEMENTS = 10


def format_chat_history(chat_history: list[dict]) -> str:
    """
    Format chat history for prompt inclusion.

    Args:
        chat_history: List of chat message dicts with role and content.

    Returns:
        str: Formatted chat history string.
    """
    if not chat_history:
        return "No previous conversation."

    formatted = []
    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prefix = "User" if role == "user" else "Assistant"
        formatted.append(f"{prefix}: {content}")

    return "\n".join(formatted)


async def refiner_node(state: AgentState) -> dict:
    """
    Refiner Agent node for the workflow.

    Classifies user intent from natural language messages
    to determine what refinement action to take.

    Uses Claude 3.7 Sonnet for accurate intent classification.

    Args:
        state: Current workflow state.

    Returns:
        dict: State updates including refiner_intent and related fields.
    """
    pending_message = state.get("pending_user_message", "")
    refinement_count = state.get("refinement_count", 0)

    logger.info(
        f"Refiner: processing message, refinement count={refinement_count}"
    )

    if not pending_message:
        logger.warning("Refiner: no pending message to process")
        return {
            "refiner_intent": "clarification",
            "clarification_question": "I didn't receive a message. How would you like to modify the acceptance criteria?",
            "current_agent": "refiner",
        }

    try:
        provider = get_llm_provider()
        model = provider.get_main_model()

        chat_history_str = format_chat_history(state.get("chat_history", []))
        current_ac = state.get("generated_ac", "")
        current_format = state.get("selected_format", "checklist")

        prompt = format_prompt(
            "refiner.txt",
            current_ac=current_ac,
            current_format=current_format,
            chat_history=chat_history_str,
            user_message=pending_message,
        )

        # Debug logging
        logger.info(f"Refiner: analyzing user message: '{pending_message}'")
        logger.debug(f"Refiner: full prompt:\n{prompt}")

        response = await model.ainvoke(prompt)
        response_text = response.content.strip()

        logger.debug(f"Refiner: LLM response:\n{response_text}")

        # Parse JSON response
        try:
            # Handle markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                response_text = "\n".join(json_lines)

            parsed = json.loads(response_text)
            refiner_response = RefinerResponse(**parsed)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Refiner: failed to parse response: {e}")
            logger.debug(f"Refiner: raw response text: {response_text}")
            # Default to clarification if parsing fails
            return {
                "refiner_intent": "clarification",
                "clarification_question": "I'm not sure what you'd like to change. Could you please be more specific?",
                "current_agent": "refiner",
            }

        logger.info(
            f"Refiner: classified intent='{refiner_response.intent}', "
            f"target_criterion={refiner_response.target_criterion}, "
            f"modification_details='{refiner_response.modification_details}'"
        )

        # Update chat history with assistant response
        chat_history = state.get("chat_history", []).copy()

        # Build state updates based on intent
        state_updates = {
            "refiner_intent": refiner_response.intent,
            "current_agent": "refiner",
            "pending_user_message": None,  # Clear processed message
        }

        if refiner_response.intent == "modify_specific":
            state_updates["target_criterion"] = refiner_response.target_criterion
            state_updates["modification_details"] = refiner_response.modification_details
            chat_history.append({
                "role": "assistant",
                "content": f"Modifying criterion #{refiner_response.target_criterion}..."
            })

        elif refiner_response.intent == "add_criterion":
            state_updates["modification_details"] = refiner_response.modification_details
            chat_history.append({
                "role": "assistant",
                "content": "Adding a new criterion..."
            })

        elif refiner_response.intent == "remove_criterion":
            state_updates["target_criterion"] = refiner_response.target_criterion
            chat_history.append({
                "role": "assistant",
                "content": f"Removing criterion #{refiner_response.target_criterion}..."
            })

        elif refiner_response.intent == "change_format":
            state_updates["selected_format"] = refiner_response.new_format
            chat_history.append({
                "role": "assistant",
                "content": f"Converting to {refiner_response.new_format} format..."
            })

        elif refiner_response.intent == "regenerate":
            state_updates["regeneration_context"] = refiner_response.regeneration_context
            state_updates["generation_attempts"] = 0  # Reset attempts for regeneration
            chat_history.append({
                "role": "assistant",
                "content": "Regenerating acceptance criteria with your feedback..."
            })

        elif refiner_response.intent == "clarification":
            state_updates["clarification_question"] = refiner_response.clarification_question
            chat_history.append({
                "role": "assistant",
                "content": refiner_response.clarification_question or "Could you clarify?"
            })

        elif refiner_response.intent == "approve":
            chat_history.append({
                "role": "assistant",
                "content": "Saving to Jira..."
            })

        elif refiner_response.intent == "cancel":
            chat_history.append({
                "role": "assistant",
                "content": "Operation cancelled."
            })

        state_updates["chat_history"] = chat_history

        return state_updates

    except Exception as e:
        logger.error(f"Refiner error: {e}")
        return {
            "refiner_intent": "clarification",
            "clarification_question": f"I encountered an error. Please try again or type 'cancel' to abort.",
            "error": str(e),
            "current_agent": "refiner",
        }


def add_user_message_to_chat(state: AgentState, message: str) -> dict:
    """
    Add a user message to chat history and prepare for refiner processing.

    Args:
        state: Current workflow state.
        message: User's message.

    Returns:
        dict: State updates with updated chat_history and pending_user_message.
    """
    chat_history = state.get("chat_history", []).copy()
    chat_history.append({"role": "user", "content": message})

    return {
        "chat_history": chat_history,
        "pending_user_message": message,
        "refinement_count": state.get("refinement_count", 0) + 1,
    }
