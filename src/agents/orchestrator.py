"""Orchestrator Agent for analyzing ticket information sufficiency."""

import json
import logging

from src.agents.llm import get_llm_provider
from src.agents.prompts import format_prompt
from src.agents.state import AgentState, OrchestratorDecision

logger = logging.getLogger(__name__)


def parse_orchestrator_decision(response_content: str) -> OrchestratorDecision:
    """
    Parse the orchestrator response into a structured decision.

    Args:
        response_content: Raw LLM response content.

    Returns:
        OrchestratorDecision: Parsed decision object.
    """
    try:
        # Try to parse as JSON
        data = json.loads(response_content)
        return OrchestratorDecision(**data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse orchestrator response as JSON: {e}")
        # Default to needing more information if parsing fails
        return OrchestratorDecision(
            sufficient_information=False,
            missing_information=["Unable to parse response"],
            reasoning="Parsing error, defaulting to information gathering",
        )


async def orchestrator_node(state: AgentState) -> dict:
    """
    Orchestrator Agent node for the workflow.

    Analyzes ticket content and decides if more information is needed
    to generate high-quality acceptance criteria.

    Uses Claude 3.5 Haiku for fast, cost-effective decisions.

    Args:
        state: Current workflow state.

    Returns:
        dict: State updates including needs_more_info decision.
    """
    logger.info(f"Orchestrator analyzing ticket: {state['ticket_key']}")

    try:
        provider = get_llm_provider()
        model = provider.get_orchestrator_model()

        prompt = format_prompt(
            "orchestrator.txt",
            title=state["ticket_title"],
            description=state["ticket_description"],
            ticket_type=state["ticket_type"],
        )

        response = await model.ainvoke(prompt)
        decision = parse_orchestrator_decision(response.content)

        logger.info(
            f"Orchestrator decision: sufficient_info={decision.sufficient_information}, "
            f"missing={decision.missing_information}"
        )

        return {
            "needs_more_info": not decision.sufficient_information,
            "current_agent": "orchestrator",
        }

    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        return {
            "error": str(e),
            "current_agent": "orchestrator",
        }
