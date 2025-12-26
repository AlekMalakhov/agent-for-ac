#!/usr/bin/env python3
"""
Test script for AI/LLM Orchestration

This script tests the complete AI agent workflow:
1. LLM provider configuration (Anthropic or Bedrock)
2. Individual agent functionality (Orchestrator, Generator, Evaluator)
3. LangGraph workflow integration
4. End-to-end AC generation

Usage:
    # Run all tests
    uv run python test_ai_orchestration.py

    # Run with real LLM (requires API key in .env)
    USE_REAL_LLM=true uv run python test_ai_orchestration.py

    # Run specific test
    uv run python test_ai_orchestration.py --test workflow
"""

import asyncio
import json
import os
import sys
from typing import Literal

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"✅ {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"❌ {text}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"ℹ️  {text}")


async def test_configuration() -> bool:
    """Test 1: Configuration and Environment Variables."""
    print_header("Test 1: Configuration & Environment Variables")

    try:
        from src.config.settings import get_settings

        settings = get_settings()

        print_info(f"LLM Provider: {settings.llm_provider}")
        print_info(f"Orchestrator Model: {settings.llm_model_orchestrator}")
        print_info(f"Main Model: {settings.llm_model_main}")

        # Check if API keys are configured
        if settings.llm_provider == "anthropic":
            if settings.anthropic_api_key:
                key_preview = settings.anthropic_api_key.get_secret_value()[:10] + "..."
                print_info(f"Anthropic API Key: {key_preview}")
            else:
                print_error("Anthropic API key not configured")
                return False
        elif settings.llm_provider == "bedrock":
            if settings.aws_region:
                print_info(f"AWS Region: {settings.aws_region}")
            else:
                print_error("AWS region not configured")
                return False

        print_success("Configuration loaded successfully")
        return True

    except Exception as e:
        print_error(f"Configuration test failed: {e}")
        return False


async def test_llm_providers() -> bool:
    """Test 2: LLM Provider Factory and Model Instantiation."""
    print_header("Test 2: LLM Provider Factory")

    try:
        from src.agents.llm import get_llm_provider
        from src.config.settings import get_settings

        settings = get_settings()
        provider = get_llm_provider()

        print_info(f"Provider type: {type(provider).__name__}")

        # Test orchestrator model
        try:
            orch_model = provider.get_orchestrator_model()
            print_success(f"Orchestrator model created: {type(orch_model).__name__}")
        except Exception as e:
            print_error(f"Failed to create orchestrator model: {e}")
            return False

        # Test main model
        try:
            main_model = provider.get_main_model()
            print_success(f"Main model created: {type(main_model).__name__}")
        except Exception as e:
            print_error(f"Failed to create main model: {e}")
            return False

        print_success("LLM provider tests passed")
        return True

    except Exception as e:
        print_error(f"LLM provider test failed: {e}")
        return False


async def test_agent_state() -> bool:
    """Test 3: Agent State Management."""
    print_header("Test 3: Agent State Management")

    try:
        from src.agents.workflow import create_initial_state

        state = create_initial_state(
            ticket_key="TEST-123",
            ticket_title="Test Ticket",
            ticket_description="This is a test ticket description",
            ticket_type="Story",
            ticket_url="https://example.atlassian.net/browse/TEST-123",
            user_id="U12345",
            selected_format="checklist",
        )

        # Verify required fields
        required_fields = [
            "ticket_key", "ticket_title", "ticket_description", "ticket_type",
            "ticket_url", "user_id", "selected_format", "gathered_information",
            "questions_asked", "generation_attempts", "is_complete"
        ]

        for field in required_fields:
            if field not in state:
                print_error(f"Missing required field: {field}")
                return False

        print_info(f"Ticket Key: {state['ticket_key']}")
        print_info(f"Format: {state['selected_format']}")
        print_info(f"Questions Asked: {state['questions_asked']}")
        print_info(f"Generation Attempts: {state['generation_attempts']}")

        print_success("Agent state created successfully")
        return True

    except Exception as e:
        print_error(f"Agent state test failed: {e}")
        return False


async def test_workflow_routing() -> bool:
    """Test 4: Workflow Routing Logic."""
    print_header("Test 4: Workflow Routing Logic")

    try:
        from src.agents.workflow import (
            route_from_orchestrator,
            route_from_gatherer,
            route_from_evaluator,
        )

        # Test orchestrator routing
        print_info("Testing orchestrator routing...")

        # Should route to gatherer when info needed
        result = route_from_orchestrator({"error": None, "needs_more_info": True})
        if result != "gatherer":
            print_error(f"Expected 'gatherer', got '{result}'")
            return False

        # Should route to generator when info sufficient
        result = route_from_orchestrator({"error": None, "needs_more_info": False})
        if result != "generator":
            print_error(f"Expected 'generator', got '{result}'")
            return False

        print_success("Orchestrator routing works")

        # Test gatherer routing
        print_info("Testing gatherer routing...")

        # Should wait when question pending
        result = route_from_gatherer({
            "current_question": "What is the scope?",
            "questions_asked": 1,
            "needs_more_info": True,
        })
        if result != "wait_for_answer":
            print_error(f"Expected 'wait_for_answer', got '{result}'")
            return False

        print_success("Gatherer routing works")

        # Test evaluator routing
        print_info("Testing evaluator routing...")

        # Should end on high score
        result = route_from_evaluator({"quality_score": 8, "generation_attempts": 1})
        if result != "end":
            print_error(f"Expected 'end', got '{result}'")
            return False

        # Should retry on low score
        result = route_from_evaluator({"quality_score": 5, "generation_attempts": 1})
        if result != "generator":
            print_error(f"Expected 'generator', got '{result}'")
            return False

        print_success("Evaluator routing works")

        print_success("All routing logic tests passed")
        return True

    except Exception as e:
        print_error(f"Workflow routing test failed: {e}")
        return False


async def test_workflow_with_mocks() -> bool:
    """Test 5: Complete Workflow with Mocked LLM."""
    print_header("Test 5: Complete Workflow (Mocked LLM)")

    try:
        from unittest.mock import AsyncMock, patch
        from src.agents.workflow import create_ac_workflow, create_initial_state

        print_info("Setting up mocked LLM responses...")

        # Mock orchestrator response
        with patch("src.agents.orchestrator.get_llm_provider") as mock_orch_provider, \
             patch("src.agents.orchestrator.format_prompt") as mock_orch_prompt, \
             patch("src.agents.generator.get_llm_provider") as mock_gen_provider, \
             patch("src.agents.generator.format_prompt") as mock_gen_prompt, \
             patch("src.agents.evaluator.get_llm_provider") as mock_eval_provider, \
             patch("src.agents.evaluator.format_prompt") as mock_eval_prompt:

            # Orchestrator says info is sufficient
            mock_orch_model = AsyncMock()
            mock_orch_model.ainvoke.return_value.content = json.dumps({
                "sufficient_information": True,
                "missing_information": [],
                "reasoning": "Ticket has complete information"
            })
            mock_orch_provider.return_value.get_orchestrator_model.return_value = mock_orch_model

            # Generator produces AC
            mock_gen_model = AsyncMock()
            mock_gen_model.ainvoke.return_value.content = """- [ ] User can log in with email and password
- [ ] User receives error message on invalid credentials
- [ ] User is redirected to dashboard on successful login
- [ ] Session expires after 24 hours of inactivity"""
            mock_gen_provider.return_value.get_main_model.return_value = mock_gen_model

            # Evaluator gives high score
            mock_eval_model = AsyncMock()
            mock_eval_model.ainvoke.return_value.content = json.dumps({
                "score": 8,
                "feedback": "Clear and comprehensive acceptance criteria",
                "strengths": ["Clear expectations", "Covers success and error cases"],
                "improvements": ["Could add more edge cases"]
            })
            mock_eval_provider.return_value.get_main_model.return_value = mock_eval_model

            print_info("Creating workflow...")
            workflow = create_ac_workflow()

            print_info("Creating initial state...")
            initial_state = create_initial_state(
                ticket_key="TEST-456",
                ticket_title="Implement User Login",
                ticket_description="As a user, I want to log in to the system so that I can access my account.",
                ticket_type="Story",
                ticket_url="https://example.atlassian.net/browse/TEST-456",
                user_id="U12345",
                selected_format="checklist",
            )

            print_info("Running workflow...")
            result = await workflow.ainvoke(initial_state)

            # Verify results
            if not result.get("generated_ac"):
                print_error("No acceptance criteria generated")
                return False

            if result.get("quality_score", 0) < 7:
                print_error(f"Quality score too low: {result.get('quality_score')}")
                return False

            if not result.get("is_complete"):
                print_error("Workflow did not complete")
                return False

            print_info(f"\n📋 Generated AC:\n{result['generated_ac']}")
            print_info(f"\n⭐ Quality Score: {result['quality_score']}/10")
            print_info(f"📝 Feedback: {result.get('evaluation_feedback', 'N/A')}")

            print_success("Workflow completed successfully with mocked LLM")
            return True

    except Exception as e:
        print_error(f"Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_workflow_with_real_llm() -> bool:
    """Test 6: Complete Workflow with Real LLM."""
    print_header("Test 6: Complete Workflow (Real LLM)")

    # Check if we should run this test
    if not os.getenv("USE_REAL_LLM"):
        print_info("Skipping real LLM test (set USE_REAL_LLM=true to enable)")
        return True

    try:
        from src.agents.workflow import create_ac_workflow, create_initial_state

        print_info("⚠️  This will make real API calls to the LLM provider")
        print_info("Creating workflow with real LLM...")

        workflow = create_ac_workflow()

        initial_state = create_initial_state(
            ticket_key="TEST-REAL",
            ticket_title="Add Password Reset Feature",
            ticket_description="""As a user who forgot my password, I want to reset it via email
            so that I can regain access to my account. The system should send a reset link to
            my registered email address.""",
            ticket_type="Story",
            ticket_url="https://example.atlassian.net/browse/TEST-REAL",
            user_id="U12345",
            selected_format="bdd",
        )

        print_info("Running workflow with real LLM (this may take 10-30 seconds)...")
        result = await workflow.ainvoke(initial_state)

        # Display results
        print_info(f"\n{'─' * 70}")
        print_info("📋 GENERATED ACCEPTANCE CRITERIA:")
        print_info(f"{'─' * 70}")
        print(result.get('generated_ac', 'No AC generated'))

        print_info(f"\n{'─' * 70}")
        print_info(f"⭐ QUALITY SCORE: {result.get('quality_score', 'N/A')}/10")
        print_info(f"{'─' * 70}")

        if result.get('evaluation_feedback'):
            print_info(f"\n📝 EVALUATOR FEEDBACK:")
            print(result.get('evaluation_feedback'))

        print_info(f"\n📊 WORKFLOW STATS:")
        print_info(f"  - Generation attempts: {result.get('generation_attempts', 0)}")
        print_info(f"  - Questions asked: {result.get('questions_asked', 0)}")
        print_info(f"  - Workflow complete: {result.get('is_complete', False)}")

        if result.get('is_complete') and result.get('quality_score', 0) >= 7:
            print_success("Real LLM workflow completed successfully!")
            return True
        else:
            print_error("Real LLM workflow did not meet success criteria")
            return False

    except Exception as e:
        print_error(f"Real LLM workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_prompt_templates() -> bool:
    """Test 7: Prompt Templates Loading."""
    print_header("Test 7: Prompt Templates")

    try:
        import os
        from pathlib import Path

        prompt_dir = Path(__file__).parent / "src" / "agents" / "prompts"

        required_prompts = [
            "orchestrator.txt",
            "information_gatherer.txt",
            "generator.txt",
            "evaluator.txt",
        ]

        for prompt_file in required_prompts:
            prompt_path = prompt_dir / prompt_file
            if not prompt_path.exists():
                print_error(f"Missing prompt template: {prompt_file}")
                return False

            # Check file is not empty
            content = prompt_path.read_text()
            if len(content.strip()) < 50:
                print_error(f"Prompt template too short: {prompt_file}")
                return False

            print_success(f"Found {prompt_file} ({len(content)} chars)")

        print_success("All prompt templates exist and are valid")
        return True

    except Exception as e:
        print_error(f"Prompt template test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests in sequence."""
    print_header("🧪 AI/LLM Orchestration Test Suite")
    print_info("Testing Agent for AC - AI/LLM Orchestration System")
    print_info("=" * 70)

    tests = [
        ("Configuration", test_configuration),
        ("LLM Providers", test_llm_providers),
        ("Agent State", test_agent_state),
        ("Workflow Routing", test_workflow_routing),
        ("Prompt Templates", test_prompt_templates),
        ("Workflow (Mocked)", test_workflow_with_mocks),
        ("Workflow (Real LLM)", test_workflow_with_real_llm),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print_error(f"Unexpected error in {test_name}: {e}")
            results[test_name] = False

    # Summary
    print_header("📊 Test Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test_name}")

    print(f"\n{'─' * 70}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'─' * 70}\n")

    if passed == total:
        print_success("🎉 All tests passed!")
        return 0
    else:
        print_error(f"⚠️  {total - passed} test(s) failed")
        return 1


def main():
    """Main entry point."""
    import sys

    # Check for specific test
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        if len(sys.argv) < 3:
            print_error("Usage: test_ai_orchestration.py --test <test_name>")
            return 1

        test_name = sys.argv[2]
        test_map = {
            "config": test_configuration,
            "providers": test_llm_providers,
            "state": test_agent_state,
            "routing": test_workflow_routing,
            "prompts": test_prompt_templates,
            "workflow": test_workflow_with_mocks,
            "real": test_workflow_with_real_llm,
        }

        if test_name not in test_map:
            print_error(f"Unknown test: {test_name}")
            print_info(f"Available tests: {', '.join(test_map.keys())}")
            return 1

        result = asyncio.run(test_map[test_name]())
        return 0 if result else 1

    # Run all tests
    return asyncio.run(run_all_tests())


if __name__ == "__main__":
    sys.exit(main())
