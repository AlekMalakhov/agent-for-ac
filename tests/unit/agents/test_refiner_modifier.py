"""Unit tests for Refiner and Modifier agent implementations."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.modifier import (
    format_target_description,
    get_modification_type_description,
    modifier_node,
)
from src.agents.refiner import (
    add_user_message_to_chat,
    format_chat_history,
    refiner_node,
)
from src.agents.state import RefinerResponse


class TestRefinerAgent:
    """Tests for the Refiner Agent."""

    def test_format_chat_history_empty(self):
        """Format empty chat history."""
        result = format_chat_history([])
        assert result == "No previous conversation."

    def test_format_chat_history_with_messages(self):
        """Format chat history with messages."""
        history = [
            {"role": "user", "content": "Make it more specific"},
            {"role": "assistant", "content": "I've updated the criteria."},
        ]

        result = format_chat_history(history)

        assert "User: Make it more specific" in result
        assert "Assistant: I've updated the criteria." in result

    def test_add_user_message_to_chat(self):
        """Add user message to chat history."""
        state = {
            "chat_history": [{"role": "assistant", "content": "How can I help?"}],
            "refinement_count": 0,
        }

        result = add_user_message_to_chat(state, "Make criterion 3 more specific")

        assert len(result["chat_history"]) == 2
        assert result["chat_history"][1]["role"] == "user"
        assert result["chat_history"][1]["content"] == "Make criterion 3 more specific"
        assert result["pending_user_message"] == "Make criterion 3 more specific"
        assert result["refinement_count"] == 1

    def test_add_user_message_preserves_history(self):
        """Adding message preserves existing chat history."""
        state = {
            "chat_history": [
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "Response"},
            ],
            "refinement_count": 2,
        }

        result = add_user_message_to_chat(state, "Second message")

        assert len(result["chat_history"]) == 3
        assert result["refinement_count"] == 3

    @pytest.mark.asyncio
    @patch("src.agents.refiner.get_llm_provider")
    @patch("src.agents.refiner.format_prompt")
    async def test_refiner_node_modify_specific(
        self, mock_format_prompt, mock_get_provider
    ):
        """Refiner classifies modify_specific intent correctly."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "intent": "modify_specific",
            "target_criterion": 3,
            "modification_details": "more specific about error handling",
            "new_format": None,
            "regeneration_context": None,
            "clarification_question": None,
            "reasoning": "User wants to modify criterion 3"
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1\n- [ ] Criterion 2\n- [ ] Criterion 3",
            "selected_format": "checklist",
            "pending_user_message": "Make criterion 3 more specific about errors",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await refiner_node(state)

        assert result["refiner_intent"] == "modify_specific"
        assert result["target_criterion"] == 3
        assert result["current_agent"] == "refiner"

    @pytest.mark.asyncio
    @patch("src.agents.refiner.get_llm_provider")
    @patch("src.agents.refiner.format_prompt")
    async def test_refiner_node_add_criterion(
        self, mock_format_prompt, mock_get_provider
    ):
        """Refiner classifies add_criterion intent correctly."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "intent": "add_criterion",
            "target_criterion": None,
            "modification_details": "error handling",
            "new_format": None,
            "regeneration_context": None,
            "clarification_question": None,
            "reasoning": "User wants to add a criterion for error handling"
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1",
            "selected_format": "checklist",
            "pending_user_message": "Add an error handling criterion",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await refiner_node(state)

        assert result["refiner_intent"] == "add_criterion"
        assert result["modification_details"] == "error handling"

    @pytest.mark.asyncio
    @patch("src.agents.refiner.get_llm_provider")
    @patch("src.agents.refiner.format_prompt")
    async def test_refiner_node_change_format(
        self, mock_format_prompt, mock_get_provider
    ):
        """Refiner classifies change_format intent correctly."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "intent": "change_format",
            "target_criterion": None,
            "modification_details": "",
            "new_format": "bdd",
            "regeneration_context": None,
            "clarification_question": None,
            "reasoning": "User wants to convert to BDD format"
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1",
            "selected_format": "checklist",
            "pending_user_message": "Convert to BDD format",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await refiner_node(state)

        assert result["refiner_intent"] == "change_format"
        assert result["selected_format"] == "bdd"

    @pytest.mark.asyncio
    @patch("src.agents.refiner.get_llm_provider")
    @patch("src.agents.refiner.format_prompt")
    async def test_refiner_node_approve(
        self, mock_format_prompt, mock_get_provider
    ):
        """Refiner classifies approve intent correctly."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "intent": "approve",
            "target_criterion": None,
            "modification_details": "",
            "new_format": None,
            "regeneration_context": None,
            "clarification_question": None,
            "reasoning": "User is satisfied with the AC"
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1",
            "selected_format": "checklist",
            "pending_user_message": "looks good",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await refiner_node(state)

        assert result["refiner_intent"] == "approve"

    @pytest.mark.asyncio
    @patch("src.agents.refiner.get_llm_provider")
    @patch("src.agents.refiner.format_prompt")
    async def test_refiner_node_clarification(
        self, mock_format_prompt, mock_get_provider
    ):
        """Refiner asks for clarification when intent is unclear."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = json.dumps({
            "intent": "clarification",
            "target_criterion": None,
            "modification_details": "",
            "new_format": None,
            "regeneration_context": None,
            "clarification_question": "Which criterion would you like to change?",
            "reasoning": "Unclear what user wants to modify"
        })
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1",
            "selected_format": "checklist",
            "pending_user_message": "change it",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await refiner_node(state)

        assert result["refiner_intent"] == "clarification"
        assert result["clarification_question"] == "Which criterion would you like to change?"

    @pytest.mark.asyncio
    async def test_refiner_node_no_pending_message(self):
        """Refiner handles missing pending message."""
        state = {
            "generated_ac": "- [ ] Criterion 1",
            "selected_format": "checklist",
            "pending_user_message": None,
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await refiner_node(state)

        assert result["refiner_intent"] == "clarification"
        assert "didn't receive a message" in result["clarification_question"]

    @pytest.mark.asyncio
    @patch("src.agents.refiner.get_llm_provider")
    @patch("src.agents.refiner.format_prompt")
    async def test_refiner_node_invalid_json_response(
        self, mock_format_prompt, mock_get_provider
    ):
        """Refiner handles invalid JSON response gracefully."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = "This is not valid JSON"
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1",
            "selected_format": "checklist",
            "pending_user_message": "Some message",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await refiner_node(state)

        assert result["refiner_intent"] == "clarification"
        assert "not sure what you'd like to change" in result["clarification_question"]


class TestModifierAgent:
    """Tests for the Modifier Agent."""

    def test_get_modification_type_description(self):
        """Get modification type descriptions."""
        assert get_modification_type_description("modify_specific") == "Modify specific criterion"
        assert get_modification_type_description("add_criterion") == "Add new criterion"
        assert get_modification_type_description("remove_criterion") == "Remove criterion"
        assert get_modification_type_description("unknown") == "Modify criteria"

    def test_format_target_description_modify(self):
        """Format target description for modify intent."""
        state = {
            "refiner_intent": "modify_specific",
            "target_criterion": 3,
            "modification_details": "more specific about errors",
        }

        result = format_target_description(state)

        assert "Criterion #3" in result
        assert "more specific about errors" in result

    def test_format_target_description_add(self):
        """Format target description for add intent."""
        state = {
            "refiner_intent": "add_criterion",
            "target_criterion": None,
            "modification_details": "error handling",
        }

        result = format_target_description(state)

        assert "Add new criterion about: error handling" in result

    def test_format_target_description_remove(self):
        """Format target description for remove intent."""
        state = {
            "refiner_intent": "remove_criterion",
            "target_criterion": 5,
            "modification_details": "",
        }

        result = format_target_description(state)

        assert "Criterion #5" in result

        # Test with modification details
        state_with_details = {
            "refiner_intent": "remove_criterion",
            "target_criterion": 6,
            "modification_details": "Error Handling section",
        }

        result_with_details = format_target_description(state_with_details)

        assert "Criterion #6" in result_with_details
        assert "Error Handling section" in result_with_details

    @pytest.mark.asyncio
    @patch("src.agents.modifier.get_llm_provider")
    @patch("src.agents.modifier.format_prompt")
    async def test_modifier_node_modifies_ac(
        self, mock_format_prompt, mock_get_provider
    ):
        """Modifier applies changes and returns updated AC."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = (
            "- [ ] Criterion 1\n"
            "- [ ] Criterion 2\n"
            "- [ ] Criterion 3: Now more specific about error handling"
        )
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1\n- [ ] Criterion 2\n- [ ] Criterion 3",
            "selected_format": "checklist",
            "refiner_intent": "modify_specific",
            "target_criterion": 3,
            "modification_details": "more specific about error handling",
            "chat_history": [],
            "refinement_count": 1,
        }

        result = await modifier_node(state)

        assert "Now more specific about error handling" in result["generated_ac"]
        assert result["refinement_count"] == 2
        assert result["current_agent"] == "modifier"

    @pytest.mark.asyncio
    @patch("src.agents.modifier.get_llm_provider")
    @patch("src.agents.modifier.format_prompt")
    async def test_modifier_node_adds_criterion(
        self, mock_format_prompt, mock_get_provider
    ):
        """Modifier adds a new criterion."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = (
            "- [ ] Criterion 1\n"
            "- [ ] Criterion 2\n"
            "- [ ] Criterion 3: Error handling for network failures"
        )
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Criterion 1\n- [ ] Criterion 2",
            "selected_format": "checklist",
            "refiner_intent": "add_criterion",
            "target_criterion": None,
            "modification_details": "error handling",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await modifier_node(state)

        assert "Criterion 3" in result["generated_ac"]
        assert "Error handling" in result["generated_ac"]

    @pytest.mark.asyncio
    async def test_modifier_node_no_ac(self):
        """Modifier handles missing AC."""
        state = {
            "generated_ac": None,
            "selected_format": "checklist",
            "refiner_intent": "modify_specific",
            "target_criterion": 1,
            "modification_details": "change",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await modifier_node(state)

        assert result["error"] == "No acceptance criteria to modify"
        assert result["current_agent"] == "modifier"

    @pytest.mark.asyncio
    @patch("src.agents.modifier.get_llm_provider")
    @patch("src.agents.modifier.format_prompt")
    async def test_modifier_node_clears_modification_fields(
        self, mock_format_prompt, mock_get_provider
    ):
        """Modifier clears modification-specific fields after processing."""
        mock_model = AsyncMock()
        mock_model.ainvoke.return_value.content = "- [ ] Updated criterion"
        mock_get_provider.return_value.get_main_model.return_value = mock_model
        mock_format_prompt.return_value = "test prompt"

        state = {
            "generated_ac": "- [ ] Original",
            "selected_format": "checklist",
            "refiner_intent": "modify_specific",
            "target_criterion": 1,
            "modification_details": "details",
            "chat_history": [],
            "refinement_count": 0,
        }

        result = await modifier_node(state)

        assert result["target_criterion"] is None
        assert result["modification_details"] == ""


class TestRefinerResponse:
    """Tests for RefinerResponse Pydantic model."""

    def test_valid_modify_specific_response(self):
        """Parse valid modify_specific response."""
        response = RefinerResponse(
            intent="modify_specific",
            target_criterion=3,
            modification_details="more specific",
            reasoning="User wants to modify criterion 3"
        )

        assert response.intent == "modify_specific"
        assert response.target_criterion == 3
        assert response.modification_details == "more specific"

    def test_valid_change_format_response(self):
        """Parse valid change_format response."""
        response = RefinerResponse(
            intent="change_format",
            new_format="bdd",
            reasoning="User wants BDD format"
        )

        assert response.intent == "change_format"
        assert response.new_format == "bdd"

    def test_valid_approve_response(self):
        """Parse valid approve response."""
        response = RefinerResponse(
            intent="approve",
            reasoning="User is satisfied"
        )

        assert response.intent == "approve"

    def test_default_values(self):
        """Check default values."""
        response = RefinerResponse(
            intent="approve",
            reasoning="Done"
        )

        assert response.target_criterion is None
        assert response.modification_details == ""
        assert response.new_format is None
        assert response.regeneration_context is None
        assert response.clarification_question is None
