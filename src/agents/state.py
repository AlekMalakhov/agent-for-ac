"""Shared state schema for AC generation workflow."""

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class AgentState(TypedDict):
    """Shared state for all agents in the workflow."""

    # Jira ticket data
    ticket_key: str
    ticket_title: str
    ticket_description: str
    ticket_type: str
    ticket_url: str

    # Conversation context
    user_id: str
    gathered_information: list[dict]  # Q&A history: [{"question": ..., "answer": ...}]
    questions_asked: int
    reformulation_attempts: int

    # Current question (for Information Gatherer)
    current_question: str | None

    # AC generation
    selected_format: Literal["checklist", "bdd", "free"] | None
    generated_ac: str | None
    generation_attempts: int

    # Evaluation
    quality_score: int | None
    evaluator_feedback: str | None

    # Flow control
    current_agent: str
    needs_more_info: bool
    is_complete: bool
    error: str | None

    # Chat refinement fields
    chat_history: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]
    refinement_count: int  # Track number of refinements
    pending_user_message: str | None  # Latest user message to process
    refiner_intent: str | None  # Last classified intent
    clarification_question: str | None  # Question to ask user when intent is unclear
    target_criterion: int | None  # Criterion number for modify/remove operations
    modification_details: str | None  # Details about the requested modification
    regeneration_context: str | None  # Additional context for regeneration requests


class EvaluationResult(BaseModel):
    """Result from Evaluator Agent."""

    score: int = Field(..., ge=1, le=10, description="Quality score from 1 to 10")
    feedback: str = Field(..., description="Overall assessment of the acceptance criteria")
    strengths: list[str] = Field(default_factory=list, description="List of strong points")
    improvements: list[str] = Field(
        default_factory=list, description="Specific suggestions for improvement"
    )


class OrchestratorDecision(BaseModel):
    """Decision from Orchestrator Agent."""

    sufficient_information: bool = Field(
        ..., description="Whether there is enough information to generate AC"
    )
    missing_information: list[str] = Field(
        default_factory=list, description="List of missing details"
    )
    reasoning: str = Field(..., description="Brief explanation of the decision")


class GathererResponse(BaseModel):
    """Response from Information Gatherer Agent."""

    sufficient_information: bool = Field(
        ..., description="Whether enough information has been gathered"
    )
    question: str | None = Field(
        None, description="Clarifying question to ask (null if sufficient)"
    )
    reasoning: str = Field(..., description="Why this information is needed")


class RefinerResponse(BaseModel):
    """Response from Refiner Agent for classifying user intent."""

    intent: Literal[
        "modify_specific",
        "add_criterion",
        "remove_criterion",
        "change_format",
        "regenerate",
        "approve",
        "cancel",
        "clarification",
    ] = Field(..., description="Classified user intent")
    target_criterion: int | None = Field(
        None, description="Criterion number to modify/remove (1-indexed)"
    )
    modification_details: str | None = Field(
        default="", description="Details about what to change"
    )
    new_format: Literal["checklist", "bdd", "free"] | None = Field(
        None, description="Target format for format change requests"
    )
    regeneration_context: str | None = Field(
        None, description="Additional context for regeneration requests"
    )
    clarification_question: str | None = Field(
        None, description="Question to ask if intent is unclear"
    )
    reasoning: str | None = Field(default="", description="Brief explanation of classification")
