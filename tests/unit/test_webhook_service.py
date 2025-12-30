"""Unit tests for webhook service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from src.schemas.jira import AcceptanceCriteriaDetectionResult, JiraTicket
from src.schemas.webhook import (
    JiraChangelog,
    JiraChangeItem,
    JiraIssue,
    JiraIssueFields,
    JiraUser,
    JiraWebhookPayload,
    WebhookResponse,
)
from src.services.webhook import WebhookService


class TestJiraWebhookPayload:
    """Test suite for JiraWebhookPayload schema."""

    def test_get_status_change_with_status_change(self):
        """Test extracting status change from changelog."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
            ),
            changelog=JiraChangelog(
                id="10001",
                items=[
                    JiraChangeItem(
                        field="status",
                        fromString="Backlog",
                        toString="To Do",
                    )
                ],
            ),
        )

        from_status, to_status = payload.get_status_change()

        assert from_status == "Backlog"
        assert to_status == "To Do"

    def test_get_status_change_no_changelog(self):
        """Test status change extraction when no changelog."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
            ),
        )

        from_status, to_status = payload.get_status_change()

        assert from_status is None
        assert to_status is None

    def test_get_status_change_no_status_in_changelog(self):
        """Test status change extraction when changelog has other changes."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
            ),
            changelog=JiraChangelog(
                id="10001",
                items=[
                    JiraChangeItem(
                        field="summary",
                        fromString="Old title",
                        toString="New title",
                    )
                ],
            ),
        )

        from_status, to_status = payload.get_status_change()

        assert from_status is None
        assert to_status is None

    def test_get_assignee_email(self):
        """Test extracting assignee email."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
                fields=JiraIssueFields(
                    assignee=JiraUser(
                        accountId="123456",
                        emailAddress="developer@example.com",
                        displayName="Test Developer",
                    )
                ),
            ),
        )

        email = payload.get_assignee_email()

        assert email == "developer@example.com"

    def test_get_assignee_email_no_assignee(self):
        """Test extracting assignee email when no assignee."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
            ),
        )

        email = payload.get_assignee_email()

        assert email is None

    def test_get_ticket_key(self):
        """Test extracting ticket key."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
            ),
        )

        key = payload.get_ticket_key()

        assert key == "PROJ-123"

    def test_get_ticket_type(self):
        """Test extracting ticket type."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
                fields=JiraIssueFields(
                    issuetype={"name": "Story", "id": "10001"}
                ),
            ),
        )

        ticket_type = payload.get_ticket_type()

        assert ticket_type == "Story"

    def test_get_ticket_type_no_issuetype(self):
        """Test extracting ticket type when not set."""
        payload = JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key="PROJ-123",
                self="https://test.atlassian.net/rest/api/3/issue/10001",
            ),
        )

        ticket_type = payload.get_ticket_type()

        assert ticket_type is None


class TestWebhookService:
    """Test suite for WebhookService class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        mock = MagicMock()
        mock.webhook_target_statuses = ["To Do", "ToDo", "TODO"]
        mock.slack_bot_token = SecretStr("xoxb-test-token")
        mock.jira_site_url = "https://test.atlassian.net"
        mock.jira_user_email = "bot@example.com"
        mock.jira_api_token = SecretStr("test-api-token")
        return mock

    @pytest.fixture
    def mock_slack_client(self):
        """Create mock Slack client."""
        client = AsyncMock()
        client.users_lookupByEmail = AsyncMock(
            return_value={"ok": True, "user": {"id": "U12345678"}}
        )
        client.conversations_open = AsyncMock(
            return_value={"ok": True, "channel": {"id": "D12345678"}}
        )
        client.chat_postMessage = AsyncMock(return_value={"ok": True})
        return client

    @pytest.fixture
    def webhook_service(self, mock_settings, mock_slack_client):
        """Create a WebhookService instance for testing."""
        with patch("src.services.webhook.get_settings", return_value=mock_settings):
            return WebhookService(mock_slack_client)

    def _create_payload(
        self,
        ticket_key: str = "PROJ-123",
        from_status: str | None = "Backlog",
        to_status: str | None = "To Do",
        ticket_type: str = "Story",
        assignee_email: str | None = "developer@example.com",
    ) -> JiraWebhookPayload:
        """Helper to create test webhook payloads."""
        changelog = None
        if from_status or to_status:
            changelog = JiraChangelog(
                id="10001",
                items=[
                    JiraChangeItem(
                        field="status",
                        fromString=from_status,
                        toString=to_status,
                    )
                ],
            )

        assignee = None
        if assignee_email:
            assignee = JiraUser(
                accountId="123456",
                emailAddress=assignee_email,
                displayName="Test Developer",
            )

        return JiraWebhookPayload(
            webhookEvent="jira:issue_updated",
            issue=JiraIssue(
                id="10001",
                key=ticket_key,
                self=f"https://test.atlassian.net/rest/api/3/issue/10001",
                fields=JiraIssueFields(
                    summary="Test ticket",
                    issuetype={"name": ticket_type, "id": "10001"},
                    status={"name": to_status or "Backlog"},
                    assignee=assignee,
                ),
            ),
            changelog=changelog,
        )

    @pytest.mark.asyncio
    async def test_process_issue_updated_no_status_change(self, webhook_service):
        """Test processing webhook with no status change."""
        payload = self._create_payload(from_status=None, to_status=None)
        payload.changelog = None

        result = await webhook_service.process_issue_updated(payload)

        assert result.status == "skipped"
        assert "No status change detected" in result.message

    @pytest.mark.asyncio
    async def test_process_issue_updated_non_target_status(self, webhook_service):
        """Test processing webhook when status is not a target."""
        payload = self._create_payload(to_status="In Progress")

        result = await webhook_service.process_issue_updated(payload)

        assert result.status == "skipped"
        assert "not a target status" in result.message

    @pytest.mark.asyncio
    async def test_process_issue_updated_unsupported_ticket_type(self, webhook_service):
        """Test processing webhook for unsupported ticket type."""
        payload = self._create_payload(ticket_type="Epic")

        result = await webhook_service.process_issue_updated(payload)

        assert result.status == "skipped"
        assert "not supported" in result.message

    @pytest.mark.asyncio
    async def test_process_issue_updated_ticket_has_ac(self, webhook_service):
        """Test processing webhook when ticket already has AC."""
        payload = self._create_payload()

        mock_jira_service = AsyncMock()
        mock_jira_service.get_ticket = AsyncMock(
            return_value=JiraTicket(
                key="PROJ-123",
                title="Test ticket",
                ticket_type="Story",
                description="## Acceptance Criteria\n- Test criterion",
                status="To Do",
                url="https://test.atlassian.net/browse/PROJ-123",
            )
        )
        mock_jira_service.detect_acceptance_criteria = MagicMock(
            return_value=AcceptanceCriteriaDetectionResult(
                has_ac=True,
                ac_content="- Test criterion",
                ac_start_index=0,
                ac_end_index=50,
            )
        )

        with patch(
            "src.services.webhook.get_jira_service",
            return_value=mock_jira_service,
        ):
            result = await webhook_service.process_issue_updated(payload)

        assert result.status == "skipped"
        assert "already has acceptance criteria" in result.message

    @pytest.mark.asyncio
    async def test_process_issue_updated_no_assignee(self, webhook_service):
        """Test processing webhook when ticket has no assignee."""
        payload = self._create_payload(assignee_email=None)

        mock_jira_service = AsyncMock()
        mock_jira_service.get_ticket = AsyncMock(
            return_value=JiraTicket(
                key="PROJ-123",
                title="Test ticket",
                ticket_type="Story",
                description="No AC here",
                status="To Do",
                url="https://test.atlassian.net/browse/PROJ-123",
            )
        )
        mock_jira_service.detect_acceptance_criteria = MagicMock(
            return_value=AcceptanceCriteriaDetectionResult(has_ac=False)
        )

        with patch(
            "src.services.webhook.get_jira_service",
            return_value=mock_jira_service,
        ):
            result = await webhook_service.process_issue_updated(payload)

        assert result.status == "skipped"
        assert "No assignee" in result.message

    @pytest.mark.asyncio
    async def test_process_issue_updated_slack_user_not_found(
        self, webhook_service, mock_slack_client
    ):
        """Test processing webhook when Slack user not found."""
        payload = self._create_payload()

        mock_jira_service = AsyncMock()
        mock_jira_service.get_ticket = AsyncMock(
            return_value=JiraTicket(
                key="PROJ-123",
                title="Test ticket",
                ticket_type="Story",
                description="No AC here",
                status="To Do",
                url="https://test.atlassian.net/browse/PROJ-123",
            )
        )
        mock_jira_service.detect_acceptance_criteria = MagicMock(
            return_value=AcceptanceCriteriaDetectionResult(has_ac=False)
        )

        # Slack user lookup fails
        mock_slack_client.users_lookupByEmail = AsyncMock(
            return_value={"ok": False, "error": "users_not_found"}
        )

        with patch(
            "src.services.webhook.get_jira_service",
            return_value=mock_jira_service,
        ):
            result = await webhook_service.process_issue_updated(payload)

        assert result.status == "skipped"
        assert "Slack user not found" in result.message

    @pytest.mark.asyncio
    async def test_process_issue_updated_success(
        self, webhook_service, mock_slack_client
    ):
        """Test successful webhook processing sends DM."""
        payload = self._create_payload()

        mock_jira_service = AsyncMock()
        mock_jira_service.get_ticket = AsyncMock(
            return_value=JiraTicket(
                key="PROJ-123",
                title="Test ticket",
                ticket_type="Story",
                description="No AC here",
                status="To Do",
                url="https://test.atlassian.net/browse/PROJ-123",
            )
        )
        mock_jira_service.detect_acceptance_criteria = MagicMock(
            return_value=AcceptanceCriteriaDetectionResult(has_ac=False)
        )

        with patch(
            "src.services.webhook.get_jira_service",
            return_value=mock_jira_service,
        ):
            result = await webhook_service.process_issue_updated(payload)

        assert result.status == "success"
        assert result.action_taken == "dm_sent"
        assert result.ticket_key == "PROJ-123"

        # Verify Slack API calls
        mock_slack_client.users_lookupByEmail.assert_called_once_with(
            email="developer@example.com"
        )
        mock_slack_client.conversations_open.assert_called_once()
        mock_slack_client.chat_postMessage.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_issue_updated_jira_fetch_fails(self, webhook_service):
        """Test processing webhook when Jira fetch fails."""
        payload = self._create_payload()

        with patch(
            "src.services.webhook.get_jira_service",
            side_effect=Exception("Jira connection failed"),
        ):
            result = await webhook_service.process_issue_updated(payload)

        assert result.status == "error"
        assert "Failed to fetch ticket" in result.message

    @pytest.mark.asyncio
    async def test_process_issue_updated_case_insensitive_status(self, webhook_service):
        """Test status matching is case-insensitive."""
        # "to do" should match "To Do" in target statuses
        payload = self._create_payload(to_status="to do")

        mock_jira_service = AsyncMock()
        mock_jira_service.get_ticket = AsyncMock(
            return_value=JiraTicket(
                key="PROJ-123",
                title="Test ticket",
                ticket_type="Story",
                description="No AC",
                status="to do",
                url="https://test.atlassian.net/browse/PROJ-123",
            )
        )
        mock_jira_service.detect_acceptance_criteria = MagicMock(
            return_value=AcceptanceCriteriaDetectionResult(has_ac=False)
        )

        with patch(
            "src.services.webhook.get_jira_service",
            return_value=mock_jira_service,
        ):
            result = await webhook_service.process_issue_updated(payload)

        assert result.status == "success"


class TestWebhookServiceUserCache:
    """Test suite for WebhookService email cache."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        mock = MagicMock()
        mock.webhook_target_statuses = ["To Do"]
        return mock

    @pytest.fixture
    def mock_slack_client(self):
        """Create mock Slack client."""
        client = AsyncMock()
        client.users_lookupByEmail = AsyncMock(
            return_value={"ok": True, "user": {"id": "U12345678"}}
        )
        return client

    @pytest.fixture
    def webhook_service(self, mock_settings, mock_slack_client):
        """Create a WebhookService instance for testing."""
        with patch("src.services.webhook.get_settings", return_value=mock_settings):
            return WebhookService(mock_slack_client)

    @pytest.mark.asyncio
    async def test_user_lookup_caches_result(self, webhook_service, mock_slack_client):
        """Test that user lookup results are cached."""
        email = "test@example.com"

        # First lookup
        result1 = await webhook_service._find_slack_user_by_email(email)
        assert result1 == "U12345678"

        # Second lookup - should use cache
        result2 = await webhook_service._find_slack_user_by_email(email)
        assert result2 == "U12345678"

        # Slack API should only be called once
        assert mock_slack_client.users_lookupByEmail.call_count == 1

    @pytest.mark.asyncio
    async def test_user_lookup_caches_not_found(self, webhook_service, mock_slack_client):
        """Test that not-found results are also cached."""
        email = "notfound@example.com"
        mock_slack_client.users_lookupByEmail = AsyncMock(
            return_value={"ok": False, "error": "users_not_found"}
        )

        # First lookup
        result1 = await webhook_service._find_slack_user_by_email(email)
        assert result1 is None

        # Second lookup - should use cache
        result2 = await webhook_service._find_slack_user_by_email(email)
        assert result2 is None

        # Slack API should only be called once
        assert mock_slack_client.users_lookupByEmail.call_count == 1

    @pytest.mark.asyncio
    async def test_user_lookup_handles_exception(self, webhook_service, mock_slack_client):
        """Test that exceptions are handled gracefully."""
        email = "error@example.com"
        mock_slack_client.users_lookupByEmail = AsyncMock(
            side_effect=Exception("Slack API error")
        )

        result = await webhook_service._find_slack_user_by_email(email)

        assert result is None
        # Should cache the failure
        assert email in webhook_service._user_email_cache
        assert webhook_service._user_email_cache[email] is None


class TestWebhookResponse:
    """Test suite for WebhookResponse schema."""

    def test_webhook_response_success(self):
        """Test creating success response."""
        response = WebhookResponse(
            status="success",
            message="AC offer sent",
            ticket_key="PROJ-123",
            action_taken="dm_sent",
        )

        assert response.status == "success"
        assert response.ticket_key == "PROJ-123"
        assert response.action_taken == "dm_sent"

    def test_webhook_response_skipped(self):
        """Test creating skipped response."""
        response = WebhookResponse(
            status="skipped",
            message="Ticket already has AC",
            ticket_key="PROJ-456",
        )

        assert response.status == "skipped"
        assert response.action_taken is None

    def test_webhook_response_error(self):
        """Test creating error response."""
        response = WebhookResponse(
            status="error",
            message="Failed to fetch ticket",
            ticket_key="PROJ-789",
        )

        assert response.status == "error"
