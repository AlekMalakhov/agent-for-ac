# Development Guide

This guide explains the development workflow, architecture decisions, and best practices for the Agent for AC project.

## Architecture Overview

### Dual-Process Design

The application uses a dual-process architecture:

1. **FastAPI Process** (`api` service)
   - Runs on port 8000
   - Provides HTTP health endpoints
   - Lightweight monitoring service
   - Uses its own async event loop
   - Managed by uvicorn

2. **Slack Bot Process** (`slack-bot` service)
   - Connects via Socket Mode (WebSocket)
   - Handles Slack events and commands
   - Manages AI agent workflows
   - Uses its own async event loop
   - Managed by Slack Bolt's AsyncSocketModeHandler

**Why separate processes?**
- Prevents event loop conflicts between FastAPI and Slack Bolt
- Allows independent scaling
- Easier to debug and monitor
- Clear separation of concerns

### Stateless Architecture

The application is **fully stateless** - no databases or persistent storage:

**State Management:**
- Active workflows stored in-memory (`_active_workflows` dictionary)
- Conversation context maintained in Slack threads
- Jira data fetched on-demand via API
- LLM responses generated fresh for each request

**Benefits:**
- Simpler deployment (no database to manage)
- Easy horizontal scaling
- Lower operational costs
- Faster development iteration
- No data persistence concerns

### Technology Stack

**Backend:**
- Python 3.12 - Modern Python with enhanced type hints
- FastAPI - High-performance async web framework
- Slack Bolt - Official Slack SDK with async support
- LangChain + LangGraph - AI agent orchestration
- Anthropic/Bedrock - LLM providers
- uv - Fast, modern Python package manager

**Infrastructure:**
- Docker Compose - Local development orchestration
- Stateless design - No database required

**Observability:**
- Structlog - Structured logging
- Sentry - Error tracking and monitoring (optional)
- Pydantic - Runtime validation and settings

## Development Setup

### Initial Setup

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and navigate to project
cd agent_for_ac

# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env with your tokens
```

### Running Locally

**Option 1: Docker Compose (Recommended)**
```bash
docker compose up
```

**Option 2: Run locally with hot reload**
```bash
# Terminal 1: Run API
uv run python -m src.api

# Terminal 2: Run Slack bot
uv run python -m src.slack.app
```

**Option 3: Python virtual environment (for testing)**
```bash
# Activate uv environment
source .venv/bin/activate  # Unix
# or
.venv\Scripts\activate  # Windows

# Run tests
python test_logging.py
python test_config_validation.py
```

## Code Organization

### Module Structure

```
src/
├── config/          # Configuration management
├── core/            # Core infrastructure (logging, exceptions)
├── api/             # FastAPI application  
├── slack/           # Slack bot application
├── agents/          # AI agent system (orchestrator, generator, etc.)
├── schemas/         # Pydantic data models
└── services/        # Business logic services (Jira, health)
```

### Import Conventions

Always use absolute imports from `src`:
```python
# Good
from src.config.settings import get_settings
from src.core.database import init_database

# Bad
from ..config.settings import get_settings
from core.database import init_database
```

### Type Hints

Use Python 3.12+ union syntax:
```python
# Good
def process(value: str | None) -> dict[str, Any]:
    ...

# Old style (avoid)
from typing import Optional, Dict, Any
def process(value: Optional[str]) -> Dict[str, Any]:
    ...
```

### Async Patterns

**Jira API calls:**
```python
from src.services.jira import get_jira_service

async def process_ticket(ticket_key: str):
    jira = await get_jira_service()
    ticket = await jira.get_ticket(ticket_key)
    return ticket
```

**LLM API calls:**
```python
from src.agents.llm import get_llm

async def generate_ac(prompt: str):
    llm = get_llm(provider="anthropic", model="claude-3-5-sonnet")
    response = await llm.ainvoke(prompt)
    return response
```

### Logging Best Practices

Use structured logging with context:
```python
import structlog

logger = structlog.get_logger()

# Good - structured with context
logger.info(
    "user_action_completed",
    user_id=user_id,
    action="generate_ac",
    duration_ms=duration,
)

# Bad - unstructured string
logger.info(f"User {user_id} completed action in {duration}ms")
```

### Error Handling

Use custom exceptions and provide context:
```python
from src.core.exceptions import DatabaseConnectionError

try:
    await init_database()
except Exception as e:
    # Log with context
    logger.error("database_init_failed", error=str(e), exc_info=True)

    # Raise custom exception
    raise DatabaseConnectionError(
        f"Failed to initialize database: {str(e)}"
    ) from e
```

## Adding New Features

### Adding a New Slack Command

1. **Update command handler** (`src/slack/handlers/commands.py`):
```python
async def handle_ac_agent_command(ack, command, say):
    await ack()

    text = command.get("text", "").strip().lower()

    # Add new command check
    if text == "mycommand":
        await handle_my_command(say, command)
        return

    # ... existing handlers ...

async def handle_my_command(say, command):
    """Handle my new command."""
    # Implementation
    await say("Response message")
```

2. **Test the command:**
- Restart slack-bot: `docker compose restart slack-bot`
- Send `/ac-agent mycommand` in Slack DM

### Adding a New API Endpoint

1. **Create Pydantic schema** (`src/schemas/myfeature.py`):
```python
from pydantic import BaseModel

class MyResponse(BaseModel):
    status: str
    data: dict[str, Any]
```

2. **Create route handler** (`src/api/routes/myfeature.py`):
```python
from fastapi import APIRouter
from src.schemas.myfeature import MyResponse

router = APIRouter(tags=["myfeature"])

@router.get("/myendpoint", response_model=MyResponse)
async def my_endpoint() -> MyResponse:
    return MyResponse(status="success", data={})
```

3. **Register router** (`src/api/app.py`):
```python
from src.api.routes import health, myfeature

app.include_router(health.router)
app.include_router(myfeature.router)
```

### Adding a New Database Model

**Note:** This application uses a stateless architecture without a database. If you need to add persistent storage in the future, consider:

1. **Evaluate necessity:** Can the data be stored in Slack threads or fetched on-demand?
2. **Choose storage:** PostgreSQL for relational data, Redis for caching, or cloud storage
3. **Update architecture document** to reflect the change from stateless to stateful
4. **Add database connection code** in `src/core/`
5. **Update docker-compose.yml** to include database service

## Testing

### Running All Tests

```bash
# AI orchestration tests
uv run python test_ai_orchestration.py

# Jira integration tests  
uv run python test_with_jira_ticket.py

# AC generation tests
uv run python test_generate_ac.py

# Unit tests
uv run pytest tests/unit/
```

### Writing New Tests

Follow the existing patterns in test files:
- Use clear test names
- Include docstrings
- Restore state after tests
- Provide pass/fail indicators

## Debugging

### Viewing Logs

**All services:**
```bash
docker compose logs -f
```

**Specific service:**
```bash
docker compose logs -f slack-bot
docker compose logs -f api
docker compose logs -f postgres
```

**With filtering:**
```bash
docker compose logs -f slack-bot | grep error
```

### Interactive Debugging

**Access running container:**
```bash
docker compose exec slack-bot /bin/sh
docker compose exec api /bin/sh
```

### Common Debug Scenarios

**Bot not responding:**
1. Check logs: `docker compose logs slack-bot`
2. Verify tokens in `.env`
3. Check Socket Mode is enabled
4. Restart bot: `docker compose restart slack-bot`

**Jira connection issues:**
1. Verify credentials in `.env`
2. Test with a real ticket key
3. Check API token permissions in Jira

**LLM API issues:**
1. Check API key is valid
2. Verify model names are correct
3. Check API rate limits
4. Review logs for specific error messages

## Code Quality

### Before Committing

- Run tests
- Check code formatting
- Verify type hints
- Update documentation if needed
- Test in Docker environment

### Code Review Checklist

- [ ] Type hints on all functions
- [ ] Docstrings for public functions
- [ ] Structured logging used
- [ ] Error handling with custom exceptions
- [ ] Async/await used correctly
- [ ] No secrets in code
- [ ] Tests passing
- [ ] Documentation updated

## Performance Considerations

### Jira API

- API calls are made on-demand (no caching by default)
- Use async operations for non-blocking I/O
- Consider rate limits for high-volume usage
- Batch requests when possible

### LLM API

- Response times vary by model (Haiku faster than Sonnet)
- Use appropriate model for task complexity
- Consider streaming for long responses
- Monitor token usage and costs

### Slack Bot

- Acknowledge commands immediately (`await ack()`)
- Use async for all I/O operations
- Store active workflows in memory (auto-cleanup)
- Leverage Slack threads for conversation context

## Security

### Secrets Management

Never commit secrets:
- All tokens in `.env` (gitignored)
- Use environment variables
- Sanitize logs (no credentials)

### Input Validation

Use Pydantic for validation:
```python
from pydantic import BaseModel, Field, validator

class MyInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str

    @validator('email')
    def validate_email(cls, v):
        # Validation logic
        return v
```

### Error Messages

Don't expose sensitive information:
```python
# Good
raise DatabaseConnectionError("Failed to connect to database")

# Bad
raise DatabaseConnectionError(f"Failed to connect to postgresql://user:password@host/db")
```

## Deployment (Future)

This section will be expanded when deploying to production:
- AWS ECS configuration
- Environment-specific settings
- Secrets management with AWS Secrets Manager
- CI/CD pipeline
- Monitoring and alerting

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Slack Bolt Python](https://slack.dev/bolt-python/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Structlog](https://www.structlog.org/)
- [uv Documentation](https://github.com/astral-sh/uv)
