"""Slack context data schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class SlackMessage(BaseModel):
    """Single Slack message."""

    text: str = Field(..., description="Message text content")
    user_id: str = Field(..., description="Slack user ID of message author")
    timestamp: str = Field(..., description="Message timestamp (ts)")
    channel_id: str = Field(..., description="Channel ID where message was posted")
    thread_ts: str | None = Field(
        default=None, description="Thread parent timestamp if message is in a thread"
    )
    is_thread_reply: bool = Field(
        default=False, description="Whether this is a reply in a thread"
    )


class SlackThread(BaseModel):
    """A Slack thread with parent message and replies."""

    channel_id: str = Field(..., description="Channel ID")
    thread_ts: str = Field(..., description="Thread parent timestamp")
    parent_message: SlackMessage = Field(..., description="Thread parent message")
    replies: list[SlackMessage] = Field(
        default_factory=list, description="Thread replies"
    )
    reply_count: int = Field(default=0, description="Number of replies in thread")


class SlackContextResult(BaseModel):
    """Result of Slack context gathering."""

    success: bool = Field(..., description="Whether context gathering succeeded")
    messages: list[SlackMessage] = Field(
        default_factory=list, description="Relevant messages found"
    )
    threads: list[SlackThread] = Field(
        default_factory=list, description="Relevant threads found"
    )
    total_messages: int = Field(default=0, description="Total number of messages found")
    source: Literal["channel", "none"] = Field(
        default="none", description="Source of context"
    )
    summary: str | None = Field(
        default=None, description="LLM-generated summary of discussions"
    )
    error: str | None = Field(default=None, description="Error message if failed")
