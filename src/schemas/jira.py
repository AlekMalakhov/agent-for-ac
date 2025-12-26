"""Jira-related data schemas."""

from pydantic import BaseModel, Field


class JiraTicket(BaseModel):
    """Jira ticket data model."""

    key: str = Field(..., description="Ticket key (e.g., PROJ-123)")
    title: str = Field(..., description="Ticket summary/title")
    ticket_type: str = Field(..., description="Ticket type (Story, Task, Epic, Bug, etc.)")
    description: str = Field(default="", description="Ticket description content")
    status: str = Field(..., description="Ticket status (To Do, In Progress, Done, etc.)")
    url: str = Field(..., description="Full URL to the Jira ticket")


class AcceptanceCriteriaDetectionResult(BaseModel):
    """Result of AC detection in a Jira ticket."""

    has_ac: bool = Field(..., description="Whether AC block was found")
    ac_content: str | None = Field(
        default=None, description="Existing AC content if found"
    )
    ac_start_index: int | None = Field(
        default=None,
        description="Start position of AC block in description (for replacement)",
    )
    ac_end_index: int | None = Field(
        default=None, description="End position of AC block in description"
    )


class JiraUpdateResult(BaseModel):
    """Result of updating a Jira ticket."""

    success: bool = Field(..., description="Whether the update succeeded")
    ticket_key: str = Field(..., description="Ticket key that was updated")
    ticket_url: str = Field(..., description="URL to the updated ticket")
    message: str = Field(..., description="Human-readable result message")
    error: str | None = Field(default=None, description="Error message if failed")
