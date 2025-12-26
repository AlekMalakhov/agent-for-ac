# Testing Guide for Agent for AC

This document provides an overview of all testing capabilities for the Agent for AC project.

## Test Suite Overview

The project includes test scripts to verify the AI agents, Slack integration, and Jira integration.

### Automated Test Scripts

1. **test_ai_orchestration.py** - AI agent workflow tests
2. **test_with_jira_ticket.py** - Jira integration tests
3. **test_generate_ac.py** - Acceptance criteria generation tests
4. **tests/unit/** - Unit tests for components

### Manual Testing Guides

- **TEST_SLACK_COMMANDS.md** - Slack command testing
- **TEST_AI_ORCHESTRATION.md** - AI orchestration testing
- **TEST_HEALTH_CHECK.md** - Health check testing

## Quick Start

### Prerequisites

```bash
# Ensure dependencies are installed
uv sync

# Ensure .env file exists with valid configuration
cp .env.example .env  # If needed
nano .env  # Add your tokens
```

### Running Automated Tests

#### 1. AI Orchestration Tests

Tests the multi-agent AI workflow for generating acceptance criteria.

```bash
uv run python test_ai_orchestration.py
```

**What it tests:**
- Orchestrator agent decision making
- Information gathering flow
- AC generation in multiple formats
- Quality evaluation
- Full workflow integration

**Expected output:**
```
Starting AI Orchestration Test...
==================================================
Creating initial state...
Running workflow...
✅ Workflow completed successfully!

Generated AC (Quality: 8/10):
[Generated acceptance criteria shown here]
```

---

#### 2. Jira Integration Tests

Tests reading and processing real Jira tickets.

**Prerequisites:**
- Valid Jira credentials in `.env`
- Real Jira ticket to test with

**Run tests:**
```bash
uv run python test_with_jira_ticket.py
```

**What it tests:**
- Jira API connection
- Ticket reading
- AC detection
- Workflow execution with real ticket data

---

#### 3. AC Generation Tests

Tests generating acceptance criteria from scratch.

```bash
uv run python test_generate_ac.py
```

**What it tests:**
- AC generation without existing ticket
- Different format outputs
- Quality evaluation

---

#### 4. Unit Tests

Run all unit tests:

```bash
uv run pytest tests/unit/
```

**What it tests:**
- Agent components
- LLM provider abstraction
- Jira service
- Workflow state management

---

## Manual Testing

For comprehensive Slack integration testing:

**[TEST_SLACK_COMMANDS.md](./TEST_SLACK_COMMANDS.md)**

This guide includes:
- Testing slash commands
- Testing @mentions in channels
- Testing thread interactions
- Expected bot responses

**[TEST_AI_ORCHESTRATION.md](./TEST_AI_ORCHESTRATION.md)**

This guide includes:
- Step-by-step AI workflow testing
- Testing different AC formats
- Testing information gathering
- Evaluating quality scores

## Test Categories Summary

### 1. AI Agent Tests
- ✅ Orchestrator agent routing
- ✅ Information gathering questions
- ✅ AC generation in multiple formats
- ✅ Quality evaluation scoring
- ✅ Full workflow integration

### 2. Jira Integration Tests
- ✅ API connection and authentication
- ✅ Ticket reading and parsing
- ✅ AC detection in descriptions
- ✅ Ticket updates
- ✅ Error handling for invalid tickets

### 3. Slack Integration Tests
- ✅ Slash command handling
- ✅ @mention detection
- ✅ Thread conversation management
- ✅ Message formatting
- ✅ Interactive workflow

### 4. Service Health Tests
- ✅ Health check endpoint
- ✅ Jira connectivity verification
- ✅ LLM API connectivity

## Important Notes

### Test Requirements

Test scripts require:
- Valid `.env` configuration
- Running Docker services (for integration tests)
- LLM API access (Anthropic or Bedrock)
- Jira credentials (for Jira integration tests)

### Running Tests in CI/CD

For CI/CD pipelines, run tests in this order:

```bash
# 1. Start services
docker compose up -d

# 2. Wait for services to be ready
sleep 10

# 3. Run unit tests
uv run pytest tests/unit/

# 4. Run integration tests (if Jira/LLM configured)
uv run python test_ai_orchestration.py
uv run python test_generate_ac.py

# 5. Cleanup
docker compose down
```

### Exit Codes

All test scripts exit with:
- `0` - All tests passed
- `1` - One or more tests failed

This makes them suitable for CI/CD integration.

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError` when running tests

**Solution:**
```bash
uv sync
```

### LLM API Errors

**Problem:** Tests fail with API connection errors

**Solution:**
- Verify `ANTHROPIC_API_KEY` or AWS credentials in `.env`
- Check API rate limits
- Verify model names are correct

### Jira Connection Issues

**Problem:** Jira integration tests fail

**Solution:**
```bash
# Verify Jira credentials
echo $JIRA_SITE_URL
echo $JIRA_USER_EMAIL
# Check API token is valid in Jira settings
```

### Docker Issues

**Problem:** Services won't start

**Solution:**
```bash
# Restart Docker services
docker compose down
docker compose up --build

# Check service logs
docker compose logs slack-bot
```

### Port Conflicts

**Problem:** API service fails to start

**Solution:**
```bash
# Check what's using port 8000
lsof -i :8000

# Stop conflicting service or change port in docker-compose.yml
```

## Best Practices

1. **Start with unit tests** - They're fast and don't require external services
2. **Test AI workflows interactively** - Use test scripts to see agent behavior
3. **Use Docker Compose** - Ensures consistent environment
4. **Monitor logs** - Watch `docker compose logs -f` during testing
5. **Test with real Jira tickets** - Validates end-to-end integration
6. **Check quality scores** - Evaluate AI-generated output

## Contributing

When adding new tests:

1. Follow existing test patterns
2. Add tests to appropriate directory (unit/ or root)
3. Document test purpose and expected behavior
4. Include example outputs
5. Update this guide with new tests
6. Test both success and error cases

## Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Slack Bolt Documentation](https://slack.dev/bolt-python/)
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Jira Cloud REST API](https://developer.atlassian.com/cloud/jira/platform/rest/)
