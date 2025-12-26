"""Slack context gathering service for enriching AC generation."""

import re
from datetime import datetime, timedelta, timezone

import structlog
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from src.agents.llm.provider import get_llm_provider
from src.agents.prompts import format_prompt
from src.config.settings import get_settings
from src.core.exceptions import SlackAPIError, SlackScopeError
from src.schemas.slack_context import (
    SlackContextResult,
    SlackMessage,
    SlackThread,
)

logger = structlog.get_logger()


class SlackContextService:
    """
    Service for gathering Slack context related to Jira tickets.

    This service scans channels for discussions related to a ticket
    and summarizes them for use in AC generation.
    """

    def __init__(self, client: AsyncWebClient):
        """
        Initialize Slack context service.

        Args:
            client: Async Slack Web API client
        """
        self._client = client
        self._settings = get_settings()

    async def get_channel_context(
        self,
        channel_id: str,
        ticket_key: str,
        ticket_title: str = "",
        max_messages: int = 100,
        lookback_hours: int = 168,  # 7 days
    ) -> SlackContextResult:
        """
        Get context from a channel by scanning for ticket-related messages.

        Args:
            channel_id: Slack channel ID
            ticket_key: Jira ticket key to search for (e.g., "PROJ-123")
            ticket_title: Optional ticket title for additional context
            max_messages: Maximum messages to retrieve from channel
            lookback_hours: How far back to search (in hours)

        Returns:
            SlackContextResult: Gathered context with summary
        """
        try:
            # Calculate oldest timestamp
            oldest = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            oldest_ts = str(oldest.timestamp())

            logger.info(
                "slack_context_gathering",
                channel_id=channel_id,
                ticket_key=ticket_key,
                lookback_hours=lookback_hours,
            )

            # Fetch channel history
            response = await self._client.conversations_history(
                channel=channel_id,
                limit=max_messages,
                oldest=oldest_ts,
            )

            if not response.get("ok"):
                error = response.get("error", "Unknown error")
                if "missing_scope" in error or "not_in_channel" in error:
                    raise SlackScopeError(f"Cannot access channel: {error}")
                raise SlackAPIError(f"Failed to get channel history: {error}")

            messages = response.get("messages", [])

            # Filter messages mentioning the ticket
            relevant_messages = self._filter_relevant_messages(messages, ticket_key)

            if not relevant_messages:
                logger.info(
                    "slack_context_no_matches",
                    channel_id=channel_id,
                    ticket_key=ticket_key,
                    total_messages=len(messages),
                )
                return SlackContextResult(
                    success=True,
                    source="channel",
                    total_messages=0,
                )

            # Get thread replies for messages that have threads
            threads = await self._fetch_threads(channel_id, relevant_messages)

            # Convert to schema models
            slack_messages = [
                self._to_slack_message(msg, channel_id) for msg in relevant_messages
            ]

            # Calculate total messages (parent + replies)
            total_messages = len(slack_messages)
            for thread in threads:
                total_messages += len(thread.replies)

            # Generate summary using LLM
            summary = await self._summarize_context(
                slack_messages, threads, ticket_key, ticket_title
            )

            logger.info(
                "slack_context_gathered",
                channel_id=channel_id,
                ticket_key=ticket_key,
                matching_messages=len(slack_messages),
                threads=len(threads),
                total_messages=total_messages,
            )

            return SlackContextResult(
                success=True,
                messages=slack_messages,
                threads=threads,
                total_messages=total_messages,
                source="channel",
                summary=summary,
            )

        except SlackScopeError:
            raise
        except SlackApiError as e:
            error_msg = str(e.response.get("error", str(e)))
            if "missing_scope" in error_msg or "channel_not_found" in error_msg:
                raise SlackScopeError(f"Cannot access channel: {error_msg}") from e
            logger.error(
                "slack_api_error",
                channel_id=channel_id,
                error=error_msg,
            )
            raise SlackAPIError(f"Slack API error: {error_msg}") from e
        except Exception as e:
            logger.error(
                "slack_context_error",
                channel_id=channel_id,
                ticket_key=ticket_key,
                error=str(e),
                exc_info=True,
            )
            raise SlackAPIError(f"Failed to gather Slack context: {str(e)}") from e

    def _filter_relevant_messages(
        self, messages: list[dict], ticket_key: str
    ) -> list[dict]:
        """
        Filter messages that mention the ticket key.

        Args:
            messages: List of Slack message dicts
            ticket_key: Jira ticket key to search for

        Returns:
            List of relevant messages
        """
        # Create pattern to match ticket key (case-insensitive)
        pattern = re.compile(re.escape(ticket_key), re.IGNORECASE)

        relevant = []
        for msg in messages:
            text = msg.get("text", "")
            # Check if message mentions ticket key
            if pattern.search(text):
                relevant.append(msg)

        return relevant

    async def _fetch_threads(
        self, channel_id: str, messages: list[dict]
    ) -> list[SlackThread]:
        """
        Fetch thread replies for messages that have threads.

        Args:
            channel_id: Slack channel ID
            messages: List of parent messages

        Returns:
            List of SlackThread objects
        """
        threads = []

        for msg in messages:
            # Check if message has replies
            reply_count = msg.get("reply_count", 0)
            if reply_count == 0:
                continue

            thread_ts = msg.get("ts")
            if not thread_ts:
                continue

            try:
                response = await self._client.conversations_replies(
                    channel=channel_id,
                    ts=thread_ts,
                    limit=50,  # Limit replies per thread
                )

                if response.get("ok"):
                    reply_messages = response.get("messages", [])
                    # First message is the parent, rest are replies
                    parent = reply_messages[0] if reply_messages else msg
                    replies = reply_messages[1:] if len(reply_messages) > 1 else []

                    threads.append(
                        SlackThread(
                            channel_id=channel_id,
                            thread_ts=thread_ts,
                            parent_message=self._to_slack_message(parent, channel_id),
                            replies=[
                                self._to_slack_message(r, channel_id, is_reply=True)
                                for r in replies
                            ],
                            reply_count=len(replies),
                        )
                    )

            except SlackApiError as e:
                logger.warning(
                    "slack_thread_fetch_failed",
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    error=str(e),
                )
                continue

        return threads

    def _to_slack_message(
        self, msg: dict, channel_id: str, is_reply: bool = False
    ) -> SlackMessage:
        """
        Convert Slack API message dict to SlackMessage model.

        Args:
            msg: Slack message dict
            channel_id: Channel ID
            is_reply: Whether this is a thread reply

        Returns:
            SlackMessage model
        """
        return SlackMessage(
            text=msg.get("text", ""),
            user_id=msg.get("user", "unknown"),
            timestamp=msg.get("ts", ""),
            channel_id=channel_id,
            thread_ts=msg.get("thread_ts"),
            is_thread_reply=is_reply,
        )

    async def _summarize_context(
        self,
        messages: list[SlackMessage],
        threads: list[SlackThread],
        ticket_key: str,
        ticket_title: str,
    ) -> str | None:
        """
        Use LLM to summarize gathered Slack context.

        Args:
            messages: List of relevant messages
            threads: List of threads with replies
            ticket_key: Jira ticket key
            ticket_title: Ticket title

        Returns:
            Summary string or None if no relevant context
        """
        if not messages and not threads:
            return None

        # Format messages for the prompt
        formatted_messages = self._format_messages_for_summary(messages, threads)

        if not formatted_messages.strip():
            return None

        try:
            # Get fast model for summarization
            provider = get_llm_provider()
            model = provider.get_orchestrator_model()

            # Build prompt
            prompt = format_prompt(
                "slack_summarizer.txt",
                ticket_key=ticket_key,
                ticket_title=ticket_title or "No title",
                messages=formatted_messages,
            )

            # Invoke model
            response = await model.ainvoke(prompt)
            summary = response.content.strip()

            # Check if the model found relevant context
            if "no relevant" in summary.lower():
                return None

            logger.debug(
                "slack_context_summarized",
                ticket_key=ticket_key,
                summary_length=len(summary),
            )

            return summary

        except Exception as e:
            logger.warning(
                "slack_context_summarization_failed",
                ticket_key=ticket_key,
                error=str(e),
            )
            # Return formatted messages as fallback
            return f"Slack discussions found (summary unavailable):\n{formatted_messages[:1000]}"

    def _format_messages_for_summary(
        self, messages: list[SlackMessage], threads: list[SlackThread]
    ) -> str:
        """
        Format messages and threads for LLM summarization.

        Args:
            messages: List of relevant messages
            threads: List of threads

        Returns:
            Formatted string for the prompt
        """
        parts = []

        # Format standalone messages (not in threads)
        thread_timestamps = {t.thread_ts for t in threads}
        standalone = [m for m in messages if m.timestamp not in thread_timestamps]

        for msg in standalone:
            parts.append(f"Message: {msg.text}")

        # Format threads
        for thread in threads:
            thread_text = f"Thread:\n  Parent: {thread.parent_message.text}"
            for reply in thread.replies:
                thread_text += f"\n  Reply: {reply.text}"
            parts.append(thread_text)

        return "\n\n".join(parts)


# Singleton instance
_slack_context_service: SlackContextService | None = None


async def get_slack_context_service(client: AsyncWebClient) -> SlackContextService:
    """
    Get or create the singleton Slack context service instance.

    Args:
        client: Async Slack Web API client

    Returns:
        SlackContextService: Configured service instance
    """
    global _slack_context_service

    if _slack_context_service is None:
        _slack_context_service = SlackContextService(client)
        logger.info("slack_context_service_initialized")

    return _slack_context_service


async def get_channel_context_safe(
    client: AsyncWebClient,
    channel_id: str,
    ticket_key: str,
    ticket_title: str = "",
) -> SlackContextResult:
    """
    Safely gather Slack context with graceful fallback on errors.

    This function catches all exceptions and returns an empty result
    instead of failing, allowing AC generation to proceed without
    Slack context if gathering fails.

    Args:
        client: Async Slack Web API client
        channel_id: Slack channel ID
        ticket_key: Jira ticket key
        ticket_title: Optional ticket title

    Returns:
        SlackContextResult: Gathered context or empty result on error
    """
    try:
        service = await get_slack_context_service(client)
        return await service.get_channel_context(
            channel_id=channel_id,
            ticket_key=ticket_key,
            ticket_title=ticket_title,
        )
    except SlackScopeError as e:
        logger.warning(
            "slack_context_scope_error",
            channel_id=channel_id,
            ticket_key=ticket_key,
            error=str(e),
        )
        return SlackContextResult(
            success=False,
            source="none",
            error=f"Cannot access channel: {str(e)}",
        )
    except SlackAPIError as e:
        logger.warning(
            "slack_context_api_error",
            channel_id=channel_id,
            ticket_key=ticket_key,
            error=str(e),
        )
        return SlackContextResult(
            success=False,
            source="none",
            error=str(e),
        )
    except Exception as e:
        logger.error(
            "slack_context_unexpected_error",
            channel_id=channel_id,
            ticket_key=ticket_key,
            error=str(e),
            exc_info=True,
        )
        return SlackContextResult(
            success=False,
            source="none",
            error="Unexpected error gathering Slack context",
        )
