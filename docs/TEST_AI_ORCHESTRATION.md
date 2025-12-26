# Testing AI/LLM Orchestration

This guide explains how to test the AI/LLM orchestration system for Agent for AC.

## Overview

The AI orchestration system uses a multi-agent architecture with:
- **Orchestrator Agent** - Decides if information is sufficient
- **Information Gatherer Agent** - Asks clarifying questions
- **Generator Agent** - Creates acceptance criteria
- **Evaluator Agent** - Scores AC quality (1-10)

All agents work together in a LangGraph workflow.

---

## Quick Start

### 1. Test with Mock LLM (No API Key Required)

This tests the workflow logic without making real API calls:

```bash
uv run python test_ai_orchestration.py
```

**Expected Output:**
```
==========================================
Test 1: Configuration & Environment Variables
==========================================

ℹ️  LLM Provider: anthropic
ℹ️  Orchestrator Model: claude-3-5-haiku-20241022
ℹ️  Main Model: claude-3-7-sonnet-20250219
✅ Configuration loaded successfully

==========================================
Test 5: Complete Workflow (Mocked LLM)
==========================================

ℹ️  Setting up mocked LLM responses...
ℹ️  Creating workflow...
ℹ️  Running workflow...

📋 Generated AC:
- [ ] User can log in with email and password
- [ ] User receives error message on invalid credentials
- [ ] User is redirected to dashboard on successful login
- [ ] Session expires after 24 hours

⭐ Quality Score: 8/10
✅ Workflow completed successfully

📊 Test Summary
✅ PASS     Configuration
✅ PASS     LLM Providers
✅ PASS     Agent State
✅ PASS     Workflow Routing
✅ PASS     Prompt Templates
✅ PASS     Workflow (Mocked)
✅ PASS     Workflow (Real LLM) [SKIPPED]

Results: 6/7 tests passed
🎉 All tests passed!
```

### 2. Test with Real LLM (Requires API Key)

First, ensure you have API credentials configured in `.env`:

**For Anthropic:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

**For AWS Bedrock:**
```bash
LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

Then run:
```bash
USE_REAL_LLM=true uv run python test_ai_orchestration.py
```

**Expected Behavior:**
- Makes real API calls to Anthropic or AWS Bedrock
- Takes 10-30 seconds to complete
- Generates actual acceptance criteria
- Shows real quality evaluation

---

## Test Breakdown

### Test 1: Configuration & Environment Variables

**What it tests:** Configuration loading and environment variable validation

```bash
uv run python test_ai_orchestration.py --test config
```

**Checks:**
- ✅ Settings can be loaded
- ✅ LLM provider is configured
- ✅ Model names are set
- ✅ API keys exist (if applicable)

**Common Issues:**
- Missing `.env` file → Copy from `.env.example`
- Invalid `LLM_PROVIDER` → Must be "anthropic" or "bedrock"
- Missing API key → Add to `.env`

---

### Test 2: LLM Provider Factory

**What it tests:** LLM provider instantiation and model creation

```bash
uv run python test_ai_orchestration.py --test providers
```

**Checks:**
- ✅ Provider factory works
- ✅ Orchestrator model can be created
- ✅ Main model can be created

**Common Issues:**
- `ValueError: Unknown LLM provider` → Check `LLM_PROVIDER` in `.env`
- `ValueError: ANTHROPIC_API_KEY is required` → Add key to `.env`
- AWS credentials error → Configure AWS credentials

---

### Test 3: Agent State Management

**What it tests:** Agent state creation and structure

```bash
uv run python test_ai_orchestration.py --test state
```

**Checks:**
- ✅ State contains all required fields
- ✅ Initial values are correct
- ✅ State structure matches TypedDict

---

### Test 4: Workflow Routing Logic

**What it tests:** Conditional routing between agents

```bash
uv run python test_ai_orchestration.py --test routing
```

**Checks:**
- ✅ Orchestrator routes to gatherer when info needed
- ✅ Orchestrator routes to generator when info sufficient
- ✅ Gatherer routes to wait when question pending
- ✅ Gatherer routes to generator when done
- ✅ Evaluator routes to end on high score
- ✅ Evaluator routes to generator for retry on low score

---

### Test 5: Prompt Templates

**What it tests:** Prompt template files exist and are valid

```bash
uv run python test_ai_orchestration.py --test prompts
```

**Checks:**
- ✅ `orchestrator.txt` exists
- ✅ `information_gatherer.txt` exists
- ✅ `generator.txt` exists
- ✅ `evaluator.txt` exists
- ✅ All templates are non-empty

---

### Test 6: Complete Workflow (Mocked)

**What it tests:** Full workflow execution with mocked LLM responses

```bash
uv run python test_ai_orchestration.py --test workflow
```

**Workflow Steps:**
1. Orchestrator analyzes ticket → says info is sufficient
2. Generator creates acceptance criteria
3. Evaluator scores quality → gives 8/10
4. Workflow completes successfully

**Mocked LLM Responses:**
- Orchestrator: `{"sufficient_information": true, "reasoning": "..."}`
- Generator: Returns checklist-formatted AC
- Evaluator: `{"score": 8, "feedback": "...", "strengths": [...], "improvements": [...]}`

---

### Test 7: Complete Workflow (Real LLM)

**What it tests:** Full workflow with actual LLM API calls

```bash
USE_REAL_LLM=true uv run python test_ai_orchestration.py --test real
```

**What happens:**
1. Creates test ticket: "Add Password Reset Feature"
2. Sends to Orchestrator agent
3. Orchestrator decides if info is sufficient
4. If sufficient → Generator creates AC in BDD format
5. Evaluator scores the generated AC
6. Shows results with quality score and feedback

**Cost:** Small API cost (typically $0.01-0.05 per run)

**Sample Output:**
```
──────────────────────────────────────────────────────────────────────
📋 GENERATED ACCEPTANCE CRITERIA:
──────────────────────────────────────────────────────────────────────
**Given** a user who has forgotten their password
**When** they request a password reset
**Then** the system should send a reset link to their registered email

**Given** a user clicks the password reset link
**When** the link is valid and not expired
**Then** they should be able to set a new password

**Given** a user enters a new password
**When** the password meets security requirements
**Then** their password should be updated and they can log in

──────────────────────────────────────────────────────────────────────
⭐ QUALITY SCORE: 9/10
──────────────────────────────────────────────────────────────────────

📝 EVALUATOR FEEDBACK:
Strengths:
- Clear Given/When/Then format
- Covers main flow and edge cases
- Security requirements included

Improvements:
- Could add expired link scenario

📊 WORKFLOW STATS:
  - Generation attempts: 1
  - Questions asked: 0
  - Workflow complete: True
```

---

## Running Individual Components

### Test Orchestrator Only

```python
uv run python -c "
import asyncio
from src.agents.orchestrator import orchestrator_node
from src.agents.workflow import create_initial_state

async def test():
    state = create_initial_state(
        ticket_key='TEST-1',
        ticket_title='Add Login',
        ticket_description='User login feature',
        ticket_type='Story',
        ticket_url='https://example.com',
        user_id='U123'
    )
    result = await orchestrator_node(state)
    print(f'Needs more info: {result[\"needs_more_info\"]}')

asyncio.run(test())
"
```

### Test Generator Only

```python
uv run python -c "
import asyncio
from src.agents.generator import generator_node
from src.agents.workflow import create_initial_state

async def test():
    state = create_initial_state(
        ticket_key='TEST-1',
        ticket_title='Add Login',
        ticket_description='User can log in with email/password',
        ticket_type='Story',
        ticket_url='https://example.com',
        user_id='U123',
        selected_format='checklist'
    )
    state['needs_more_info'] = False
    result = await generator_node(state)
    print(f'Generated AC:\n{result[\"generated_ac\"]}')

asyncio.run(test())
"
```

### Test Evaluator Only

```python
uv run python -c "
import asyncio
from src.agents.evaluator import evaluator_node
from src.agents.workflow import create_initial_state

async def test():
    state = create_initial_state(
        ticket_key='TEST-1',
        ticket_title='Add Login',
        ticket_description='User login',
        ticket_type='Story',
        ticket_url='https://example.com',
        user_id='U123'
    )
    state['generated_ac'] = '''
- [ ] User can log in with email and password
- [ ] Error message shown on invalid credentials
- [ ] User redirected to dashboard on success
    '''
    result = await evaluator_node(state)
    print(f'Quality score: {result[\"quality_score\"]}/10')
    print(f'Feedback: {result[\"evaluation_feedback\"]}')

asyncio.run(test())
"
```

---

## Running Pytest Tests

The project includes unit tests using pytest:

### Run All Agent Tests

```bash
uv run pytest tests/unit/agents/ -v
```

### Run LLM Provider Tests

```bash
uv run pytest tests/unit/agents/test_llm_providers.py -v
```

### Run Workflow Tests

```bash
uv run pytest tests/unit/agents/test_workflow.py -v
```

**Expected Output:**
```
tests/unit/agents/test_llm_providers.py::TestLLMProviderInterface::test_llm_provider_is_abstract PASSED
tests/unit/agents/test_llm_providers.py::TestGetLLMProvider::test_returns_anthropic_provider PASSED
tests/unit/agents/test_llm_providers.py::TestAnthropicProvider::test_get_orchestrator_model PASSED
tests/unit/agents/test_workflow.py::TestRoutingFunctions::test_route_from_orchestrator PASSED
tests/unit/agents/test_workflow.py::TestWorkflowIntegration::test_happy_path PASSED

============== 15 passed in 2.5s ==============
```

---

## Troubleshooting

### Issue: Configuration Error

**Symptom:**
```
❌ Configuration test failed: ValidationError
```

**Solution:**
1. Ensure `.env` file exists: `ls -la .env`
2. Check required variables: `cat .env | grep LLM_PROVIDER`
3. Copy from example if missing: `cp .env.example .env`

---

### Issue: Provider Instantiation Failed

**Symptom:**
```
❌ Failed to create orchestrator model: ANTHROPIC_API_KEY is required
```

**Solution:**
1. Add API key to `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-...
   ```
2. Or switch to Bedrock:
   ```bash
   LLM_PROVIDER=bedrock
   AWS_REGION=us-east-1
   ```

---

### Issue: Import Errors

**Symptom:**
```
ModuleNotFoundError: No module named 'langchain_anthropic'
```

**Solution:**
```bash
# Sync dependencies
uv sync

# If still fails, manually add
uv add langchain-anthropic
uv add langgraph
```

---

### Issue: Real LLM Test Timeout

**Symptom:**
```
❌ Real LLM workflow test failed: TimeoutError
```

**Solution:**
- Check internet connection
- Verify API key is valid
- Check LLM provider status page
- Increase timeout (not currently configurable)

---

### Issue: Low Quality Score

**Symptom:**
```
Quality score: 4/10
```

**Solution:**
- This is expected behavior when testing
- Evaluator may give low score on first attempt
- Generator will retry (max 2 attempts)
- Check `generation_attempts` in output
- Review `evaluation_feedback` for improvement suggestions

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Test AI Orchestration

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Run AI orchestration tests (mocked)
        run: uv run python test_ai_orchestration.py

      # Optional: Test with real LLM (requires secrets)
      - name: Run AI orchestration tests (real)
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        env:
          USE_REAL_LLM: true
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: uv run python test_ai_orchestration.py
```

---

## Performance Benchmarks

### Expected Performance

| Test | Duration | API Calls | Cost |
|------|----------|-----------|------|
| Configuration | <1s | 0 | $0 |
| LLM Providers | <1s | 0 | $0 |
| Agent State | <1s | 0 | $0 |
| Workflow Routing | <1s | 0 | $0 |
| Prompt Templates | <1s | 0 | $0 |
| Workflow (Mocked) | 1-2s | 0 | $0 |
| Workflow (Real - Anthropic) | 10-20s | 3 | ~$0.02 |
| Workflow (Real - Bedrock) | 15-30s | 3 | ~$0.01 |

### Cost Breakdown (Real LLM)

**Per Workflow Run:**
- Orchestrator call (Haiku): ~$0.001
- Generator call (Sonnet): ~$0.01
- Evaluator call (Sonnet): ~$0.01
- **Total: ~$0.02 per run**

---

## Next Steps

After verifying AI orchestration works:

1. **Integrate with Slack Bot** - Connect workflow to Slack commands
2. **Add User Approval Flow** - Implement interactive buttons in Slack
3. **Connect to Jira** - Write generated AC to Jira tickets
4. **Add Slack Context** - Enhance with Slack conversation context
5. **Monitor in Production** - Track quality scores and generation times

---

## Related Documentation

- [Development Guide](DEVELOPMENT.md) - General development workflow
- [Testing Guide](TESTING_GUIDE.md) - Complete testing overview
- [Integration Test Checklist](INTEGRATION_TEST_CHECKLIST.md) - E2E testing

---

## Support

If tests are failing and you can't resolve:

1. Check logs for detailed error messages
2. Verify `.env` configuration
3. Test individual components separately
4. Review prompt templates for syntax errors
5. Check LLM provider status pages

For issues, create a GitHub issue with:
- Test output
- `.env` configuration (redacted)
- Python version: `python --version`
- Package versions: `uv pip list | grep langchain`
