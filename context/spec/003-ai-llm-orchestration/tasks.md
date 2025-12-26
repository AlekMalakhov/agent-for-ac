# Implementation Tasks: AI/LLM Orchestration

## Phase 1: Foundation & Configuration

- [x] **Task 1.1: Add new dependencies to pyproject.toml**
  - Add `langgraph>=0.0.40`
  - Add `langchain-anthropic>=0.1.0`
  - Add `langchain-aws>=0.1.0`
  - Run `uv sync` to install

- [x] **Task 1.2: Update configuration (settings.py and .env.example)**
  - Add LLM provider settings (`llm_provider`, `anthropic_api_key`, AWS credentials)
  - Add model configuration settings (`llm_model_orchestrator`, `llm_model_main`)
  - Update `.env.example` with new variables

- [x] **Task 1.3: Create agents module directory structure**
  - Create `src/agents/__init__.py`
  - Create `src/agents/llm/__init__.py`
  - Create `src/agents/prompts/` directory

## Phase 2: LLM Provider Layer

- [x] **Task 2.1: Implement LLM provider abstraction**
  - Create `src/agents/llm/provider.py` with abstract `LLMProvider` class
  - Implement `get_llm_provider()` factory function

- [x] **Task 2.2: Implement Anthropic provider**
  - Create `src/agents/llm/anthropic.py`
  - Implement `AnthropicProvider` class with `get_orchestrator_model()` and `get_main_model()`

- [x] **Task 2.3: Implement Bedrock provider**
  - Create `src/agents/llm/bedrock.py`
  - Implement `BedrockProvider` class with `get_orchestrator_model()` and `get_main_model()`

## Phase 3: State & Prompts

- [x] **Task 3.1: Create state schema**
  - Create `src/agents/state.py`
  - Define `AgentState` TypedDict
  - Define `EvaluationResult` Pydantic model

- [x] **Task 3.2: Create prompt templates**
  - Create `src/agents/prompts/orchestrator.txt`
  - Create `src/agents/prompts/information_gatherer.txt`
  - Create `src/agents/prompts/generator.txt`
  - Create `src/agents/prompts/evaluator.txt`

- [x] **Task 3.3: Create prompt loader utility**
  - Create helper function to load and format prompt templates
  - Handle file not found errors gracefully

## Phase 4: Agent Implementations

- [x] **Task 4.1: Implement Orchestrator Agent**
  - Create `src/agents/orchestrator.py`
  - Implement `orchestrator_node()` function
  - Parse JSON response to determine `needs_more_info`

- [x] **Task 4.2: Implement Information Gatherer Agent**
  - Create `src/agents/information_gatherer.py`
  - Implement `gatherer_node()` function
  - Handle question generation and reformulation logic

- [x] **Task 4.3: Implement Generator Agent**
  - Create `src/agents/generator.py`
  - Implement `generator_node()` function
  - Support checklist, BDD, and free formats

- [x] **Task 4.4: Implement Evaluator Agent**
  - Create `src/agents/evaluator.py`
  - Implement `evaluator_node()` function
  - Parse evaluation response with score and feedback

## Phase 5: Workflow & Integration

- [x] **Task 5.1: Create LangGraph workflow**
  - Create `src/agents/workflow.py`
  - Implement `create_ac_workflow()` function
  - Define routing functions for conditional edges

- [x] **Task 5.2: Update Slack command handler**
  - Modify `src/slack/handlers/commands.py`
  - Replace placeholder AC generation with agent workflow
  - Add format preference selection via Slack interactive components

- [x] **Task 5.3: Implement user approval workflow**
  - Add Slack interactive buttons for "Approve & Save to Jira", "Regenerate", "Cancel"
  - Handle button click events
  - Update Jira on approval

## Phase 6: Testing

- [x] **Task 6.1: Create unit tests for LLM providers**
  - Test provider factory function
  - Test model instantiation with mocked credentials

- [x] **Task 6.2: Create unit tests for agents**
  - Test each agent node with mocked LLM responses
  - Test response parsing functions

- [x] **Task 6.3: Create integration tests for workflow**
  - Test full workflow execution with mocked LLM
  - Test routing logic and state transitions
