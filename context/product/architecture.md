# System Architecture Overview: Agent for AC

---

## 1. Application & Technology Stack

### Backend Framework
- **Python 3.12+** with **FastAPI**
  - Async support for handling Slack events and AI API calls
  - Rich ecosystem for integrations
  - Fast development speed for MVP
  - Excellent for AI/ML workloads
  - Type hints and Pydantic for validation

### Slack Integration
- **Slack Bolt for Python**
  - Official framework for Slack apps
  - Handles events, slash commands, and interactive components
  - Built-in Socket Mode support for local development
  - Async support with `AsyncApp` and `AsyncSocketModeHandler`

### AI/LLM Orchestration
- **LangChain + LangGraph**
  - **LangChain:** Core framework for building LLM applications
  - **LangGraph:** State machine and workflow orchestration for multi-agent systems
  - **Agent Architecture:** Six specialized agents working together:
    - **Orchestrator Agent:** Analyzes ticket and routes workflow
    - **Information Gatherer Agent:** Asks clarifying questions (max 5)
    - **Generator Agent:** Generates AC in multiple formats (Checklist, BDD, Free)
    - **Evaluator Agent:** Scores quality (1-10 scale) and provides feedback
    - **Refiner Agent:** Classifies user intent for chat-based AC refinement
    - **Modifier Agent:** Applies surgical modifications to existing AC
  - **Interactive Chat Refinement:** Natural language AC modification after generation
  - **Prompt Management:** Version-controlled prompt templates (6 files)
  - **Memory & State:** Managed via LangGraph state machine

### LLM Providers
Dual provider support with abstraction layer:
- **Anthropic API** (Primary)
  - Direct API access via `anthropic` Python SDK
  - Claude 3.5 Sonnet/Haiku models
  - Fast response times
  - Simple authentication with API key

- **AWS Bedrock** (Alternative)
  - Access to multiple models (Claude, Llama, Mistral)
  - Integrated with AWS infrastructure
  - Managed service with AWS authentication
  - `boto3` for API access

**Provider Abstraction:**
```python
# src/agents/llm/provider.py
LLMProvider = Literal["anthropic", "bedrock"]

def get_llm(provider: LLMProvider, model_name: str) -> BaseChatModel:
    # Returns appropriate ChatAnthropic or ChatBedrock instance
```

### Package Management
- **uv** - Fast Python package and dependency management
  - Modern alternative to pip/poetry
  - Instant dependency resolution
  - Project-aware environments

---

## 2. Data & Persistence

### Stateless Architecture (Current)

The application is designed to be **fully stateless** for simplicity and ease of deployment:

**No Database Required:**
- Workflow state is managed in-memory during active conversations
- User interactions tracked via `_active_workflows` dictionary (in-memory)
- Conversation context maintained within Slack threads
- Jira ticket data fetched on-demand via API calls

**No Caching Layer Required:**
- Jira API calls made as needed (typically 2-3 per workflow)
- Slack handles message history and threading natively
- LLM responses generated fresh for each request

**Benefits of Stateless Design:**
- Simpler deployment (fewer services to manage)
- No database migrations or schema management
- Easy horizontal scaling (stateless services scale trivially)
- Lower operational costs (no database hosting)
- Faster local development setup
- No data persistence concerns

**Workflow State Management:**
```python
# In-memory storage for active workflows
_active_workflows: dict[str, WorkflowContext] = {}

# Workflow context contains:
# - stage: "format_selection" | "gathering_info" | "approval"
# - ticket: JiraTicket object
# - detection_result: ACDetectionResult
# - jira_service: JiraService instance
```

**State Lifecycle:**
1. User mentions bot with Jira link → workflow created in `_active_workflows`
2. User interacts through Slack thread → state updated
3. User approves/cancels → workflow removed from dictionary

### Future Considerations (If Needed)

If persistent storage becomes necessary in the future:
- **Analytics/Reporting:** Track AC generation history, quality metrics over time
- **User Preferences:** Store per-user or per-workspace settings
- **Rate Limiting:** Track API usage across sessions
- **Audit Trail:** Record all AC generations for compliance

**Potential technologies:**
- PostgreSQL for relational data
- Redis for caching and session state
- SQLite for simple local storage

---

## 3. Infrastructure & Deployment

### Current: Local Development & Deployment

**Container Orchestration:** Docker Compose
- Single `docker-compose.yml` for all services
- **Services:**
  - `api` - FastAPI server (port 8000)
  - `slack-bot` - Slack bot application

**Local Environment:** Developer machine with Docker Desktop
- Runs on macOS/Linux/Windows
- No cloud costs during development
- Hot reload enabled for both services

**Slack Connection:** Socket Mode (WebSocket)
- Uses Bot Token (`xoxb-...`) for Slack Web API calls
- Uses App-Level Token (`xapp-...`) for WebSocket connection
- Bot connects outbound to Slack (firewall-friendly)
- No need for public URLs, tunneling, or ngrok
- Ideal for local development and small deployments

**Configuration Management:**
- Environment variables via `.env` file
- `python-dotenv` for loading environment
- `pydantic-settings` for type-safe configuration
- All secrets in `.env` (not committed to git)

### Future: Production Cloud Deployment (Phase 3)

**Cloud Provider:** AWS
- Mature managed services ecosystem
- Good integration with Bedrock for LLM
- Cost-effective for small-medium workloads

**Container Hosting:** AWS ECS with Fargate
- Serverless container hosting
- Auto-scaling based on load
- Direct Docker image deployment
- No server management required
- **Containers in Production:**
  - `slack-bot` - Main Slack bot application
  - `api` - FastAPI health/monitoring endpoints

**Slack Connection:** Socket Mode or HTTP Events API
- Can continue using Socket Mode (WebSocket)
- Option to migrate to HTTP Events API for better scalability
- HTTP mode requires public URL (ALB/API Gateway)

**Deployment Architecture (Future):**
```
┌─────────────────────────────────────┐
│         AWS ECS Cluster             │
│  ┌────────────┐   ┌──────────────┐ │
│  │ slack-bot  │   │     api      │ │
│  │  (Fargate) │   │  (Fargate)   │ │
│  └────────────┘   └──────────────┘ │
└─────────────────────────────────────┘
         │                  │
         │                  ▼
         │          ┌──────────────┐
         │          │     ALB      │
         │          │ (Port 8000)  │
         │          └──────────────┘
         ▼
   ┌──────────┐
   │  Slack   │
   │   API    │
   └──────────┘
```

---

## 4. External Services & APIs

### Slack Integration

**Library:** Slack Bolt for Python (`slack_bolt`)
- Async-first design with `AsyncApp`
- Event-driven architecture

**Authentication:** OAuth 2.0
- Bot Token (`SLACK_BOT_TOKEN`) - API calls to Slack Web API
- App-Level Token (`SLACK_APP_TOKEN`) - WebSocket connection for Socket Mode

**APIs Used:**
- **Events API** (via Socket Mode) - Receives events like `app_mention`, `message`
- **Web API** - Posting messages with `chat.postMessage`
- **Interactive Components** - Buttons and menus (future enhancement)

**Capabilities Implemented:**
- Slash commands (`/ac-agent`)
- Direct messages (DM support)
- App mentions (`@Agent for AC`) in channels
- Thread support - bot creates and replies in threads
- Real-time bidirectional communication via WebSocket

**Event Handlers:**
```python
# src/slack/handlers/events.py
@app.event("app_mention")  # When bot is mentioned in channel
@app.event("message")       # For DM conversations

# Slash commands
@app.command("/ac-agent")   # Command handler
```

### Jira Integration

**Integration Method:** Direct Jira Cloud REST API via `httpx`
- Async HTTP client for non-blocking I/O
- Custom service layer (`src/services/jira.py`)

**Authentication:** API Token (Basic Auth)
- Uses email + API token for authentication
- Workspace-level access (single token for all users)
- Simple setup, no OAuth callback required

**Configuration:**
```bash
JIRA_SITE_URL=https://company.atlassian.net
JIRA_USER_EMAIL=email@company.com
JIRA_API_TOKEN=ATT...
```

**API Endpoints Used:**
- `GET /rest/api/3/issue/{issueKey}` - Fetch ticket details
- `PUT /rest/api/3/issue/{issueKey}` - Update ticket (write AC)
- `GET /rest/api/3/issue/{issueKey}/comment` - Get comments (future)
- `GET /rest/api/3/search` - Search with JQL (future)

**Operations:**
1. **Read Ticket:** Fetch title, description, status, type, existing AC
2. **Detect AC:** Pattern matching to identify existing acceptance criteria
3. **Update Ticket:** Append or replace AC in description field

**Supported Ticket Types:** Story, Task

**Error Handling:**
- `JiraConnectionError` - Network/connectivity issues
- `JiraTicketNotFoundError` - Invalid ticket key
- `JiraPermissionError` - Insufficient permissions
- `JiraInvalidTicketLinkError` - Malformed URL/key
- `JiraUnsupportedTicketTypeError` - Epic or other unsupported types

**API Client Architecture:**
```
Slack Handler
     ↓
JiraService (singleton)
     ↓
httpx AsyncClient
     ↓
Jira REST API
```

### LLM Services

**Orchestration Framework:** LangChain + LangGraph

**LLM Provider Configuration:**
```bash
LLM_PROVIDER=anthropic  # or "bedrock"

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Models
LLM_MODEL_ORCHESTRATOR=claude-3-5-haiku-20241022
LLM_MODEL_MAIN=claude-3-7-sonnet-20250219
```

**Agent System:**
```
┌──────────────────────────────────────────┐
│         LangGraph Workflow               │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │      Orchestrator Agent            │ │
│  │  (Analyzes ticket, routes flow)    │ │
│  └───────────┬────────────────────────┘ │
│              │                           │
│    ┌─────────┴─────────┐                │
│    ▼                   ▼                 │
│  ┌─────────────┐  ┌────────────────┐    │
│  │ Information │  │   Generator    │    │
│  │  Gatherer   │  │     Agent      │    │
│  │   Agent     │  │ (Checklist/BDD)│    │
│  └──────┬──────┘  └────────┬───────┘    │
│         │                  │             │
│         └──────────┬───────┘             │
│                    ▼                     │
│             ┌──────────────┐             │
│             │  Evaluator   │             │
│             │    Agent     │             │
│             │ (Quality 1-10)│            │
│             └──────────────┘             │
└──────────────────────────────────────────┘
```

**Agent Responsibilities:**
1. **Orchestrator** - Decision making, workflow routing
2. **Information Gatherer** - Ask up to 5 clarifying questions
3. **Generator** - Create AC in selected format
4. **Evaluator** - Score quality and suggest improvements

**Model Selection:**
- Orchestrator: Fast model (Haiku) for quick routing decisions
- Main agents: Powerful model (Sonnet) for generation and evaluation

**Provider Abstraction Layer:**
```python
# src/agents/llm/provider.py
class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"

def get_llm(provider, model_name) -> BaseChatModel:
    if provider == "anthropic":
        return ChatAnthropic(model=model_name, api_key=...)
    elif provider == "bedrock":
        return ChatBedrock(model_id=model_name, region=...)
```

---

## 5. Observability & Monitoring

### Current: Local Development

**Logging:**
- **Library:** `structlog` for structured JSON logging
- **Format:** JSON-formatted logs with context
- **Levels:** Configurable via `LOG_LEVEL` env var
- **Output:** Console (stdout/stderr)
- **Clean Logs:** INFO level by default - no verbose ping-pong or HTTP debug messages

**Example structured log:**
```json
{
  "event": "jira_ticket_retrieved",
  "ticket_key": "PROJ-123",
  "ticket_type": "Story",
  "status": "To Do",
  "level": "info",
  "timestamp": "2025-12-10T10:30:45.123456Z"
}
```

**Logging Configuration:**
```python
# src/core/logging.py
import structlog

logger = structlog.get_logger()
logger.info("event_name", field1="value1", field2="value2")
```

**Log Levels:**
- `DEBUG` - Verbose output (Slack ping-pong, HTTP requests)
- `INFO` - Standard operations (default, clean output)
- `WARNING` - Warnings and recoverable errors
- `ERROR` - Errors requiring attention
- `CRITICAL` - System failures

**Error Tracking:**
- **Sentry** (optional) - Free tier up to 5,000 events/month
- Configured via `SENTRY_DSN` in `.env`
- Automatic exception capture and stack traces
- Works seamlessly with local development
- Error grouping and release tracking

**Health Checks:**
- FastAPI health endpoint (`GET /health`)
- Basic service availability monitoring
- Jira connectivity verification

**Metrics (Logged):**
- Requests processed
- Error counts and types
- Processing times for AC generation
- Jira/Slack/LLM API call statistics

### Future: Production (Phase 3)

**Logging:**
- AWS CloudWatch Logs (automatic from ECS/Fargate)
- Structured JSON logs via structlog
- Log aggregation and retention policies
- Searchable and filterable logs
- Log streaming to analysis tools

**Error Tracking:**
- Sentry (upgrade tier if needed)
- Real-time error alerts
- Performance monitoring
- Release tracking and error attribution
- User impact analysis

**Metrics:**
- AWS CloudWatch Metrics or Prometheus
- API response times and throughput
- Jira/Slack API call rates and latency
- LLM token usage and costs
- Success/failure rates per workflow stage

**Alerting:**
- Sentry alerts for critical errors
- AWS SNS for infrastructure alerts
- Slack notifications for system events
- PagerDuty integration for on-call

**Dashboards:**
- AWS CloudWatch Dashboards for infrastructure
- Sentry performance dashboards
- Custom business metrics:
  - AC generated per day/week
  - Average quality scores
  - User engagement metrics
  - Time saved per ticket

---

## 6. Security & Best Practices

### Secrets Management
- All secrets in `.env` file (not committed)
- `.env.example` template without actual secrets
- Environment variables validated with Pydantic
- No secrets in code or logs (redacted automatically)

### API Security
- **Jira:** API Token authentication (user-level permissions)
- **Slack:** OAuth 2.0 with Bot + App-Level tokens
- **LLM:** API key authentication (Anthropic) or IAM roles (Bedrock)

### Input Validation
- Pydantic models for all data validation
- Type hints throughout codebase
- Custom exception hierarchy for error handling
- Jira ticket link validation before processing

### Error Handling
- Custom exception classes for different error types
- Graceful degradation - bot shows user-friendly errors
- Sentry integration for tracking and debugging
- Never expose sensitive data in error messages

---

## 7. Development Workflow

### Local Setup
1. Install Docker Desktop and uv
2. Copy `.env.example` to `.env` and configure
3. Run `docker compose up`
4. Bot connects to Slack automatically

### Code Changes
- Edit code in `src/`
- Changes reflected immediately (hot reload)
- Watch logs: `docker compose logs -f slack-bot`

### Adding Dependencies
```bash
uv add package-name
docker compose up --build
```

### Testing
```bash
uv run python test_with_jira_ticket.py
uv run python test_ai_orchestration.py
```

### Debugging
- Check logs: `docker compose logs -f`
- Set `LOG_LEVEL=DEBUG` for verbose output
- Use Sentry for production error tracking

---

## 8. Architecture Decisions

### Why Stateless?
- **Simpler:** No database setup, migrations, or schema management
- **Scalable:** Easy horizontal scaling without shared state
- **Cost-effective:** No database hosting costs
- **Fast iteration:** Faster development and deployment cycles
- **Reliable:** Fewer points of failure

### Why Socket Mode?
- **Firewall-friendly:** Outbound WebSocket connection only
- **Local development:** No public URL or tunneling needed
- **Simple setup:** No webhook URL configuration
- **Real-time:** Bidirectional communication for interactive workflows

### Why Multi-Agent System?
- **Modularity:** Each agent has clear responsibility
- **Flexibility:** Easy to add/modify agents
- **Quality:** Specialized agents produce better results
- **Testability:** Agents can be tested independently

### Why Dual LLM Provider Support?
- **Flexibility:** Choose based on requirements and costs
- **Redundancy:** Fallback if one provider has issues
- **Performance:** Use different models for different tasks
- **Cost optimization:** Use cheaper models where appropriate

---

## 9. Future Enhancements

### Phase 2: Context Enrichment
- **Slack Context Gathering:** Scan related conversations
- **Enhanced Q&A:** Interactive buttons/menus for questions
- **Block Kit UI:** Rich formatting for better UX

### Phase 3: Production Readiness
- **Cloud Deployment:** AWS ECS/Fargate
- **Monitoring:** CloudWatch + Sentry dashboards
- **Performance:** Response time optimization
- **Analytics:** Usage metrics and insights

### Future Considerations
- **Database:** Add if persistent storage needed
- **Caching:** Redis for frequently accessed data
- **Multi-workspace:** Support multiple Slack workspaces
- **API Access:** REST API for programmatic access
- **Slack App Directory:** Public distribution
