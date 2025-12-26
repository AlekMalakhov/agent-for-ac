# Agent for AC

An AI-powered Slack bot that helps generate and evaluate high-quality acceptance criteria for Jira tickets using multi-agent LLM orchestration.

## Overview

Agent for AC is an intelligent assistant that:
- Analyzes Jira tickets and automatically detects existing acceptance criteria
- Asks clarifying questions when information is insufficient
- Generates clear, testable acceptance criteria in multiple formats (Checklist, BDD, Free)
- Evaluates AC quality and provides improvement recommendations
- Works seamlessly in Slack channels with thread support
- Supports multilingual interactions (questions in any language, AC generated in English)

**Target Users:** Project Managers and QA Engineers

## Features

### Core Functionality
- **Multi-Agent AI System** - Orchestrator, Information Gatherer, Generator, Evaluator, Refiner, and Modifier agents
- **Interactive Chat Refinement** - Refine generated AC through natural language conversation
- **Slack Integration** - Interact via `/ac-agent` commands or `@mention` in channels
- **Thread Support** - Bot automatically creates threads for workflows in channels
- **Jira Integration** - Read tickets, detect existing AC, and update tickets
- **LLM Provider Support** - Works with Anthropic API or AWS Bedrock
- **Multiple AC Formats** - Checklist, BDD (Given/When/Then), or Free text format

### Technical Features
- **Stateless Architecture** - No database required, all state managed in Slack threads
- **Structured Logging** - JSON logs with configurable levels (INFO for clean output)
- **Error Tracking** - Integrated Sentry support
- **Hot Reload** - Code changes reflected immediately during development
- **Docker Compose** - Easy local development setup

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Slack Bot                          │
│  (Socket Mode / WebSocket Connection)           │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │   Multi-Agent System (LangGraph)          │ │
│  │                                           │ │
│  │   ┌──────────────────────┐               │ │
│  │   │  Orchestrator Agent  │               │ │
│  │   └──────────┬───────────┘               │ │
│  │              │                            │ │
│  │    ┌─────────┼─────────┐                 │ │
│  │    ▼         ▼         ▼                 │ │
│  │  [Info]  [Generator] [Eval]              │ │
│  │  Gatherer           uator                 │ │
│  │              │                            │ │
│  │              ▼                            │ │
│  │   ┌──────────────────────┐               │ │
│  │   │   Chat Refinement    │               │ │
│  │   │  ┌────────┐ ┌─────┐  │               │ │
│  │   │  │Refiner │→│Modi-│  │               │ │
│  │   │  │        │ │fier │  │               │ │
│  │   │  └────────┘ └─────┘  │               │ │
│  │   └──────────────────────┘               │ │
│  └───────────────────────────────────────────┘ │
└────────┬────────────────┬────────────────────┘
         │                │
         ▼                ▼
   ┌─────────┐      ┌──────────┐
   │ Jira API│      │ LLM APIs │
   │(API Token)     │(Anthropic│
   └─────────┘      │/Bedrock) │
                    └──────────┘

┌──────────────────┐
│  FastAPI Server  │  ← Health checks
│  (Port 8000)     │
└──────────────────┘
```

## Prerequisites

- **Docker** and **Docker Compose** (for local development)
- **Python 3.12+** (for running tests locally)
- **uv** package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Slack workspace** with admin access (to create/install Slack app)
- **Jira Cloud** account with API token
- **LLM API access** (Anthropic API key or AWS Bedrock credentials)

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd agent_for_ac

# Copy and configure environment variables
cp .env.example .env
nano .env  # Add your tokens and API keys
```

**Required environment variables:**
```bash
# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# Jira
JIRA_SITE_URL=https://yourcompany.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token

# LLM (choose one)
LLM_PROVIDER=anthropic  # or "bedrock"
ANTHROPIC_API_KEY=sk-ant-...  # if using Anthropic

# Optional
SENTRY_DSN=
LOG_LEVEL=INFO
```

See setup guides:
- [Slack Setup Guide](docs/SLACK_SETUP.md) - How to create and configure Slack app
- [Jira Setup Guide](docs/JIRA_SETUP.md) - How to get Jira API token

### 2. Start Services

```bash
docker compose up
```

Wait for: `INFO:slack_bolt.AsyncApp:⚡️ Bolt app is running!`

### 3. Test Installation

**Check service health:**
```bash
docker compose ps  # Both services should be "Up"
curl http://localhost:8000/health
```

**Test Slack bot:**
- Open Slack workspace
- Find "Agent for AC" bot (green dot = online)
- In a channel, type: `@Agent for AC health`
- You should receive a health status message

## Usage

### Bot Interaction Modes

#### In Direct Messages (DM)
Use slash commands:
```
/ac-agent
/ac-agent health
/ac-agent <jira-link>
```

#### In Channels
Mention the bot:
```
@Agent for AC health
@Agent for AC https://yourcompany.atlassian.net/browse/PROJ-123
```

When you mention the bot with a Jira ticket link in a channel, it automatically creates a thread to keep the conversation organized.

#### In Threads
Bot automatically continues the conversation in the existing thread. No special syntax needed - just mention the bot with your response:
```
@Agent for AC checklist
@Agent for AC yes
@Agent for AC approve
```

### Generating Acceptance Criteria

**Full workflow example:**

1. **Start workflow** (in channel):
   ```
   @Agent for AC https://yourcompany.atlassian.net/browse/PROJ-123
   ```
   Bot creates a thread and analyzes the ticket.

2. **Choose format** (bot asks in thread):
   ```
   @Agent for AC checklist
   ```
   Options: `checklist`, `bdd`, `free`

3. **Answer questions** (if bot needs more info):
   ```
   @Agent for AC Yes, it should support mobile devices
   ```

4. **Review and refine** (interactive chat mode):
   Bot shows generated AC with quality score. You can now refine using natural language:
   ```
   @Agent for AC Make criterion #3 more specific about error handling
   @Agent for AC Add a criterion for accessibility
   @Agent for AC Convert to BDD format
   @Agent for AC Remove the last one
   ```

5. **Approve when satisfied**:
   ```
   @Agent for AC approve
   ```

6. **Done!**
   AC is automatically added to the Jira ticket.

### Interactive Chat Refinement

After AC is generated, you enter chat refinement mode where you can:

| Action | Example Command |
|--------|-----------------|
| Modify specific criterion | "Make criterion #3 more specific" |
| Add new criterion | "Add an error handling criterion" |
| Remove criterion | "Remove the last one" or "Delete criterion 4" |
| Change format | "Convert to BDD format" |
| Regenerate with context | "Regenerate focusing on edge cases" |
| Approve and save | "approve" or "looks good" |
| Cancel | "cancel" |

The bot understands natural language - just describe what you want to change!

### Available Commands

#### `/ac-agent` (empty)
Shows welcome message with available commands.

#### `/ac-agent health`
Displays system health status including Jira connectivity.

**Response:**
```
✅ *System Health Status*
✅ Service: `running`
_All systems operational._
```

#### `/ac-agent <jira-link>` or `@Agent for AC <jira-link>`
Generate or evaluate acceptance criteria for a Jira ticket.

**Supported formats:**
- Full URL: `https://yourcompany.atlassian.net/browse/PROJ-123`
- Ticket key: `PROJ-123`

**Supported ticket types:** Story, Task

### API Endpoints

#### `GET /health`
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "agent-for-ac"
}
```

**Interactive API documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Project Structure

```
agent_for_ac/
├── src/
│   ├── agents/              # Multi-agent AI system
│   │   ├── orchestrator.py  # Workflow coordinator
│   │   ├── information_gatherer.py  # Q&A agent
│   │   ├── generator.py     # AC generation agent
│   │   ├── evaluator.py     # Quality evaluation agent
│   │   ├── refiner.py       # Intent classification for chat refinement
│   │   ├── modifier.py      # Surgical AC modifications
│   │   ├── workflow.py      # LangGraph state machine
│   │   ├── llm/            # LLM provider abstraction
│   │   └── prompts/        # Agent prompts (6 files)
│   ├── config/
│   │   └── settings.py      # Pydantic settings
│   ├── core/
│   │   ├── logging.py       # Structured logging (structlog)
│   │   └── exceptions.py    # Custom exceptions
│   ├── api/
│   │   ├── app.py           # FastAPI application
│   │   └── routes/
│   │       └── health.py    # Health check endpoints
│   ├── slack/
│   │   ├── app.py           # Slack bot main application
│   │   └── handlers/
│   │       ├── commands.py  # Slash command handlers
│   │       └── events.py    # Event handlers (mentions, threads)
│   ├── schemas/
│   │   └── jira.py          # Pydantic models for Jira
│   └── services/
│       ├── health_check.py  # Health check service
│       └── jira.py          # Jira API integration
├── tests/                   # Test files
├── docs/                    # Documentation
├── context/                 # Product requirements & specs
├── docker-compose.yml       # Docker services
├── Dockerfile               # Container image
├── pyproject.toml           # Python dependencies (uv)
└── .env.example             # Environment template
```

### Running Tests

```bash
# Test with real Jira ticket
uv run python test_with_jira_ticket.py

# Test AI orchestration
uv run python test_ai_orchestration.py

# Generate AC from scratch
uv run python test_generate_ac.py
```

### Development Workflow

**Start services with logs:**
```bash
docker compose up
```

**Run in background:**
```bash
docker compose up -d
docker compose logs -f slack-bot
```

**Rebuild after code changes:**
```bash
docker compose up --build
```

**Add new dependencies:**
```bash
uv add package-name
docker compose up --build
```

### Hot Reload

Both services support hot reload - edit code in `src/` and changes are reflected immediately:
- FastAPI: Auto-reloads on code changes
- Slack bot: Restarts when files are modified

Watch logs to see reload happening:
```bash
docker compose logs -f slack-bot
```

### Logging Configuration

Clean logs are enabled by default (`LOG_LEVEL=INFO`). To see more details:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG docker compose up

# Or change in .env file
LOG_LEVEL=DEBUG
```

The bot now uses clean logging with minimal verbosity - no ping-pong messages or verbose HTTP logs cluttering your output.

## Testing Documentation

Comprehensive testing guides:
- [Slack Commands Testing](docs/TEST_SLACK_COMMANDS.md)
- [Health Check Testing](docs/TEST_HEALTH_CHECK.md)
- [Error Handling Verification](docs/TEST_ERROR_HANDLING.md)
- [AI Orchestration Testing](docs/TEST_AI_ORCHESTRATION.md)
- [Complete Testing Guide](docs/TESTING_GUIDE.md)

## Troubleshooting

### Services won't start

```bash
docker ps  # Check Docker is running
docker compose logs  # Check error messages
docker compose down && docker compose up --build  # Clean rebuild
```

### Slack bot shows offline

1. Verify tokens in `.env` (SLACK_BOT_TOKEN starts with `xoxb-`, SLACK_APP_TOKEN with `xapp-`)
2. Check Socket Mode is enabled in Slack app settings
3. Check logs: `docker compose logs slack-bot`
4. Restart: `docker compose restart slack-bot`

### Bot doesn't respond to messages

1. **In channels:** Make sure you're mentioning the bot (`@Agent for AC`)
2. **In DM:** Use `/ac-agent` slash commands
3. **In threads:** Bot responds to @mentions in threads
4. Check logs for errors: `docker compose logs -f slack-bot`

### Jira integration issues

1. Verify `JIRA_SITE_URL`, `JIRA_USER_EMAIL`, and `JIRA_API_TOKEN` in `.env`
2. Test Jira connection: Bot will show error if credentials are invalid
3. Check Jira permissions - API token must have read/write access to tickets

### LLM API issues

1. For Anthropic: Verify `ANTHROPIC_API_KEY` is valid
2. For Bedrock: Verify AWS credentials and region
3. Check logs for API errors
4. Verify model names in `.env` match available models

## Roadmap

**✅ Phase 1: Foundation & Core AC Generation (Completed)**
- Slack bot interface with Socket Mode
- Jira integration (read & write)
- Multi-agent AI system with LangGraph
- AC generation in multiple formats
- Quality evaluation
- Thread support in channels

**🚧 Phase 2: Context Enrichment (In Progress)**
- Slack conversation context gathering
- Enhanced interactive Q&A workflow
- Improved UI with Slack Block Kit

**📋 Phase 3: Production Readiness (Planned)**
- AWS ECS deployment
- CloudWatch monitoring
- Performance optimization
- Usage analytics

See [context/product/roadmap.md](context/product/roadmap.md) for details.

## Contributing

### Code Style

- Python 3.12+ syntax with type hints
- Async/await for I/O operations
- Structured logging: `logger.info("event_name", field="value")`
- Custom exceptions from `src.core.exceptions`

### Error Handling

Use custom exceptions:
- `ApplicationError` - Base exception
- `ConfigurationError` - Config validation errors
- `SlackConnectionError` - Slack API errors
- `JiraConnectionError`, `JiraTicketNotFoundError`, etc. - Jira errors

## Documentation

- [Quick Start Guide](QUICKSTART.md) - Get running in 5 minutes
- [Slack Setup Guide](docs/SLACK_SETUP.md) - Configure Slack app
- [Jira Setup Guide](docs/JIRA_SETUP.md) - Get Jira API token
- [Testing Guide](docs/TESTING_GUIDE.md) - Run tests
- [Product Definition](context/product/product-definition.md) - Product vision
- [Architecture Overview](context/product/architecture.md) - Technical architecture

## License

[Your License Here]

## Support

For issues and questions:
- Create an issue in the repository
- Check existing documentation in `docs/`
- Review test scripts for examples
