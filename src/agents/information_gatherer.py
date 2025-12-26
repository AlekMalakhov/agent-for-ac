"""Information Gatherer Agent for collecting additional context."""

import json
import logging

from src.agents.llm import get_llm_provider
from src.agents.prompts import format_prompt
from src.agents.state import AgentState, GathererResponse

logger = logging.getLogger(__name__)

# Maximum number of questions to ask
MAX_QUESTIONS = 5
# Maximum reformulation attempts per question
MAX_REFORMULATIONS = 3


def parse_gatherer_response(response_content: str) -> GathererResponse:
    """
    Parse the gatherer response into a structured format.

    Args:
        response_content: Raw LLM response content.

    Returns:
        GathererResponse: Parsed response object.
    """
    try:
        data = json.loads(response_content)
        return GathererResponse(**data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse gatherer response as JSON: {e}")
        # Default to sufficient if parsing fails (to avoid infinite loop)
        return GathererResponse(
            sufficient_information=True,
            question=None,
            reasoning="Parsing error, proceeding to generation",
        )


def format_gathered_info(gathered_information: list[dict]) -> str:
    """
    Format gathered Q&A pairs for prompt inclusion.

    Args:
        gathered_information: List of Q&A dicts.

    Returns:
        str: Formatted string of Q&A pairs.
    """
    if not gathered_information:
        return "No additional information gathered yet."

    formatted = []
    for i, qa in enumerate(gathered_information, 1):
        formatted.append(f"Q{i}: {qa.get('question', 'N/A')}")
        formatted.append(f"A{i}: {qa.get('answer', 'N/A')}")
        formatted.append("")

    return "\n".join(formatted)


async def gatherer_node(state: AgentState) -> dict:
    """
    Information Gatherer Agent node for the workflow.

    Asks clarifying questions one at a time to collect additional
    context for AC generation.

    Uses Claude 3.7 Sonnet for high-quality question generation.

    Args:
        state: Current workflow state.

    Returns:
        dict: State updates including current_question and needs_more_info.
    """
    questions_asked = state.get("questions_asked", 0)
    logger.info(f"Information Gatherer: questions asked so far: {questions_asked}")

    # Check if we've reached the question limit
    if questions_asked >= MAX_QUESTIONS:
        logger.info("Maximum questions reached, proceeding to generation")
        return {
            "needs_more_info": False,
            "current_question": None,
            "current_agent": "gatherer",
        }

    try:
        provider = get_llm_provider()
        model = provider.get_main_model()

        gathered_info_str = format_gathered_info(state.get("gathered_information", []))

        prompt = format_prompt(
            "information_gatherer.txt",
            title=state["ticket_title"],
            description=state["ticket_description"],
            gathered_info=gathered_info_str,
            questions_asked=questions_asked,
        )

        response = await model.ainvoke(prompt)
        gatherer_response = parse_gatherer_response(response.content)

        logger.info(
            f"Gatherer response: sufficient={gatherer_response.sufficient_information}, "
            f"question={gatherer_response.question is not None}"
        )

        # Update state based on response
        updates = {
            "current_agent": "gatherer",
            "needs_more_info": not gatherer_response.sufficient_information,
        }

        if gatherer_response.question:
            updates["current_question"] = gatherer_response.question
            updates["questions_asked"] = questions_asked + 1
        else:
            updates["current_question"] = None

        return updates

    except Exception as e:
        logger.error(f"Information Gatherer error: {e}")
        return {
            "error": str(e),
            "current_agent": "gatherer",
            "needs_more_info": False,  # Proceed to generation on error
        }


def add_user_answer(state: AgentState, answer: str) -> dict:
    """
    Add user's answer to gathered information.

    This function is called when user responds to a clarifying question.

    Args:
        state: Current workflow state.
        answer: User's answer to the current question.

    Returns:
        dict: State updates with new gathered information.
    """
    current_question = state.get("current_question")
    gathered_info = state.get("gathered_information", []).copy()

    if current_question:
        gathered_info.append({
            "question": current_question,
            "answer": answer,
        })

    return {
        "gathered_information": gathered_info,
        "current_question": None,
    }
