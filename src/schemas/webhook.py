"""Jira webhook payload schemas."""

from typing import Any

from pydantic import BaseModel, Field


class JiraUser(BaseModel):
    """Jira user information from webhook."""

    accountId: str = Field(..., description="Jira account ID")
    emailAddress: str | None = Field(default=None, description="User email address")
    displayName: str | None = Field(default=None, description="User display name")


class JiraIssueFields(BaseModel):
    """Jira issue fields from webhook."""

    summary: str | None = Field(default=None, description="Issue summary/title")
    description: Any | None = Field(default=None, description="Issue description (ADF or string)")
    status: dict | None = Field(default=None, description="Issue status object")
    issuetype: dict | None = Field(default=None, description="Issue type object")
    assignee: JiraUser | None = Field(default=None, description="Issue assignee")
    project: dict | None = Field(default=None, description="Project information")


class JiraIssue(BaseModel):
    """Jira issue from webhook."""

    id: str = Field(..., description="Issue ID")
    key: str = Field(..., description="Issue key (e.g., PROJ-123)")
    self: str = Field(..., description="Issue API URL")
    fields: JiraIssueFields = Field(default_factory=JiraIssueFields)


class JiraChangeItem(BaseModel):
    """Single change item in changelog."""

    field: str = Field(..., description="Field that changed")
    fieldtype: str | None = Field(default=None, description="Field type")
    fieldId: str | None = Field(default=None, description="Field ID")
    fromString: str | None = Field(default=None, description="Previous value as string")
    toString: str | None = Field(default=None, description="New value as string")


class JiraChangelog(BaseModel):
    """Changelog from webhook event."""

    id: str | None = Field(default=None, description="Changelog ID")
    items: list[JiraChangeItem] = Field(default_factory=list, description="List of changes")


class JiraWebhookPayload(BaseModel):
    """
    Jira webhook payload for issue events.

    This schema handles issue_updated events with status changes.
    """

    timestamp: int | None = Field(default=None, description="Event timestamp")
    webhookEvent: str = Field(..., description="Webhook event type (e.g., jira:issue_updated)")
    issue_event_type_name: str | None = Field(default=None, description="Specific issue event type")
    user: JiraUser | None = Field(default=None, description="User who triggered the event")
    issue: JiraIssue = Field(..., description="Issue data")
    changelog: JiraChangelog | None = Field(default=None, description="Changes made")

    def get_status_change(self) -> tuple[str | None, str | None]:
        """
        Extract status change from changelog.

        Returns:
            Tuple of (from_status, to_status) or (None, None) if no status change
        """
        if not self.changelog:
            return None, None

        for item in self.changelog.items:
            if item.field.lower() == "status":
                return item.fromString, item.toString

        return None, None

    def get_assignee_email(self) -> str | None:
        """Get assignee email address."""
        if self.issue.fields.assignee:
            return self.issue.fields.assignee.emailAddress
        return None

    def get_ticket_key(self) -> str:
        """Get the ticket key."""
        return self.issue.key

    def get_current_status(self) -> str | None:
        """Get current issue status."""
        if self.issue.fields.status:
            return self.issue.fields.status.get("name")
        return None

    def get_ticket_type(self) -> str | None:
        """Get issue type name."""
        if self.issue.fields.issuetype:
            return self.issue.fields.issuetype.get("name")
        return None


class WebhookResponse(BaseModel):
    """Response for webhook endpoint."""

    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Human-readable message")
    ticket_key: str | None = Field(default=None, description="Processed ticket key")
    action_taken: str | None = Field(default=None, description="Action that was taken")
