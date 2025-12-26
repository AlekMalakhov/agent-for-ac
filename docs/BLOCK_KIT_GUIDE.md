# Block Kit Integration Guide

This guide shows how to enhance the Slack bot with Block Kit for richer, interactive responses.

## Why Block Kit?

**Current approach:** Plain text/markdown responses
**Block Kit approach:** Structured, interactive UI components

### Benefits

1. **Better Visual Hierarchy** - Headers, sections, dividers
2. **Interactive Actions** - Buttons, menus, date pickers
3. **Rich Formatting** - Code blocks, quotes, images
4. **Professional UX** - Consistent with modern Slack apps
5. **Actionable Responses** - Users can click instead of typing

---

## Block Kit Basics

### Simple Text Response (Current)
```python
await say("Hello! This is a simple message.")
```

### Block Kit Response (Enhanced)
```python
await say({
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "✨ Hello!"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This is an *enhanced* message with _formatting_."
            }
        }
    ]
})
```

---

## Upgrading Existing Responses

### 1. Health Check Command

#### Current Implementation
```python
message = (
    f"{overall_icon} *System Health Status*\n\n"
    f"{db_icon} PostgreSQL: `{db_status}`\n"
    f"{redis_icon} Redis: `{redis_status}`\n"
)
await say(message)
```

#### Enhanced with Block Kit
```python
async def handle_health_check(say) -> None:
    """Handle health check command with Block Kit UI."""
    db_status = await check_database()
    redis_status = await check_redis()
    all_connected = db_status == "connected" and redis_status == "connected"

    # Icons
    db_icon = "✅" if db_status == "connected" else "❌"
    redis_icon = "✅" if redis_status == "connected" else "❌"
    overall_icon = "✅" if all_connected else "⚠️"

    # Build Block Kit response
    await say({
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{overall_icon} System Health Status",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*PostgreSQL*\n{db_icon} `{db_status}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Redis*\n{redis_icon} `{redis_status}`"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_All systems operational._" if all_connected else "_Some systems are experiencing issues._"
                    }
                ]
            }
        ]
    })
```

**Result:** Much cleaner layout with proper visual hierarchy.

---

### 2. Welcome Message

#### Current Implementation
```python
welcome_message = (
    "👋 Hello! I'm the Agent for AC bot.\n\n"
    "I can help you generate and evaluate acceptance criteria for Jira tickets.\n\n"
    "*Available commands:*\n"
    "• `/ac-agent health` - Check system health\n"
    "• `/ac-agent <jira-link>` - Generate or evaluate acceptance criteria (coming soon)\n\n"
    "Try sending me a command!"
)
await say(welcome_message)
```

#### Enhanced with Block Kit
```python
async def send_welcome_message(say) -> None:
    """Send welcome message with Block Kit."""
    await say({
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👋 Welcome to Agent for AC!",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "I can help you generate and evaluate *acceptance criteria* for Jira tickets."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📋 Available Commands*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "`/ac-agent health`\nCheck system health status"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "`/ac-agent <jira-link>`\nGenerate or evaluate acceptance criteria _(coming soon)_"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 *Tip:* Try `/ac-agent health` to get started!"
                    }
                ]
            }
        ]
    })
```

---

## Phase 2: AC Generation with Interactive Buttons

### Scenario: User provides Jira link, bot generates AC

```python
async def handle_ac_generation(say, jira_url: str, user_id: str) -> None:
    """Generate AC and present with interactive buttons."""

    # TODO: Call your AI service to generate AC
    # For now, using placeholder
    generated_ac = [
        "User can log in with email and password",
        "System validates credentials against database",
        "Invalid login attempts show clear error message",
        "Successful login redirects to dashboard",
        "Failed login after 3 attempts locks account for 15 minutes"
    ]

    quality_score = 8
    quality_feedback = [
        "✅ Criteria are clear and testable",
        "✅ Covers happy path and error cases",
        "⚠️ Consider adding security requirements"
    ]

    # Build rich response with buttons
    await say({
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "✨ Generated Acceptance Criteria",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Jira Ticket:* <{jira_url}|View in Jira>"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📋 Acceptance Criteria*"
                }
            },
            # List each criterion
            *[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {criterion}"
                    }
                }
                for criterion in generated_ac
            ],
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📊 Quality Assessment*\n*Score:* {quality_score}/10"
                }
            },
            *[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": feedback
                    }
                }
                for feedback in quality_feedback
            ],
            {
                "type": "divider"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Approve & Add to Jira",
                            "emoji": True
                        },
                        "style": "primary",
                        "action_id": "approve_ac",
                        "value": jira_url
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔄 Regenerate",
                            "emoji": True
                        },
                        "action_id": "regenerate_ac",
                        "value": jira_url
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "💬 Add Context",
                            "emoji": True
                        },
                        "action_id": "add_context",
                        "value": jira_url
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated for <@{user_id}> • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                ]
            }
        ]
    })
```

---

## Handling Button Interactions

When users click buttons, you need to handle those actions:

```python
# In src/slack/handlers/actions.py (new file)

import structlog
from slack_bolt.async_app import AsyncApp

logger = structlog.get_logger()


async def handle_approve_ac(ack, body, say, client):
    """Handle approve button click."""
    await ack()

    jira_url = body["actions"][0]["value"]
    user_id = body["user"]["id"]

    logger.info("ac_approved", user_id=user_id, jira_url=jira_url)

    # TODO: Update Jira ticket with AC
    # For now, just confirm
    await say({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Approved!* Acceptance criteria added to <{jira_url}|Jira ticket>."
                }
            }
        ],
        "thread_ts": body["message"]["ts"]  # Reply in thread
    })


async def handle_regenerate_ac(ack, body, say):
    """Handle regenerate button click."""
    await ack()

    jira_url = body["actions"][0]["value"]

    await say({
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🔄 Regenerating acceptance criteria..."
                }
            }
        ],
        "thread_ts": body["message"]["ts"]
    })

    # TODO: Call AI service again with different parameters
    # Then send new AC response


async def handle_add_context(ack, body, client):
    """Handle add context button - opens a modal."""
    await ack()

    jira_url = body["actions"][0]["value"]

    # Open modal for additional context
    await client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "context_modal",
            "title": {
                "type": "plain_text",
                "text": "Add Context"
            },
            "submit": {
                "type": "plain_text",
                "text": "Submit"
            },
            "blocks": [
                {
                    "type": "input",
                    "block_id": "context_input",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "context_text",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Provide additional context about this feature..."
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Additional Context"
                    }
                },
                {
                    "type": "input",
                    "block_id": "target_audience",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "audience_text",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g., Internal users, Customers, Admins"
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Target Audience"
                    }
                }
            ],
            "private_metadata": jira_url  # Pass jira_url to modal submission
        }
    )


def register_actions(app: AsyncApp) -> None:
    """Register all action handlers."""
    app.action("approve_ac")(handle_approve_ac)
    app.action("regenerate_ac")(handle_regenerate_ac)
    app.action("add_context")(handle_add_context)

    logger.info("action_handlers_registered")
```

---

## Registering Action Handlers

Update `src/slack/app.py`:

```python
from src.slack.handlers import commands, actions  # Add actions import

def create_slack_app() -> tuple[AsyncApp, AsyncSocketModeHandler]:
    """Create Slack app and Socket Mode handler."""
    settings = get_settings()

    try:
        app = AsyncApp(token=settings.slack_bot_token)

        # Register handlers
        commands.register(app)
        actions.register_actions(app)  # Add this line

        handler = AsyncSocketModeHandler(app, settings.slack_app_token)
        logger.info("slack_app_created")

        return app, handler
    except Exception as e:
        raise SlackConnectionError(f"Failed to create Slack app: {str(e)}") from e
```

---

## Block Kit Builder Tool

Slack provides a visual builder for creating Block Kit layouts:

**🔗 https://app.slack.com/block-kit-builder**

You can:
1. Design your UI visually
2. See live preview
3. Copy the JSON
4. Paste into your code

**Highly recommended** for designing complex layouts!

---

## Best Practices

### 1. Always Include Fallback Text
```python
await say({
    "text": "System health check results",  # Fallback for notifications
    "blocks": [...]
})
```

### 2. Use Context for Metadata
```python
{
    "type": "context",
    "elements": [
        {
            "type": "mrkdwn",
            "text": f"Generated by Agent for AC • {timestamp}"
        }
    ]
}
```

### 3. Limit Blocks (Max 50)
Don't exceed 50 blocks per message. For long content, use:
- Pagination with "Load more" button
- Thread replies
- Multiple messages

### 4. Use Appropriate Button Styles
- `"style": "primary"` - Main action (green)
- `"style": "danger"` - Destructive action (red)
- No style - Secondary action (gray)

### 5. Provide Loading States
```python
# Initial message
await say({"blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "⏳ Generating..."}}]})

# Update message after processing
await client.chat_update(
    channel=channel_id,
    ts=message_ts,
    blocks=[...]  # Updated blocks
)
```

---

## Migration Path

### Phase 2.1: Update Existing Commands
1. Convert health check to Block Kit ✅ Easy
2. Convert welcome message to Block Kit ✅ Easy
3. Add visual improvements (dividers, headers)

**Estimated effort:** 2-3 hours

### Phase 2.2: Add Interactive AC Generation
1. Create AC response with buttons
2. Implement action handlers
3. Add modal for context gathering
4. Implement Jira integration for approval

**Estimated effort:** 1-2 days

### Phase 2.3: Advanced Features
1. Add progress indicators
2. Implement editing capabilities
3. Add comparison view (before/after)
4. Thread-based conversations

**Estimated effort:** 2-3 days

---

## Example: Complete Flow

### User Journey with Block Kit

1. **User:** `/ac-agent https://jira.company.com/browse/PROJ-123`

2. **Bot:** Shows loading state
   ```
   ⏳ Analyzing Jira ticket...
   ```

3. **Bot:** Updates with generated AC (rich Block Kit layout)
   - Header with ticket info
   - Generated criteria (bulleted, formatted)
   - Quality score with visual indicator
   - Action buttons: Approve, Regenerate, Add Context

4. **User:** Clicks "Add Context" button

5. **Bot:** Opens modal with form fields
   - Additional context (textarea)
   - Target audience (text input)

6. **User:** Submits modal

7. **Bot:** Regenerates with new context
   - Shows updated AC
   - Maintains conversation in thread

8. **User:** Clicks "Approve & Add to Jira"

9. **Bot:** Updates Jira ticket
   - Confirms in thread
   - Provides link to updated ticket
   - Shows timestamp and who approved

---

## Testing Block Kit Responses

### 1. Unit Testing
```python
# tests/unit/test_block_kit.py

def test_health_check_blocks_structure():
    """Test health check returns valid Block Kit structure."""
    blocks = build_health_check_blocks("connected", "connected")

    assert blocks[0]["type"] == "header"
    assert "System Health Status" in blocks[0]["text"]["text"]
    assert len(blocks) >= 3
```

### 2. Visual Testing
Use the Block Kit Builder to paste your JSON and verify it renders correctly.

### 3. Integration Testing
```python
async def test_health_command_with_blocks():
    """Test /ac-agent health returns Block Kit response."""
    # Mock say function
    mock_say = AsyncMock()

    # Call handler
    await handle_health_check(mock_say)

    # Verify Block Kit structure
    call_args = mock_say.call_args[0][0]
    assert "blocks" in call_args
    assert isinstance(call_args["blocks"], list)
```

---

## Resources

**Official Documentation:**
- [Block Kit Reference](https://api.slack.com/block-kit)
- [Block Kit Builder](https://app.slack.com/block-kit-builder)
- [Interactive Components](https://api.slack.com/interactivity)
- [Modals](https://api.slack.com/surfaces/modals)

**Examples:**
- [Block Kit Samples](https://api.slack.com/block-kit/building)
- [slack-bolt Examples](https://github.com/slackapi/bolt-python/tree/main/examples)

**Best Practices:**
- [Message Guidelines](https://api.slack.com/best-practices/message-guidelines)
- [Accessibility](https://api.slack.com/best-practices/accessibility)

---

## Summary

Block Kit will transform your bot from functional to delightful:

✅ **Better UX** - Visual hierarchy, clear sections
✅ **Interactive** - Buttons replace typing commands
✅ **Professional** - Matches modern Slack apps
✅ **Actionable** - Users can click, not just read
✅ **Scalable** - Easy to add new features

**Recommendation:** Start with Phase 2.1 (upgrading existing commands) when you begin Phase 2 development. It's a small investment with big UX payoff.
