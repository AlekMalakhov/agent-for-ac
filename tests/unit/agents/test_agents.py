"""Unit tests for agent implementations."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.evaluator import (
    evaluator_node,
    format_feedback_for_retry,
    parse_evaluation_response,
)
from src.agents.generator import (
    format_gathered_info,
    format_previous_feedback,
    generator_node,
)
from src.agents.information_gatherer import (
    add_user_answer,
    gatherer_node,
    parse_gatherer_response,
)
from src.agents.orchestrator import orchestrator_node, parse_orchestrator_decision
from src.agents.state import (
    AgentState,
    EvaluationResult,
    GathererResponse,
    OrchestratorDecision,
)


class TestOrchestratorAgent:
    """Tests for the Orchestrator Agent."""

    def test_parse_orchestrator_decision_valid_json(self):
        """Parse valid JSON orchestrator response."""
        response = json.dumps({
            "sufficient_information": True,
            "missing_information": [],
            "reasoning": "The ticket has all required details."
        })

        result = parse_orchestrator_decision(response)

        assert isinstance(result, OrchestratorDecision)
        assert result.sufficient_information is True
        assert result.missing_information == []
        assert result.reasoning == "The ticket has all required details."

    def test_parse_orchestrator_decision_insufficient_info(self):
        """Parse response indicating insufficient information."""
        response = json.dumps({
            "sufficient_information": False,
            "missing_information": ["User role", "Expected outcome"],
            "reasoning": "Missing key details."
        })

        result = parse_orchestrator_decision(response)

        assert result.sufficient_information is False
        assert len(result.missing_information) == 2
        assert "User role" in result.missing_information

    def test_parse_orchestrator_decision_invalid_json(self):
        """Handle invalid JSON gracefully."""
        response = "This is not JSON"

        result = parse_orchestrator_decision(response)

        assert result.sufficient_information is False
        assert "Unable to parse response" in result.missing_information

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.get_llm_provider")
    @patch("src.agents.orchestrator.format_prompt")
    async def test_orchestrator_node_sufficient_info(
        self, mock_format_prompt, mock_get_provider
    ):
        """Orchestrator returns needs_more_info=False when info is sufficient."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "sufficient_information": True,
            "missing_information": [],
            "reasoning": "Complete"
        })
        mock_get_provider.return_value.get_orchestrator_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "ticket_key": "TEST-123",
            "ticket_title": "Test ticket",
            "ticket_description": "Full description",
            "ticket_type": "Story",
        }

        result = await orchestrator_node(state)

        assert result["needs_more_info"] is False
        assert result["current_agent"] == "orchestrator"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.get_llm_provider")
    @patch("src.agents.orchestrator.format_prompt")
    async def test_orchestrator_node_needs_info(
        self, mock_format_prompt, mock_get_provider
    ):
        """Orchestrator returns needs_more_info=True when info is missing."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "sufficient_information": False,
            "missing_information": ["Details needed"],
            "reasoning": "Incomplete"
        })
        mock_get_provider.return_value.get_orchestrator_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "ticket_key": "TEST-123",
            "ticket_title": "Test",
            "ticket_description": "",
            "ticket_type": "Bug",
        }

        result = await orchestrator_node(state)

        assert result["needs_more_info"] is True


class TestInformationGathererAgent:
    """Tests for the Information Gatherer Agent."""

    def test_parse_gatherer_response_valid_json(self):
        """Parse valid JSON gatherer response."""
        response = json.dumps({
            "sufficient_information": False,
            "question": "What is the expected behavior?",
            "reasoning": "Need to understand outcomes"
        })

        result = parse_gatherer_response(response)

        assert isinstance(result, GathererResponse)
        assert result.sufficient_information is False
        assert result.question == "What is the expected behavior?"

    def test_parse_gatherer_response_sufficient(self):
        """Parse response indicating sufficient information."""
        response = json.dumps({
            "sufficient_information": True,
            "question": None,
            "reasoning": "All necessary info gathered"
        })

        result = parse_gatherer_response(response)

        assert result.sufficient_information is True
        assert result.question is None

    def test_parse_gatherer_response_invalid_json(self):
        """Handle invalid JSON gracefully."""
        response = "Invalid JSON"

        result = parse_gatherer_response(response)

        # Should default to sufficient to avoid infinite loop
        assert result.sufficient_information is True

    def test_format_gathered_info_empty(self):
        """Format empty gathered info."""
        from src.agents.information_gatherer import (
            format_gathered_info as gatherer_format,
        )

        result = gatherer_format([])

        assert result == "No additional information gathered yet."

    def test_format_gathered_info_with_qa(self):
        """Format gathered Q&A pairs."""
        gathered = [
            {"question": "Q1?", "answer": "A1"},
            {"question": "Q2?", "answer": "A2"},
        ]

        result = format_gathered_info(gathered)

        assert "Q1:" in result
        assert "A1" in result
        assert "Q2:" in result
        assert "A2" in result

    def test_add_user_answer(self):
        """Add user answer to state."""
        state = {
            "current_question": "What is the scope?",
            "gathered_information": [{"question": "Q1?", "answer": "A1"}],
        }

        result = add_user_answer(state, "The scope is limited to X")

        assert len(result["gathered_information"]) == 2
        assert result["gathered_information"][1]["question"] == "What is the scope?"
        assert result["gathered_information"][1]["answer"] == "The scope is limited to X"
        assert result["current_question"] is None

    @pytest.mark.asyncio
    @patch("src.agents.information_gatherer.get_llm_provider")
    @patch("src.agents.information_gatherer.format_prompt")
    async def test_gatherer_node_asks_question(
        self, mock_format_prompt, mock_get_provider
    ):
        """Gatherer returns a question when more info is needed."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "sufficient_information": False,
            "question": "What users will use this?",
            "reasoning": "Need to understand audience"
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "ticket_title": "Test",
            "ticket_description": "Desc",
            "gathered_information": [],
            "questions_asked": 0,
        }

        result = await gatherer_node(state)

        assert result["current_question"] == "What users will use this?"
        assert result["needs_more_info"] is True
        assert result["questions_asked"] == 1

    @pytest.mark.asyncio
    async def test_gatherer_node_max_questions_reached(self):
        """Gatherer proceeds to generation when max questions reached."""
        state = {
            "ticket_title": "Test",
            "ticket_description": "Desc",
            "gathered_information": [],
            "questions_asked": 5,  # Max questions reached
        }

        result = await gatherer_node(state)

        assert result["needs_more_info"] is False
        assert result["current_question"] is None


class TestGeneratorAgent:
    """Tests for the Generator Agent."""

    def test_format_gathered_info_empty(self):
        """Format empty gathered info for generator."""
        result = format_gathered_info([])

        assert result == "No additional context available."

    def test_format_previous_feedback_empty(self):
        """Format empty feedback."""
        result = format_previous_feedback(None)

        assert result == ""

    def test_format_previous_feedback_with_content(self):
        """Format feedback for retry prompt."""
        result = format_previous_feedback("Improve specificity")

        assert "retry based on previous evaluation" in result.lower()
        assert "Improve specificity" in result

    @pytest.mark.asyncio
    @patch("src.agents.generator.get_llm_provider")
    @patch("src.agents.generator.format_prompt")
    async def test_generator_node_produces_ac(
        self, mock_format_prompt, mock_get_provider
    ):
        """Generator produces acceptance criteria."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = "- [ ] Criterion 1\n- [ ] Criterion 2"
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "ticket_title": "Test",
            "ticket_description": "Desc",
            "gathered_information": [],
            "selected_format": "checklist",
            "generation_attempts": 0,
            "evaluator_feedback": None,
        }

        result = await generator_node(state)

        assert result["generated_ac"] == "- [ ] Criterion 1\n- [ ] Criterion 2"
        assert result["generation_attempts"] == 1
        assert result["current_agent"] == "generator"


class TestEvaluatorAgent:
    """Tests for the Evaluator Agent."""

    def test_parse_evaluation_response_valid_json(self):
        """Parse valid JSON evaluation response."""
        response = json.dumps({
            "score": 8,
            "feedback": "Good quality AC",
            "strengths": ["Clear", "Testable"],
            "improvements": ["Add edge cases"]
        })

        result = parse_evaluation_response(response)

        assert isinstance(result, EvaluationResult)
        assert result.score == 8
        assert result.feedback == "Good quality AC"
        assert len(result.strengths) == 2
        assert len(result.improvements) == 1

    def test_parse_evaluation_response_invalid_json(self):
        """Handle invalid JSON gracefully."""
        response = "Not JSON"

        result = parse_evaluation_response(response)

        # Should default to passing score
        assert result.score == 7

    def test_format_feedback_for_retry(self):
        """Format evaluation feedback for retry."""
        evaluation = EvaluationResult(
            score=5,
            feedback="Needs improvement",
            strengths=["Clear"],
            improvements=["Add more detail", "Cover edge cases"]
        )

        result = format_feedback_for_retry(evaluation)

        assert "Score: 5/10" in result
        assert "Needs improvement" in result
        assert "Add more detail" in result
        assert "Cover edge cases" in result

    @pytest.mark.asyncio
    @patch("src.agents.evaluator.get_llm_provider")
    @patch("src.agents.evaluator.format_prompt")
    async def test_evaluator_node_high_score(
        self, mock_format_prompt, mock_get_provider
    ):
        """Evaluator marks complete when score is high."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "score": 9,
            "feedback": "Excellent AC",
            "strengths": ["Very clear"],
            "improvements": []
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Test criterion",
            "selected_format": "checklist",
            "generation_attempts": 1,
        }

        result = await evaluator_node(state)

        assert result["quality_score"] == 9
        assert result["is_complete"] is True

    @pytest.mark.asyncio
    @patch("src.agents.evaluator.get_llm_provider")
    @patch("src.agents.evaluator.format_prompt")
    async def test_evaluator_node_low_score(
        self, mock_format_prompt, mock_get_provider
    ):
        """Evaluator marks not complete when score is low."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "score": 4,
            "feedback": "Needs work",
            "strengths": [],
            "improvements": ["Be more specific"]
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Vague criterion",
            "selected_format": "checklist",
            "generation_attempts": 1,
        }

        result = await evaluator_node(state)

        assert result["quality_score"] == 4
        assert result["is_complete"] is False  # Should retry

    @pytest.mark.asyncio
    async def test_evaluator_node_no_ac(self):
        """Evaluator handles missing AC."""
        state = {
            "generated_ac": None,
            "selected_format": "checklist",
            "generation_attempts": 1,
        }

        result = await evaluator_node(state)

        assert result["quality_score"] == 0
        assert result["is_complete"] is True
        assert result["error"] == "No acceptance criteria generated"
