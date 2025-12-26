"""Evaluator Agent for assessing acceptance criteria quality."""

import json
import logging

from src.agents.llm import get_llm_provider
from src.agents.prompts import format_prompt
from src.agents.state import AgentState, EvaluationResult

logger = logging.getLogger(__name__)

# Quality score threshold for acceptance
QUALITY_THRESHOLD = 7
# Maximum generation attempts
MAX_GENERATION_ATTEMPTS = 2


def parse_evaluation_response(response_content: str) -> EvaluationResult:
    """
    Parse the evaluator response into a structured result.

    Args:
        response_content: Raw LLM response content.

    Returns:
        EvaluationResult: Parsed evaluation result.
    """
    try:
        data = json.loads(response_content)
        return EvaluationResult(**data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse evaluator response as JSON: {e}")
        # Default to passing score if parsing fails
        return EvaluationResult(
            score=7,
            feedback="Unable to parse evaluation response",
            strengths=[],
            improvements=[],
        )


def format_feedback_for_retry(evaluation: EvaluationResult) -> str:
    """
    Format evaluation result as feedback for generator retry.

    Args:
        evaluation: Evaluation result object.

    Returns:
        str: Formatted feedback string.
    """
    feedback_parts = [f"Score: {evaluation.score}/10", f"Feedback: {evaluation.feedback}"]

    if evaluation.improvements:
        feedback_parts.append("\nAreas to improve:")
        for improvement in evaluation.improvements:
            feedback_parts.append(f"- {improvement}")

    return "\n".join(feedback_parts)


async def evaluator_node(state: AgentState) -> dict:
    """
    Evaluator Agent node for the workflow.

    Evaluates the quality of generated acceptance criteria
    and provides feedback for improvement.

    Uses Claude 3.7 Sonnet for quality assessment.

    Args:
        state: Current workflow state.

    Returns:
        dict: State updates including quality_score and evaluator_feedback.
    """
    generation_attempts = state.get("generation_attempts", 0)
    selected_format = state.get("selected_format") or "checklist"
    generated_ac = state.get("generated_ac", "")

    logger.info(f"Evaluator: assessing AC (attempt {generation_attempts})")

    if not generated_ac:
        logger.warning("No AC to evaluate")
        return {
            "quality_score": 0,
            "evaluator_feedback": "No acceptance criteria to evaluate",
            "current_agent": "evaluator",
            "is_complete": True,
            "error": "No acceptance criteria generated",
        }

    try:
        provider = get_llm_provider()
        model = provider.get_main_model()

        prompt = format_prompt(
            "evaluator.txt",
            acceptance_criteria=generated_ac,
            format=selected_format,
        )

        response = await model.ainvoke(prompt)
        evaluation = parse_evaluation_response(response.content)

        logger.info(f"Evaluator score: {evaluation.score}/10")

        # Determine if we're done
        is_complete = (
            evaluation.score >= QUALITY_THRESHOLD
            or generation_attempts >= MAX_GENERATION_ATTEMPTS
        )

        # Format feedback for potential retry
        feedback = format_feedback_for_retry(evaluation)

        return {
            "quality_score": evaluation.score,
            "evaluator_feedback": feedback,
            "current_agent": "evaluator",
            "is_complete": is_complete,
        }

    except Exception as e:
        logger.error(f"Evaluator error: {e}")
        return {
            "quality_score": 0,
            "evaluator_feedback": str(e),
            "current_agent": "evaluator",
            "is_complete": True,  # Complete on error to avoid infinite loop
            "error": str(e),
        }
