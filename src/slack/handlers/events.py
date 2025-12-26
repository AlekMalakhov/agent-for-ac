"""Slack event handlers for message interactions."""

import structlog
from slack_bolt.async_app import AsyncApp

from src.slack.handlers.commands import (
    _active_workflows,
    handle_chat_refinement,
    handle_format_selection,
    handle_health_check,
    handle_jira_ticket,
    handle_user_answer,
)

logger = structlog.get_logger()


def _build_say_for_event(say, event, force_thread=False):
    """
    Build a say-like function that replies appropriately for the event.

    If the incoming event is part of a thread, responses will be posted
    back to the same thread. If force_thread is True and the event is in
    a channel, responses will create a new thread using the event's ts.
    Otherwise, responses are posted as regular channel or DM messages.

    Args:
        say: Slack say function
        event: Slack event payload
        force_thread: If True, force replies to be in a thread (using event ts)
    """
    thread_ts = event.get("thread_ts")
    channel_type = event.get("channel_type")

    # If message is already in a thread, reply to that thread
    if thread_ts:
        async def _say_threaded(message: str) -> None:
            await say(text=message, thread_ts=thread_ts)
        return _say_threaded

    # If force_thread is True and we're in a channel (not DM), start a new thread
    if force_thread and channel_type != "im":
        event_ts = event.get("ts")
        async def _say_new_thread(message: str) -> None:
            await say(text=message, thread_ts=event_ts)
        return _say_new_thread

    # Default: reply without thread
    async def _say(message: str) -> None:
        await say(message)
    return _say


async def handle_dm_message(event, say):
    """
    Handle message events for multi-step workflow interactions.

    This handler processes user responses during:
    - Format selection
    - Information gathering (answering questions)
    - AC approval/rejection

    Args:
        event: Slack event payload
        say: Function to send messages
    """
    # Ignore bot messages to prevent loops
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    user_id = event.get("user")
    text = event.get("text", "").strip()

    # Check if user has an active workflow
    workflow_context = _active_workflows.get(user_id)
    if not workflow_context:
        # No active workflow - ignore message or show help
        return

    stage = workflow_context.get("stage")
    say_for_event = _build_say_for_event(say, event)

    logger.info(
        "dm_message_received",
        user_id=user_id,
        stage=stage,
        text_preview=text[:50] if text else "",
    )

    if stage == "format_selection":
        await handle_format_selection(say_for_event, user_id, text)

    elif stage == "gathering_info":
        await handle_user_answer(say_for_event, user_id, text)

    elif stage == "chat_refinement":
        await handle_chat_refinement(say_for_event, user_id, text)


async def handle_app_mention(event, say):
    """
    Handle app_mention events to support usage in channels and threads.

    Supports:
    - "@bot health" to check system status
    - "@bot <jira-link or key>" to start AC workflow (creates thread in channels)
    - Workflow responses when user has an active workflow
    """
    # Ignore bot messages to prevent loops
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    user_id = event.get("user")
    raw_text = event.get("text", "") or ""

    logger.info(
        "app_mention_received",
        user_id=user_id,
        text_preview=raw_text[:50] if raw_text else "",
    )

    # app_mention text usually starts with "<@BOTID> ..."
    parts = raw_text.split(">", 1)
    command_text = parts[1].strip() if len(parts) > 1 else raw_text.strip()

    # Check if user has an active workflow - if so, treat this as a workflow response
    workflow_context = _active_workflows.get(user_id)
    if workflow_context:
        stage = workflow_context.get("stage")
        logger.info(
            "app_mention_workflow_response",
            user_id=user_id,
            stage=stage,
            text_preview=command_text[:50] if command_text else "",
        )

        # For workflow responses, continue in the existing thread context
        say_for_event = _build_say_for_event(say, event)

        if stage == "format_selection":
            await handle_format_selection(say_for_event, user_id, command_text)
            return
        elif stage == "gathering_info":
            await handle_user_answer(say_for_event, user_id, command_text)
            return
        elif stage == "chat_refinement":
            await handle_chat_refinement(say_for_event, user_id, command_text)
            return

    # No active workflow - proceed with normal command handling
    # For simple commands like health, don't force thread
    say_for_event = _build_say_for_event(say, event)

    if not command_text:
        await say_for_event(
            "Hi! You can mention me with `health` or a Jira link/key, for example:\n"
            "- `@Agent for AC health`\n"
            "- `@Agent for AC PROJ-123`"
        )
        return

    if command_text.lower() == "health":
        await handle_health_check(say_for_event)
        return

    # For Jira ticket processing, force thread creation in channels
    say_for_event_threaded = _build_say_for_event(say, event, force_thread=True)
    await handle_jira_ticket(say_for_event_threaded, command_text, user_id)


def register(app: AsyncApp) -> None:
    """
    Register message and mention event handlers with the Slack app.

    Args:
        app: AsyncApp instance to register handlers on
    """
    # Handle all user messages (DMs and channels) for active workflows
    app.event("message")(handle_dm_message)
    # Handle @mentions in channels and threads
    app.event("app_mention")(handle_app_mention)
    logger.info("event_handlers_registered")
