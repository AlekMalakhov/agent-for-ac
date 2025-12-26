# Technical Specification: AI/LLM Orchestration for AC Generation

- **Functional Specification:** `context/spec/003-ai-llm-orchestration/functional-spec.md`
- **Status:** Draft
- **Author(s):** Engineering Team

---

## 1. High-Level Technical Approach

This specification describes the implementation of a multi-agent AI system for generating and evaluating acceptance criteria. The system uses **LangGraph** for agent orchestration with support for two LLM providers: **AWS Bedrock** and **Anthropic API**.

**Key Decisions:**
- **LangGraph** state machine for multi-agent workflow orchestration
- **In-memory state** during conversation (stateless between sessions)
- **Provider abstraction** to support AWS Bedrock and direct Anthropic API
- **Claude 3.5 Haiku** for Orchestrator (fast, cheap decisions)
- **Claude 3.7 Sonnet** for Generator, Evaluator, and Information Gatherer (higher quality)
- **File-based prompts** for easy editing and version control

---

## 2. Proposed Solution & Implementation Plan (The "How")

### 2.1 New Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...
    "langgraph>=0.0.40",
    "langchain-anthropic>=0.1.0",
    "langchain-aws>=0.1.0",
]
```

### 2.2 New Directory Structure

```
src/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py          # Orchestrator Agent
│   ├── information_gatherer.py  # Information Gatherer Agent
│   ├── generator.py             # Generator Agent
│   ├── evaluator.py             # Evaluator Agent
│   ├── workflow.py              # LangGraph workflow definition
│   ├── state.py                 # Shared state schema
│   ├── prompts/
│   │   ├── orchestrator.txt
│   │   ├── information_gatherer.txt
│   │   ├── generator.txt
│   │   └── evaluator.txt
│   └── llm/
│       ├── __init__.py
│       ├── provider.py          # Abstract LLM provider interface
│       ├── bedrock.py           # AWS Bedrock implementation
│       └── anthropic.py         # Anthropic API implementation
```

### 2.3 Configuration Changes

Update `src/config/settings.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # LLM Configuration
    llm_provider: Literal["bedrock", "anthropic"] = "anthropic"

    # Anthropic API (when llm_provider = "anthropic")
    anthropic_api_key: SecretStr | None = None

    # AWS Bedrock (when llm_provider = "bedrock")
    aws_access_key_id: str | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_region: str = "us-east-1"

    # Model Configuration
    llm_model_orchestrator: str = "claude-3-5-haiku-20241022"
    llm_model_main: str = "claude-3-7-sonnet-20250219"
```

Update `.env.example`:

```bash
# LLM Configuration
LLM_PROVIDER=anthropic  # "anthropic" or "bedrock"

# Anthropic API (if LLM_PROVIDER=anthropic)
ANTHROPIC_API_KEY=sk-ant-...

# AWS Bedrock (if LLM_PROVIDER=bedrock)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Model Configuration (optional, defaults shown)
LLM_MODEL_ORCHESTRATOR=claude-3-5-haiku-20241022
LLM_MODEL_MAIN=claude-3-7-sonnet-20250219
```

### 2.4 State Schema

`src/agents/state.py`:

```python
from typing import TypedDict, Literal
from pydantic import BaseModel

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
    gathered_information: list[dict]  # Q&A history
    questions_asked: int
    reformulation_attempts: int

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


class EvaluationResult(BaseModel):
    """Result from Evaluator Agent."""
    score: int  # 1-10
    feedback: str
    strengths: list[str]
    improvements: list[str]
```

### 2.5 LLM Provider Abstraction

`src/agents/llm/provider.py`:

```python
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel

class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    def get_orchestrator_model(self) -> BaseChatModel:
        """Get model for Orchestrator (fast, cheap)."""
        pass

    @abstractmethod
    def get_main_model(self) -> BaseChatModel:
        """Get model for Generator/Evaluator/Gatherer (high quality)."""
        pass


def get_llm_provider() -> LLMProvider:
    """Factory function to get configured LLM provider."""
    settings = get_settings()

    if settings.llm_provider == "anthropic":
        from src.agents.llm.anthropic import AnthropicProvider
        return AnthropicProvider()
    elif settings.llm_provider == "bedrock":
        from src.agents.llm.bedrock import BedrockProvider
        return BedrockProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

`src/agents/llm/anthropic.py`:

```python
from langchain_anthropic import ChatAnthropic
from src.config.settings import get_settings

class AnthropicProvider(LLMProvider):
    def get_orchestrator_model(self) -> BaseChatModel:
        settings = get_settings()
        return ChatAnthropic(
            model=settings.llm_model_orchestrator,
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=1024,
        )

    def get_main_model(self) -> BaseChatModel:
        settings = get_settings()
        return ChatAnthropic(
            model=settings.llm_model_main,
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_tokens=4096,
        )
```

`src/agents/llm/bedrock.py`:

```python
from langchain_aws import ChatBedrock
from src.config.settings import get_settings

class BedrockProvider(LLMProvider):
    def get_orchestrator_model(self) -> BaseChatModel:
        settings = get_settings()
        return ChatBedrock(
            model_id=f"anthropic.{settings.llm_model_orchestrator}",
            region_name=settings.aws_region,
            credentials_profile_name=None,  # Uses env vars
            model_kwargs={"max_tokens": 1024},
        )

    def get_main_model(self) -> BaseChatModel:
        settings = get_settings()
        return ChatBedrock(
            model_id=f"anthropic.{settings.llm_model_main}",
            region_name=settings.aws_region,
            credentials_profile_name=None,
            model_kwargs={"max_tokens": 4096},
        )
```

### 2.6 LangGraph Workflow

`src/agents/workflow.py`:

```python
from langgraph.graph import StateGraph, END
from src.agents.state import AgentState
from src.agents.orchestrator import orchestrator_node
from src.agents.information_gatherer import gatherer_node
from src.agents.generator import generator_node
from src.agents.evaluator import evaluator_node

def create_ac_workflow() -> StateGraph:
    """Create the AC generation workflow graph."""

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
        }
    )

    # Gatherer routing
    workflow.add_conditional_edges(
        "gatherer",
        route_from_gatherer,
        {
            "gatherer": "gatherer",  # Continue asking
            "generator": "generator",  # Enough info
            "end": END,  # Needs clarification
        }
    )

    # Generator -> Evaluator
    workflow.add_edge("generator", "evaluator")

    # Evaluator routing
    workflow.add_conditional_edges(
        "evaluator",
        route_from_evaluator,
        {
            "generator": "generator",  # Retry (score < 7)
            "end": END,  # Success or max attempts
        }
    )

    return workflow.compile()


def route_from_orchestrator(state: AgentState) -> str:
    if state.get("error"):
        return "end"
    if state["needs_more_info"]:
        return "gatherer"
    return "generator"


def route_from_gatherer(state: AgentState) -> str:
    if state["questions_asked"] >= 5:
        return "generator" if not state["needs_more_info"] else "end"
    if state["needs_more_info"]:
        return "gatherer"
    return "generator"


def route_from_evaluator(state: AgentState) -> str:
    score = state.get("quality_score", 0)
    attempts = state.get("generation_attempts", 0)

    if score >= 7 or attempts >= 2:
        return "end"
    return "generator"
```

### 2.7 Agent Implementations

**Orchestrator Agent** (`src/agents/orchestrator.py`):

```python
async def orchestrator_node(state: AgentState) -> AgentState:
    """
    Analyzes ticket content and decides if more information is needed.
    Uses Claude 3.5 Haiku for fast, cheap decisions.
    """
    provider = get_llm_provider()
    model = provider.get_orchestrator_model()

    prompt = load_prompt("orchestrator.txt")

    response = await model.ainvoke(
        prompt.format(
            title=state["ticket_title"],
            description=state["ticket_description"],
            ticket_type=state["ticket_type"],
        )
    )

    # Parse response to determine if more info needed
    needs_more_info = parse_orchestrator_decision(response.content)

    return {
        **state,
        "needs_more_info": needs_more_info,
        "current_agent": "orchestrator",
    }
```

**Information Gatherer Agent** (`src/agents/information_gatherer.py`):

```python
async def gatherer_node(state: AgentState) -> AgentState:
    """
    Asks clarifying questions one at a time.
    Max 5 questions, max 3 reformulations per question.
    """
    provider = get_llm_provider()
    model = provider.get_main_model()

    prompt = load_prompt("information_gatherer.txt")

    response = await model.ainvoke(
        prompt.format(
            title=state["ticket_title"],
            description=state["ticket_description"],
            gathered_info=state["gathered_information"],
            questions_asked=state["questions_asked"],
        )
    )

    # Returns: question to ask, or signal that info is sufficient
    question, is_sufficient = parse_gatherer_response(response.content)

    return {
        **state,
        "current_question": question,
        "needs_more_info": not is_sufficient,
        "questions_asked": state["questions_asked"] + (1 if question else 0),
        "current_agent": "gatherer",
    }
```

**Generator Agent** (`src/agents/generator.py`):

```python
async def generator_node(state: AgentState) -> AgentState:
    """
    Generates acceptance criteria based on gathered context.
    Uses selected format (checklist, BDD, free).
    """
    provider = get_llm_provider()
    model = provider.get_main_model()

    prompt = load_prompt("generator.txt")

    # Include evaluator feedback if retrying
    feedback = state.get("evaluator_feedback", "")

    response = await model.ainvoke(
        prompt.format(
            title=state["ticket_title"],
            description=state["ticket_description"],
            gathered_info=state["gathered_information"],
            format=state["selected_format"] or "checklist",
            previous_feedback=feedback,
        )
    )

    return {
        **state,
        "generated_ac": response.content,
        "generation_attempts": state.get("generation_attempts", 0) + 1,
        "current_agent": "generator",
    }
```

**Evaluator Agent** (`src/agents/evaluator.py`):

```python
async def evaluator_node(state: AgentState) -> AgentState:
    """
    Evaluates AC quality (clarity, structure, formulation).
    Returns score 1-10 and actionable feedback.
    """
    provider = get_llm_provider()
    model = provider.get_main_model()

    prompt = load_prompt("evaluator.txt")

    response = await model.ainvoke(
        prompt.format(
            acceptance_criteria=state["generated_ac"],
            format=state["selected_format"],
        )
    )

    # Parse structured evaluation result
    evaluation = parse_evaluation_response(response.content)

    return {
        **state,
        "quality_score": evaluation.score,
        "evaluator_feedback": evaluation.feedback,
        "current_agent": "evaluator",
        "is_complete": evaluation.score >= 7 or state["generation_attempts"] >= 2,
    }
```

### 2.8 Integration with Slack Handler

Update `src/slack/handlers/commands.py`:

```python
from src.agents.workflow import create_ac_workflow
from src.agents.state import AgentState

async def handle_jira_ticket(say, ticket_input: str, user_id: str) -> None:
    """Handle Jira ticket processing with AI agents."""

    jira_service = await get_jira_service()
    ticket = await jira_service.get_ticket(ticket_input)

    # Ask for AC format preference
    format_choice = await ask_format_preference(say)

    # Initialize workflow state
    initial_state: AgentState = {
        "ticket_key": ticket.key,
        "ticket_title": ticket.title,
        "ticket_description": ticket.description,
        "ticket_type": ticket.ticket_type,
        "ticket_url": ticket.url,
        "user_id": user_id,
        "gathered_information": [],
        "questions_asked": 0,
        "reformulation_attempts": 0,
        "selected_format": format_choice,
        "generated_ac": None,
        "generation_attempts": 0,
        "quality_score": None,
        "evaluator_feedback": None,
        "current_agent": "orchestrator",
        "needs_more_info": False,
        "is_complete": False,
        "error": None,
    }

    # Run workflow
    workflow = create_ac_workflow()
    final_state = await run_workflow_with_interaction(
        workflow, initial_state, say
    )

    # Show result and ask for approval
    if final_state["generated_ac"]:
        await show_result_and_ask_approval(say, final_state, jira_service)
```

### 2.9 Prompt Templates

`src/agents/prompts/orchestrator.txt`:

```
You are an AI assistant that analyzes Jira tickets to determine if there is sufficient information to generate high-quality acceptance criteria.

Ticket Title: {title}
Ticket Type: {ticket_type}
Ticket Description:
{description}

Analyze this ticket and determine:
1. Is there enough information to generate clear, testable acceptance criteria?
2. What key information is missing (if any)?

Respond in JSON format:
{
  "sufficient_information": true/false,
  "missing_information": ["list of missing details"],
  "reasoning": "brief explanation"
}
```

`src/agents/prompts/information_gatherer.txt`:

```
You are an AI assistant helping to gather information for writing acceptance criteria.

Ticket Title: {title}
Ticket Description:
{description}

Information gathered so far:
{gathered_info}

Questions asked so far: {questions_asked}/5

Your task:
1. Analyze what information is still missing
2. Generate ONE clarifying question to ask the user
3. The question should be specific and help clarify requirements

Respond in JSON format:
{
  "sufficient_information": true/false,
  "question": "your question here (or null if sufficient)",
  "reasoning": "why this information is needed"
}

If you have enough information, set sufficient_information to true and question to null.
```

`src/agents/prompts/generator.txt`:

```
You are an expert at writing clear, testable acceptance criteria for software development tickets.

Ticket Title: {title}
Ticket Description:
{description}

Additional Context from Q&A:
{gathered_info}

Requested Format: {format}

{previous_feedback}

Generate comprehensive acceptance criteria in the requested format.

For "checklist" format, use:
- [ ] Criterion 1
- [ ] Criterion 2

For "bdd" format, use:
Given [context]
When [action]
Then [expected result]

For "free" format, use clear prose with testable statements.

Requirements:
- Write in English
- Include edge cases and error scenarios
- Make each criterion testable
- Be specific and unambiguous
```

`src/agents/prompts/evaluator.txt`:

```
You are an expert at evaluating the quality of acceptance criteria for software development.

Acceptance Criteria to Evaluate:
{acceptance_criteria}

Expected Format: {format}

Evaluate the acceptance criteria on the following dimensions:
1. Clarity - Are the criteria easy to understand?
2. Structure - Is the format correct and consistent?
3. Testability - Can each criterion be verified?
4. Completeness - Are edge cases and errors covered?
5. Specificity - Are the criteria unambiguous?

Provide a score from 1-10 and specific feedback.

Respond in JSON format:
{
  "score": 7,
  "feedback": "Overall assessment",
  "strengths": ["list of strong points"],
  "improvements": ["specific suggestions for improvement"]
}
```

---

## 3. Impact and Risk Analysis

### System Dependencies

| Component | Depends On | Affected By |
|-----------|------------|-------------|
| Agents Module | LLM Provider, Settings | LLM API changes |
| Slack Handler | Agents Module, Jira Service | Workflow changes |
| Settings | Environment Variables | New LLM config |

### Potential Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API rate limits | Blocked requests | Implement retry with exponential backoff |
| LLM API downtime | Service unavailable | Log errors, notify user, graceful degradation |
| High LLM costs | Budget overrun | Monitor token usage, use Haiku for Orchestrator |
| Slow response times | Poor UX | Show progress messages in Slack |
| Poor AC quality | User dissatisfaction | Evaluator feedback loop, max 2 retries |
| Invalid prompt responses | Parsing errors | Structured output parsing with fallbacks |

---

## 4. Testing Strategy

### Unit Tests

- **LLM Provider:** Mock LLM responses, test provider switching
- **State Management:** Test state transitions and validation
- **Prompt Loading:** Test prompt file loading and formatting
- **Response Parsing:** Test JSON/structured response parsing

### Integration Tests

- **Workflow Execution:** Test full workflow with mocked LLM
- **Agent Routing:** Test conditional routing logic
- **Slack Integration:** Test message formatting and interactive components

### End-to-End Tests

- **Happy Path:** Ticket -> AC generation -> Approval -> Jira update
- **Insufficient Info:** Ticket -> Q&A -> AC generation
- **Low Quality Retry:** Generation -> Low score -> Retry -> Success
- **Max Attempts:** Generation -> Retry -> Retry -> Show best result

### Test Configuration

```python
# tests/conftest.py
@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = Mock(spec=LLMProvider)
    provider.get_orchestrator_model.return_value = MockChatModel()
    provider.get_main_model.return_value = MockChatModel()
    return provider
```
