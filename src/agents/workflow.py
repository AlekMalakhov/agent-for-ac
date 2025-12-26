"""LangGraph workflow for AC generation."""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from src.agents.evaluator import QUALITY_THRESHOLD, evaluator_node
from src.agents.generator import MAX_GENERATION_ATTEMPTS, generator_node
from src.agents.information_gatherer import MAX_QUESTIONS, gatherer_node
from src.agents.modifier import modifier_node
from src.agents.orchestrator import orchestrator_node
from src.agents.refiner import refiner_node
from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def route_from_orchestrator(state: AgentState) -> Literal["gatherer", "generator", "end"]:
    """
    Route from Orchestrator to next node.

    Args:
        state: Current workflow state.

    Returns:
        str: Next node name or "end".
    """
    if state.get("error"):
        logger.info("Orchestrator error, ending workflow")
        return "end"

    if state.get("needs_more_info"):
        logger.info("Orchestrator: needs more info, routing to gatherer")
        return "gatherer"

    logger.info("Orchestrator: sufficient info, routing to generator")
    return "generator"


def route_from_gatherer(state: AgentState) -> Literal["wait_for_answer", "generator", "end"]:
    """
    Route from Information Gatherer to next node.

    Args:
        state: Current workflow state.

    Returns:
        str: Next node name or "end".
    """
    questions_asked = state.get("questions_asked", 0)
    needs_more_info = state.get("needs_more_info", False)
    current_question = state.get("current_question")

    # If there's a question to ask, wait for user answer
    if current_question:
        logger.info(f"Gatherer: question pending, waiting for answer")
        return "wait_for_answer"

    # If max questions reached, proceed to generation
    if questions_asked >= MAX_QUESTIONS:
        logger.info("Gatherer: max questions reached, routing to generator")
        return "generator"

    # If no more info needed, proceed to generation
    if not needs_more_info:
        logger.info("Gatherer: sufficient info, routing to generator")
        return "generator"

    logger.info("Gatherer: ending (unexpected state)")
    return "end"


def route_from_evaluator(state: AgentState) -> Literal["generator", "end"]:
    """
    Route from Evaluator to next node.

    Args:
        state: Current workflow state.

    Returns:
        str: Next node name or "end".
    """
    score = state.get("quality_score", 0)
    attempts = state.get("generation_attempts", 0)

    if score >= QUALITY_THRESHOLD:
        logger.info(f"Evaluator: score {score} >= {QUALITY_THRESHOLD}, success")
        return "end"

    if attempts >= MAX_GENERATION_ATTEMPTS:
        logger.info(f"Evaluator: max attempts ({attempts}) reached, ending")
        return "end"

    logger.info(f"Evaluator: score {score} < {QUALITY_THRESHOLD}, retrying generation")
    return "generator"


def route_from_refiner(
    state: AgentState,
) -> Literal["modifier", "generator", "wait_for_chat", "end"]:
    """
    Route from Refiner to next node based on classified intent.

    Args:
        state: Current workflow state.

    Returns:
        str: Next node name or "end".
    """
    intent = state.get("refiner_intent", "")

    if intent in ("approve", "cancel"):
        logger.info(f"Refiner: intent={intent}, ending workflow")
        return "end"

    if intent in ("modify_specific", "add_criterion", "remove_criterion"):
        logger.info(f"Refiner: intent={intent}, routing to modifier")
        return "modifier"

    if intent in ("change_format", "regenerate"):
        logger.info(f"Refiner: intent={intent}, routing to generator for full regeneration")
        return "generator"

    if intent == "clarification":
        logger.info("Refiner: clarification needed, waiting for user input")
        return "wait_for_chat"

    logger.info(f"Refiner: unexpected intent={intent}, waiting for chat")
    return "wait_for_chat"


def create_ac_workflow() -> StateGraph:
    """
    Create the AC generation workflow graph.

    The workflow follows this pattern:
    1. Orchestrator analyzes ticket and decides if info is sufficient
    2. If not sufficient, Information Gatherer asks clarifying questions
    3. Generator creates acceptance criteria
    4. Evaluator assesses quality and may trigger regeneration

    Returns:
        StateGraph: Compiled workflow graph.
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("gatherer", gatherer_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("evaluator", evaluator_node)

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Orchestrator routing
    workflow.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "gatherer": "gatherer",
            "generator": "generator",
            "end": END,
        },
    )

    # Gatherer routing - note: "wait_for_answer" goes to END to allow
    # external handling (Slack interaction)
    workflow.add_conditional_edges(
        "gatherer",
        route_from_gatherer,
        {
            "wait_for_answer": END,  # Pause for user input
            "generator": "generator",
            "end": END,
        },
    )

    # Generator -> Evaluator
    workflow.add_edge("generator", "evaluator")

    # Evaluator routing
    workflow.add_conditional_edges(
        "evaluator",
        route_from_evaluator,
        {
            "generator": "generator",
            "end": END,
        },
    )

    return workflow.compile()


def create_chat_refinement_workflow() -> StateGraph:
    """
    Create the chat refinement workflow graph.

    This workflow handles interactive refinement of generated AC:
    1. Refiner classifies user intent
    2. Routes to modifier (surgical edits) or generator (full regeneration)
    3. Evaluator assesses quality of modifications
    4. Ends when user approves, cancels, or needs clarification

    Returns:
        StateGraph: Compiled chat refinement workflow graph.
    """
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("refiner", refiner_node)
    workflow.add_node("modifier", modifier_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("evaluator", evaluator_node)

    # Set entry point
    workflow.set_entry_point("refiner")

    # Refiner routing
    workflow.add_conditional_edges(
        "refiner",
        route_from_refiner,
        {
            "modifier": "modifier",
            "generator": "generator",
            "wait_for_chat": END,  # Pause for user input
            "end": END,  # Approve or cancel
        },
    )

    # Modifier -> Evaluator
    workflow.add_edge("modifier", "evaluator")

    # Generator -> Evaluator
    workflow.add_edge("generator", "evaluator")

    # Evaluator always ends (no retry loop in chat mode, user can request changes)
    workflow.add_edge("evaluator", END)

    return workflow.compile()


def create_initial_state(
    ticket_key: str,
    ticket_title: str,
    ticket_description: str,
    ticket_type: str,
    ticket_url: str,
    user_id: str,
    selected_format: Literal["checklist", "bdd", "free"] | None = None,
    slack_context: str | None = None,
    slack_context_source: str | None = None,
) -> AgentState:
    """
    Create initial workflow state from ticket data.

    Args:
        ticket_key: Jira ticket key (e.g., "PROJ-123")
        ticket_title: Ticket title/summary
        ticket_description: Ticket description
        ticket_type: Ticket type (Bug, Story, etc.)
        ticket_url: URL to the ticket
        user_id: Slack user ID
        selected_format: AC format preference
        slack_context: LLM-summarized context from Slack discussions
        slack_context_source: Source of context ("channel" or "none")

    Returns:
        AgentState: Initialized state for workflow.
    """
    return AgentState(
        ticket_key=ticket_key,
        ticket_title=ticket_title,
        ticket_description=ticket_description or "",
        ticket_type=ticket_type,
        ticket_url=ticket_url,
        user_id=user_id,
        gathered_information=[],
        questions_asked=0,
        reformulation_attempts=0,
        current_question=None,
        selected_format=selected_format,
        generated_ac=None,
        generation_attempts=0,
        quality_score=None,
        evaluator_feedback=None,
        current_agent="orchestrator",
        needs_more_info=False,
        is_complete=False,
        error=None,
        # Slack context fields
        slack_context=slack_context,
        slack_context_source=slack_context_source,
        # Chat refinement fields
        chat_history=[],
        refinement_count=0,
        pending_user_message=None,
        refiner_intent=None,
        clarification_question=None,
        target_criterion=None,
        modification_details=None,
        regeneration_context=None,
    )
