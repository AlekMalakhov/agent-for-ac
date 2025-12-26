# Technical Specification: Slack Bot Setup

- **Functional Specification:** `context/spec/001-slack-bot-setup/functional-spec.md`
- **Status:** Draft
- **Author(s):** Technical Team with Python Expert Analysis

---

## 1. High-Level Technical Approach

This implementation establishes the foundational Python infrastructure for Agent for AC using a **dual-process architecture**:

1. **FastAPI Process** - HTTP server for health endpoints (`/health`, `/readiness`)
2. **Slack Bot Process** - Slack Bolt application with Socket Mode for DM command handling
3. **Shared Infrastructure** - Both processes connect to PostgreSQL and Redis for data/caching
4. **Docker Compose Orchestration** - All services (postgres, redis, api, slack-bot) managed together

This architecture provides clear separation of concerns, simplifies debugging, and enables independent scaling in production (Phase 3).

**Technology Stack:**
- Python 3.12 with FastAPI + Slack Bolt
- PostgreSQL 16 (async with SQLAlchemy/SQLModel)
- Redis 7 (async client)
- Docker Compose for local orchestration
- uv for package management
- Structlog for structured logging
- Sentry for error tracking

---

## 2. Proposed Solution & Implementation Plan

### 2.1 Project Structure

```
agent_for_ac/
├── pyproject.toml                  # uv project configuration
├── uv.lock                         # Dependency lockfile
├── docker-compose.yml              # Service orchestration
├── Dockerfile                      # Python application container
├── .env.example                    # Configuration template
├── .env                            # Actual config (gitignored)
├── .gitignore
├── README.md
│
├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             # Pydantic settings with validation
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── logging.py              # Structlog configuration
│   │   ├── database.py             # PostgreSQL connection management
│   │   ├── cache.py                # Redis connection management
│   │   └── exceptions.py           # Custom exception hierarchy
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                  # FastAPI application factory
│   │   ├── middleware.py           # Correlation ID middleware
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py           # Health & readiness endpoints
│   │
│   ├── slack/
│   │   ├── __init__.py
│   │   ├── app.py                  # Slack Bolt app factory & startup
│   │   └── handlers/
│   │       ├── __init__.py
│   │       └── commands.py         # /ac-agent command handlers
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── health.py               # Pydantic response models
│   │
│   └── services/
│       ├── __init__.py
│       └── health_check.py         # Database/Redis health check logic
│
└── tests/
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures
    └── unit/
        ├── __init__.py
        └── test_config.py          # Configuration validation tests
```

**Rationale:**
- `src/` layout: Industry standard, clean separation from tests
- `config/`: Centralized configuration with type safety
- `core/`: Shared infrastructure (DB, cache, logging) used by both processes
- `api/` vs `slack/`: Clear separation of HTTP and Slack concerns
- `schemas/`: Pydantic models for data validation
- `services/`: Reusable business logic

### 2.2 Configuration Management

**Implementation (src/config/settings.py):**

```python
from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Slack Configuration (Required)
    slack_bot_token: SecretStr = Field(
        ..., description="Slack Bot User OAuth Token (xoxb-...)"
    )
    slack_app_token: SecretStr = Field(
        ..., description="Slack App-Level Token for Socket Mode (xapp-...)"
    )

    # Database Configuration (Required)
    postgres_url: PostgresDsn = Field(
        ..., description="PostgreSQL connection URL"
    )

    # Cache Configuration (Optional with default)
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # Observability (Optional)
    sentry_dsn: str | None = Field(
        default=None, description="Sentry DSN for error tracking"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # Environment
    environment: str = Field(
        default="local",
        description="Environment name (local, staging, production)"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

# Singleton pattern
_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

**Environment Variables (.env.example):**
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
POSTGRES_URL=postgresql+asyncpg://agent_ac:dev_password@postgres:5432/agent_ac_db
REDIS_URL=redis://redis:6379/0
SENTRY_DSN=
LOG_LEVEL=INFO
ENVIRONMENT=local
```

**Error Handling:**
- Missing required fields (SLACK_BOT_TOKEN, etc.) → Pydantic raises `ValidationError` with specific field name
- Invalid URL format → Pydantic raises `ValidationError` with validation details
- Application catches at startup and logs: "SLACK_BOT_TOKEN is required but not set in environment"

### 2.3 Database Connection & Management

**Implementation (src/core/database.py):**

```python
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import structlog

logger = structlog.get_logger()

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

async def init_database(database_url: str) -> None:
    """Initialize database engine and test connection."""
    global _engine, _session_factory

    _engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,      # Verify connections before using
        pool_size=5,
        max_overflow=10,
    )

    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )

    # Test connection and create tables
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    logger.info("database_connected", url=database_url.split("@")[0])  # Sanitized

async def close_database() -> None:
    """Close database engine."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("database_closed")

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session context manager."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Database Strategy:**
- Phase 1: Auto-create tables with `SQLModel.metadata.create_all()` (simple, fast)
- Phase 2+: Migrate to Alembic for versioned migrations

### 2.4 Redis Connection & Management

**Implementation (src/core/cache.py):**

```python
from redis.asyncio import Redis, ConnectionPool
import structlog

logger = structlog.get_logger()

_redis_client: Redis | None = None
_connection_pool: ConnectionPool | None = None

async def init_redis(redis_url: str) -> None:
    """Initialize Redis connection pool and test connection."""
    global _redis_client, _connection_pool

    _connection_pool = ConnectionPool.from_url(
        redis_url,
        max_connections=10,
        decode_responses=True,  # Automatically decode bytes to str
    )

    _redis_client = Redis(connection_pool=_connection_pool)

    # Test connection
    await _redis_client.ping()
    logger.info("redis_connected", url=redis_url.split("@")[0])

async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client, _connection_pool

    if _redis_client:
        await _redis_client.aclose()
    if _connection_pool:
        await _connection_pool.disconnect()

    logger.info("redis_closed")

def get_redis() -> Redis:
    """Get Redis client."""
    if _redis_client is None:
        raise RuntimeError("Redis not initialized")
    return _redis_client
```

### 2.5 Startup Sequence & Initialization

**Application Startup Order:**

```
1. Load & validate configuration (pydantic-settings)
   ↓ [Fail fast if missing/invalid]
2. Initialize structured logging (structlog)
   ↓
3. Initialize Sentry (if SENTRY_DSN provided)
   ↓
4. Connect to PostgreSQL
   ↓ [Fail with clear error if connection fails]
5. Connect to Redis
   ↓ [Fail with clear error if connection fails]
6. Start FastAPI (api process) OR Slack Bot (slack-bot process)
   ↓
7. Log "service_started" with process type
```

**Implementation (src/slack/app.py - Slack Bot Entrypoint):**

```python
import asyncio
import structlog
from src.config.settings import get_settings
from src.core.logging import configure_logging
from src.core.database import init_database, close_database
from src.core.cache import init_redis, close_redis
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from src.slack.handlers import commands

logger = structlog.get_logger()

async def startup() -> Settings:
    """Initialize all connections."""
    try:
        settings = get_settings()  # Validates configuration
    except Exception as e:
        print(f"Configuration error: {e}")
        raise

    configure_logging(settings.log_level)
    logger.info("configuration_loaded", environment=settings.environment)

    if settings.sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)
        logger.info("sentry_initialized")

    try:
        await init_database(str(settings.postgres_url))
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise RuntimeError(f"Failed to connect to PostgreSQL: {e}") from e

    try:
        await init_redis(str(settings.redis_url))
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise RuntimeError(f"Failed to connect to Redis: {e}") from e

    return settings

async def shutdown():
    """Clean up connections."""
    logger.info("shutting_down")
    await close_redis()
    await close_database()
    logger.info("shutdown_complete")

def create_slack_app(settings: Settings) -> AsyncSocketModeHandler:
    """Create Slack Bolt app with Socket Mode."""
    app = AsyncApp(
        token=settings.slack_bot_token.get_secret_value(),
        process_before_response=True,
    )

    # Register handlers
    commands.register(app)

    handler = AsyncSocketModeHandler(
        app=app,
        app_token=settings.slack_app_token.get_secret_value(),
    )

    logger.info("slack_app_created")
    return handler

async def main():
    """Main application entrypoint."""
    try:
        settings = await startup()

        slack_handler = create_slack_app(settings)
        logger.info("slack_bot_starting")

        await slack_handler.start_async()

    except KeyboardInterrupt:
        logger.info("received_keyboard_interrupt")
    except Exception as e:
        logger.exception("startup_failed", error=str(e))
        raise
    finally:
        await shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

**Error Messages:**
- Configuration validation error: Pydantic provides detailed message (e.g., "field required: slack_bot_token")
- Database connection error: "Failed to connect to PostgreSQL at postgresql://agent_ac@postgres:5432/agent_ac_db: connection refused"
- Redis connection error: "Failed to connect to Redis at redis://redis:6379: connection timeout"
- Slack connection error: "Failed to connect to Slack: invalid_auth"

### 2.6 FastAPI Health Endpoints

**Implementation (src/api/routes/health.py):**

```python
from fastapi import APIRouter, status
from src.schemas.health import HealthResponse, ReadinessResponse
from src.services.health_check import check_database, check_redis

router = APIRouter()

@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """Basic health check - returns 200 if service is running."""
    return HealthResponse(status="healthy", service="agent-for-ac")

@router.get("/readiness", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """Readiness check - verifies dependencies are available."""
    db_status = await check_database()
    redis_status = await check_redis()

    is_ready = db_status == "connected" and redis_status == "connected"

    if is_ready:
        return ReadinessResponse(
            status="ready",
            postgres=db_status,
            redis=redis_status,
        )
    else:
        # Return 503 Service Unavailable
        return ReadinessResponse(
            status="not ready",
            postgres=db_status,
            redis=redis_status,
        )
```

**Response Schemas (src/schemas/health.py):**

```python
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    service: str

class ReadinessResponse(BaseModel):
    status: str
    postgres: str
    redis: str
```

**Health Check Service (src/services/health_check.py):**

```python
from src.core.database import _engine
from src.core.cache import _redis_client
import structlog

logger = structlog.get_logger()

async def check_database() -> str:
    """Check PostgreSQL connection status."""
    if _engine is None:
        return "disconnected"

    try:
        async with _engine.connect() as conn:
            await conn.execute("SELECT 1")
        return "connected"
    except Exception as e:
        logger.warning("database_health_check_failed", error=str(e))
        return "disconnected"

async def check_redis() -> str:
    """Check Redis connection status."""
    if _redis_client is None:
        return "disconnected"

    try:
        await _redis_client.ping()
        return "connected"
    except Exception as e:
        logger.warning("redis_health_check_failed", error=str(e))
        return "disconnected"
```

**FastAPI Application Factory (src/api/app.py):**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog
from src.api.routes import health
from src.config.settings import get_settings

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    logger.info("fastapi_starting")
    yield
    logger.info("fastapi_stopping")

def create_app() -> FastAPI:
    """FastAPI application factory."""
    settings = get_settings()

    app = FastAPI(
        title="Agent for AC API",
        description="Acceptance Criteria Generation Bot API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Register routes
    app.include_router(health.router, tags=["health"])

    return app
```

### 2.7 Slack Bot Command Handling

**Command Handler Registration (src/slack/handlers/commands.py):**

```python
from slack_bolt.async_app import AsyncApp
from src.services.health_check import check_database, check_redis
import structlog

logger = structlog.get_logger()

def register(app: AsyncApp) -> None:
    """Register all Slack command handlers."""
    app.command("/ac-agent")(handle_ac_agent_command)

async def handle_ac_agent_command(ack, command, say):
    """Handle /ac-agent slash command."""
    await ack()  # Acknowledge immediately

    user_id = command["user_id"]
    text = command.get("text", "").strip()
    channel_type = command.get("channel_name")

    # Only respond in DMs
    if channel_type != "directmessage":
        await say("Please use this command in a direct message with me.")
        return

    logger.info(
        "ac_agent_command_received",
        user_id=user_id,
        text=text,
    )

    # Handle health check
    if text.lower() == "health":
        db_status = await check_database()
        redis_status = await check_redis()

        response = (
            "*Bot Status Check*\n\n"
            f"• Bot: :white_check_mark: Online and operational\n"
            f"• PostgreSQL: {':white_check_mark:' if db_status == 'connected' else ':x:'} {db_status.capitalize()}\n"
            f"• Redis: {':white_check_mark:' if redis_status == 'connected' else ':x:'} {redis_status.capitalize()}"
        )
        await say(response)

    # Handle empty command
    elif not text:
        await say(
            "Hello! I'm Agent for AC. I'm ready to help you generate acceptance criteria. "
            "(Full functionality coming soon!)"
        )

    # Handle command with arguments
    else:
        await say(f"I received your command: `{text}`. Command processing is being implemented.")
```

### 2.8 Logging & Observability

**Structlog Configuration (src/core/logging.py):**

```python
import logging
import sys
import structlog

def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging with structlog."""

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            # JSON for production, pretty for development
            structlog.dev.ConsoleRenderer() if sys.stdout.isatty()
                else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

**Sentry Integration:**
- Initialized in startup sequence if `SENTRY_DSN` is provided
- Automatically captures unhandled exceptions
- Tags events with environment name
- FastAPI middleware integration for request context

### 2.9 Docker Compose Orchestration

**Dockerfile:**

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/

# Expose FastAPI port
EXPOSE 8000

# Default command (overridden in docker-compose)
CMD ["uv", "run", "uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: agent_ac
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: agent_ac_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agent_ac"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    command: ["uv", "run", "uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src  # Hot reload for development
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  slack-bot:
    build: .
    command: ["uv", "run", "python", "-m", "src.slack.app"]
    volumes:
      - ./src:/app/src  # Hot reload for development
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
```

**Key Features:**
- Health checks ensure dependencies are ready before app starts
- Volume mounts enable hot reload during development
- Separate volumes for data persistence
- Both processes (api, slack-bot) use same Dockerfile with different commands

### 2.10 Dependencies (pyproject.toml)

```toml
[project]
name = "agent-for-ac"
version = "0.1.0"
description = "Slack bot for generating Jira acceptance criteria"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.109.0",
    "slack-bolt>=1.18.0",
    "python-dotenv>=1.0.0",
    "pydantic-settings>=2.1.0",
    "sqlmodel>=0.0.14",
    "redis>=5.0.0",
    "asyncpg>=0.29.0",
    "uvicorn>=0.27.0",
    "langchain>=0.1.0",
    "sentry-sdk[fastapi]>=1.40.0",
    "structlog>=24.1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.26.0",
]
```

---

## 3. Impact and Risk Analysis

### 3.1 System Dependencies

**Internal Dependencies:**
- None (this is the foundational infrastructure)

**External Dependencies:**
- Slack workspace (existing bot already configured)
- PostgreSQL database (provided by Docker Compose)
- Redis cache (provided by Docker Compose)
- Sentry service (optional, external SaaS)

**Future Features Depending on This Setup:**
- All Phase 1 features (Jira integration, AC generation) will build on this foundation
- Database models will be added as features require them
- Slack handlers will expand to support more commands and interactions

### 3.2 Potential Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **AsyncIO Complexity** - FastAPI and Slack Bolt use separate event loops | High - Could cause deadlocks or blocking | Medium | **Separate processes** - Run api and slack-bot as independent Docker services. Eliminates event loop conflicts. |
| **Socket Mode Connection Drops** - Network issues cause Slack bot disconnection | Medium - Users can't interact during downtime | Low | **Auto-reconnect** - Slack SDK handles reconnection automatically. Add connection monitoring in Phase 3. |
| **Secret Leakage in Logs** - Tokens accidentally logged to console/Sentry | High - Security vulnerability | Medium | **SecretStr type** - Pydantic SecretStr prevents printing. Sanitize URLs before logging (split on '@'). Never log token values. |
| **Database/Redis Startup Race** - App starts before dependencies ready | Medium - Startup fails with unclear error | Medium | **Health checks** - Docker Compose `depends_on` with health check conditions. Application won't start until DB/Redis are healthy. |
| **Missing Environment Variables** - Developer forgets to set required config | Low - Startup fails | High | **Pydantic validation** - Settings validation fails fast with clear error message indicating missing field. `.env.example` documents all required vars. |
| **uv Adoption** - Team unfamiliar with new package manager | Low - Learning curve | Low | **Documentation** - uv has pip-compatible interface. Provide clear setup instructions in README. |

### 3.3 Performance Considerations

**Phase 1 (Local Development):**
- Expected load: 1-5 concurrent users
- PostgreSQL/Redis in Docker sufficient
- No performance concerns

**Phase 3 (Production):**
- Socket Mode has limits (~100 concurrent connections per bot)
- Consider migrating to HTTP Events API if needed
- AWS RDS and ElastiCache provide scalability

---

## 4. Testing Strategy

### 4.1 Manual Testing (Primary for Phase 1)

**Setup & Startup Tests:**
1. Clone repository, copy `.env.example` to `.env`, fill in Slack tokens
2. Run `docker-compose up --build`
3. Verify logs show successful startup sequence:
   - "configuration_loaded"
   - "database_connected"
   - "redis_connected"
   - "slack_bot_starting" (slack-bot service)
   - "fastapi_starting" (api service)

**Health Endpoint Tests:**
1. `curl http://localhost:8000/health` → Returns `{"status": "healthy", "service": "agent-for-ac"}`
2. `curl http://localhost:8000/readiness` → Returns `{"status": "ready", "postgres": "connected", "redis": "connected"}`
3. Stop postgres: `docker-compose stop postgres`
4. `curl http://localhost:8000/readiness` → Returns `{"status": "not ready", "postgres": "disconnected", ...}`
5. Restart postgres: `docker-compose start postgres`

**Slack Bot Tests:**
1. Open Slack workspace, find bot in Apps
2. Send DM: `/ac-agent` → Receives "Hello! I'm Agent for AC..." message
3. Send DM: `/ac-agent health` → Receives formatted health status with checkmarks
4. Send DM: `/ac-agent test command` → Receives "I received your command: `test command`..."
5. Try command in channel → Receives "Please use this command in a direct message"

**Error Scenario Tests:**
1. Remove `SLACK_BOT_TOKEN` from `.env`, restart → Logs "SLACK_BOT_TOKEN is required...", exits
2. Set invalid `POSTGRES_URL`, restart → Logs "Failed to connect to PostgreSQL...", exits
3. Set invalid Slack token, restart → Logs "Failed to connect to Slack: invalid_auth", exits

### 4.2 Unit Testing (Minimal for Phase 1)

**Configuration Tests (tests/unit/test_config.py):**
```python
import pytest
from pydantic import ValidationError
from src.config.settings import Settings

def test_missing_slack_bot_token():
    """Test that missing SLACK_BOT_TOKEN raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            slack_app_token="xapp-test",
            postgres_url="postgresql://test",
        )
    assert "slack_bot_token" in str(exc_info.value)

def test_invalid_log_level():
    """Test that invalid LOG_LEVEL raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            slack_bot_token="xoxb-test",
            slack_app_token="xapp-test",
            postgres_url="postgresql://test",
            log_level="INVALID"
        )
    assert "log_level must be one of" in str(exc_info.value)
```

**Health Check Tests:**
```python
import pytest
from src.services.health_check import check_database, check_redis
from src.core.database import init_database
from src.core.cache import init_redis

@pytest.mark.asyncio
async def test_database_health_check_when_connected():
    """Test database health check returns 'connected' when DB is available."""
    await init_database("sqlite+aiosqlite:///:memory:")
    status = await check_database()
    assert status == "connected"

@pytest.mark.asyncio
async def test_redis_health_check_when_disconnected():
    """Test Redis health check returns 'disconnected' when Redis not initialized."""
    status = await check_redis()
    assert status == "disconnected"
```

### 4.3 Future Testing (Phase 2+)

- Integration tests with test Slack workspace
- API integration tests with TestClient
- End-to-end tests for full command workflows
- Load testing for Socket Mode connection limits
- CI/CD pipeline with automated tests

---

## 5. Implementation Checklist

### 5.1 Initial Setup
- [ ] Initialize uv project: `uv init --lib agent-for-ac`
- [ ] Add dependencies to pyproject.toml
- [ ] Create project structure (src/, tests/, etc.)
- [ ] Create .gitignore (include .env, __pycache__, etc.)
- [ ] Create .env.example with all required variables

### 5.2 Core Infrastructure
- [ ] Implement src/config/settings.py with Pydantic validation
- [ ] Implement src/core/logging.py with structlog configuration
- [ ] Implement src/core/exceptions.py with custom exceptions
- [ ] Implement src/core/database.py with async PostgreSQL connection
- [ ] Implement src/core/cache.py with async Redis connection

### 5.3 FastAPI Application
- [ ] Implement src/schemas/health.py with response models
- [ ] Implement src/services/health_check.py with DB/Redis checks
- [ ] Implement src/api/routes/health.py with /health and /readiness endpoints
- [ ] Implement src/api/app.py with FastAPI factory
- [ ] Test FastAPI startup locally: `uv run uvicorn src.api.app:create_app --factory --reload`

### 5.4 Slack Bot Application
- [ ] Implement src/slack/handlers/commands.py with /ac-agent handler
- [ ] Implement src/slack/app.py with Slack Bolt factory and startup sequence
- [ ] Test Slack bot startup locally: `uv run python -m src.slack.app`
- [ ] Verify Socket Mode connection in Slack workspace

### 5.5 Docker & Orchestration
- [ ] Create Dockerfile with uv installation
- [ ] Create docker-compose.yml with all services
- [ ] Test: `docker-compose up --build`
- [ ] Verify all services start successfully
- [ ] Verify volume persistence (restart, check data still exists)

### 5.6 Testing & Validation
- [ ] Write unit tests for configuration validation
- [ ] Write unit tests for health check services
- [ ] Perform manual testing checklist (all scenarios above)
- [ ] Test error scenarios (missing env vars, connection failures)
- [ ] Document any issues found and resolved

### 5.7 Documentation
- [ ] Write README.md with setup instructions
- [ ] Document environment variables in .env.example
- [ ] Add inline code comments for complex logic
- [ ] Create development guide for team
