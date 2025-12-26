"""Integration tests for the LangGraph workflow."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.state import AgentState
from src.agents.workflow import (
    create_ac_workflow,
    create_initial_state,
    route_from_evaluator,
    route_from_gatherer,
    route_from_orchestrator,
)


class TestRoutingFunctions:
    """Tests for workflow routing functions."""

    def test_route_from_orchestrator_with_error(self):
        """Orchestrator routes to end on error."""
        state = {"error": "Some error", "needs_more_info": False}

        result = route_from_orchestrator(state)

        assert result == "end"

    def test_route_from_orchestrator_needs_info(self):
        """Orchestrator routes to gatherer when info is needed."""
        state = {"error": None, "needs_more_info": True}

        result = route_from_orchestrator(state)

        assert result == "gatherer"

    def test_route_from_orchestrator_sufficient_info(self):
        """Orchestrator routes to generator when info is sufficient."""
        state = {"error": None, "needs_more_info": False}

        result = route_from_orchestrator(state)

        assert result == "generator"

    def test_route_from_gatherer_question_pending(self):
        """Gatherer routes to wait when question is pending."""
        state = {
            "current_question": "What is the scope?",
            "questions_asked": 1,
            "needs_more_info": True,
        }

        result = route_from_gatherer(state)

        assert result == "wait_for_answer"

    def test_route_from_gatherer_max_questions(self):
        """Gatherer routes to generator when max questions reached."""
        state = {
            "current_question": None,
            "questions_asked": 5,  # Max questions
            "needs_more_info": False,
        }

        result = route_from_gatherer(state)

        assert result == "generator"

    def test_route_from_gatherer_sufficient_info(self):
        """Gatherer routes to generator when info is sufficient."""
        state = {
            "current_question": None,
            "questions_asked": 2,
            "needs_more_info": False,
        }

        result = route_from_gatherer(state)

        assert result == "generator"

    def test_route_from_evaluator_high_score(self):
        """Evaluator routes to end on high score."""
        state = {"quality_score": 8, "generation_attempts": 1}

        result = route_from_evaluator(state)

        assert result == "end"

    def test_route_from_evaluator_low_score_first_attempt(self):
        """Evaluator routes to generator for retry on low score."""
        state = {"quality_score": 5, "generation_attempts": 1}

        result = route_from_evaluator(state)

        assert result == "generator"

    def test_route_from_evaluator_max_attempts(self):
        """Evaluator routes to end when max attempts reached."""
        state = {"quality_score": 5, "generation_attempts": 2}

        result = route_from_evaluator(state)

        assert result == "end"


class TestCreateInitialState:
    """Tests for create_initial_state function."""

    def test_creates_complete_state(self):
        """Creates AgentState with all required fields."""
        state = create_initial_state(
            ticket_key="TEST-123",
            ticket_title="Test Ticket",
            ticket_description="Test description",
            ticket_type="Story",
            ticket_url="https://example.atlassian.net/browse/TEST-123",
            user_id="U12345",
            selected_format="bdd",
        )

        assert state["ticket_key"] == "TEST-123"
        assert state["ticket_title"] == "Test Ticket"
        assert state["ticket_description"] == "Test description"
        assert state["ticket_type"] == "Story"
        assert state["ticket_url"] == "https://example.atlassian.net/browse/TEST-123"
        assert state["user_id"] == "U12345"
        assert state["selected_format"] == "bdd"
        assert state["gathered_information"] == []
        assert state["questions_asked"] == 0
        assert state["generation_attempts"] == 0
        assert state["is_complete"] is False
        assert state["error"] is None

    def test_creates_state_with_default_format(self):
        """Creates state with None format when not specified."""
        state = create_initial_state(
            ticket_key="TEST-123",
            ticket_title="Test",
            ticket_description="",
            ticket_type="Bug",
            ticket_url="https://example.com",
            user_id="U12345",
        )

        assert state["selected_format"] is None


class TestWorkflowIntegration:
    """Integration tests for the full workflow."""

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.get_llm_provider")
    @patch("src.agents.orchestrator.format_prompt")
    @patch("src.agents.generator.get_llm_provider")
    @patch("src.agents.generator.format_prompt")
    @patch("src.agents.evaluator.get_llm_provider")
    @patch("src.agents.evaluator.format_prompt")
    async def test_happy_path_sufficient_info(
        self,
        mock_eval_prompt,
        mock_eval_provider,
        mock_gen_prompt,
        mock_gen_provider,
        mock_orch_prompt,
        mock_orch_provider,
    ):
        """Complete workflow when info is sufficient from start."""
        # Orchestrator says info is sufficient
        mock_orch_model = AsyncMock()
        mock_orch_model.ainvoke.return_value.content = json.dumps({
            "sufficient_information": True,
            "missing_information": [],
            "reasoning": "Complete"
        })
        mock_orch_provider.return_value.get_orchestrator_model.return_value = mock_orch_model

        # Generator produces AC
        mock_gen_model = AsyncMock()
        mock_gen_model.ainvoke.return_value.content = "- [ ] Criterion 1\n- [ ] Criterion 2"
        mock_gen_provider.return_value.get_main_model.return_value = mock_gen_model

        # Evaluator gives high score
        mock_eval_model = AsyncMock()
        mock_eval_model.ainvoke.return_value.content = json.dumps({
            "score": 9,
            "feedback": "Excellent",
            "strengths": ["Clear"],
            "improvements": []
        })
        mock_eval_provider.return_value.get_main_model.return_value = mock_eval_model

        # Create and run workflow
        workflow = create_ac_workflow()
        initial_state = create_initial_state(
            ticket_key="TEST-123",
            ticket_title="Test Feature",
            ticket_description="Implement a new feature",
            ticket_type="Story",
            ticket_url="https://example.com/TEST-123",
            user_id="U12345",
            selected_format="checklist",
        )

        result = await workflow.ainvoke(initial_state)

        assert result["generated_ac"] == "- [ ] Criterion 1\n- [ ] Criterion 2"
        assert result["quality_score"] == 9
        assert result["is_complete"] is True
        assert result["error"] is None

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.get_llm_provider")
    @patch("src.agents.orchestrator.format_prompt")
    @patch("src.agents.information_gatherer.get_llm_provider")
    @patch("src.agents.information_gatherer.format_prompt")
    async def test_workflow_pauses_for_question(
        self,
        mock_gath_prompt,
        mock_gath_provider,
        mock_orch_prompt,
        mock_orch_provider,
    ):
        """Workflow pauses when gatherer needs to ask a question."""
        # Orchestrator says info is insufficient
        mock_orch_model = AsyncMock()
        mock_orch_model.ainvoke.return_value.content = json.dumps({
            "sufficient_information": False,
            "missing_information": ["User role"],
            "reasoning": "Need more details"
        })
        mock_orch_provider.return_value.get_orchestrator_model.return_value = mock_orch_model

        # Gatherer asks a question
        mock_gath_model = AsyncMock()
        mock_gath_model.ainvoke.return_value.content = json.dumps({
            "sufficient_information": False,
            "question": "Who will use this feature?",
            "reasoning": "Need to understand audience"
        })
        mock_gath_provider.return_value.get_main_model.return_value = mock_gath_model

        workflow = create_ac_workflow()
        initial_state = create_initial_state(
            ticket_key="TEST-456",
            ticket_title="Vague Feature",
            ticket_description="Do something",
            ticket_type="Story",
            ticket_url="https://example.com/TEST-456",
            user_id="U12345",
        )

        result = await workflow.ainvoke(initial_state)

        # Workflow should pause with a question
        assert result["current_question"] == "Who will use this feature?"
        assert result["needs_more_info"] is True
        assert result["questions_asked"] == 1

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.get_llm_provider")
    @patch("src.agents.orchestrator.format_prompt")
    @patch("src.agents.generator.get_llm_provider")
    @patch("src.agents.generator.format_prompt")
    @patch("src.agents.evaluator.get_llm_provider")
    @patch("src.agents.evaluator.format_prompt")
    async def test_retry_on_low_score(
        self,
        mock_eval_prompt,
        mock_eval_provider,
        mock_gen_prompt,
        mock_gen_provider,
        mock_orch_prompt,
        mock_orch_provider,
    ):
        """Workflow retries generation when score is low."""
        # Orchestrator says info is sufficient
        mock_orch_model = AsyncMock()
        mock_orch_model.ainvoke.return_value.content = json.dumps({
            "sufficient_information": True,
            "missing_information": [],
            "reasoning": "Complete"
        })
        mock_orch_provider.return_value.get_orchestrator_model.return_value = mock_orch_model

        # Generator produces AC
        mock_gen_model = AsyncMock()
        mock_gen_model.ainvoke.return_value.content = "- [ ] Better criterion"
        mock_gen_provider.return_value.get_main_model.return_value = mock_gen_model

        # Evaluator gives low score first, then high score
        mock_eval_model = AsyncMock()
        mock_eval_model.ainvoke.side_effect = [
            AsyncMock(content=json.dumps({
                "score": 4,
                "feedback": "Needs improvement",
                "strengths": [],
                "improvements": ["Be more specific"]
            })),
            AsyncMock(content=json.dumps({
                "score": 8,
                "feedback": "Much better",
                "strengths": ["Clear"],
                "improvements": []
            })),
        ]
        mock_eval_provider.return_value.get_main_model.return_value = mock_eval_model

        workflow = create_ac_workflow()
        initial_state = create_initial_state(
            ticket_key="TEST-789",
            ticket_title="Test",
            ticket_description="Test description",
            ticket_type="Story",
            ticket_url="https://example.com/TEST-789",
            user_id="U12345",
            selected_format="checklist",
        )

        result = await workflow.ainvoke(initial_state)

        # Should have retried and succeeded
        assert result["generation_attempts"] == 2
        assert result["quality_score"] == 8
        assert result["is_complete"] is True
