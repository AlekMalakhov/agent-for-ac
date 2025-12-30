"""Webhook processing service for proactive AC generation."""

import structlog
from slack_sdk.web.async_client import AsyncWebClient

from src.config.settings import get_settings
from src.schemas.jira import AcceptanceCriteriaDetectionResult
from src.schemas.webhook import JiraWebhookPayload, WebhookResponse
from src.services.jira import get_jira_service

logger = structlog.get_logger()

# Supported ticket types for AC generation
SUPPORTED_TICKET_TYPES = {"Story", "Task"}


class WebhookService:
    """
    Service for processing Jira webhooks and triggering proactive AC generation.

    This service:
    1. Receives Jira webhook events
    2. Detects when tickets move to target statuses (e.g., "To Do")
    3. Checks if ticket has AC
    4. Sends proactive DM to assignee offering AC generation
    """

    def __init__(self, slack_client: AsyncWebClient):
        """
        Initialize webhook service.

        Args:
            slack_client: Slack Web API client for sending DMs
        """
        self.slack_client = slack_client
        self.settings = get_settings()
        self._user_email_cache: dict[str, str | None] = {}

    async def process_issue_updated(
        self, payload: JiraWebhookPayload
    ) -> WebhookResponse:
        """
        Process Jira issue_updated webhook event.

        Checks if ticket moved to target status and offers AC generation if needed.

        Args:
            payload: Parsed Jira webhook payload

        Returns:
            WebhookResponse with processing result
        """
        ticket_key = payload.get_ticket_key()

        # Check if this is a status change
        from_status, to_status = payload.get_status_change()

        if not to_status:
            logger.debug(
                "webhook_no_status_change",
                ticket_key=ticket_key,
            )
            return WebhookResponse(
                status="skipped",
                message="No status change detected",
                ticket_key=ticket_key,
            )

        logger.info(
            "webhook_status_change_detected",
            ticket_key=ticket_key,
            from_status=from_status,
            to_status=to_status,
        )

        # Check if moved to target status
        target_statuses = self.settings.webhook_target_statuses
        if to_status.lower() not in [s.lower() for s in target_statuses]:
            logger.debug(
                "webhook_status_not_target",
                ticket_key=ticket_key,
                to_status=to_status,
                target_statuses=target_statuses,
            )
            return WebhookResponse(
                status="skipped",
                message=f"Status '{to_status}' is not a target status",
                ticket_key=ticket_key,
            )

        # Check ticket type
        ticket_type = payload.get_ticket_type()
        if ticket_type not in SUPPORTED_TICKET_TYPES:
            logger.debug(
                "webhook_unsupported_ticket_type",
                ticket_key=ticket_key,
                ticket_type=ticket_type,
            )
            return WebhookResponse(
                status="skipped",
                message=f"Ticket type '{ticket_type}' not supported for AC generation",
                ticket_key=ticket_key,
            )

        # Fetch full ticket details and check for AC
        try:
            jira_service = await get_jira_service()
            ticket = await jira_service.get_ticket(ticket_key)
            detection_result = jira_service.detect_acceptance_criteria(ticket.description)
        except Exception as e:
            logger.error(
                "webhook_jira_fetch_failed",
                ticket_key=ticket_key,
                error=str(e),
            )
            return WebhookResponse(
                status="error",
                message=f"Failed to fetch ticket: {str(e)}",
                ticket_key=ticket_key,
            )

        if detection_result.has_ac:
            logger.info(
                "webhook_ticket_has_ac",
                ticket_key=ticket_key,
            )
            return WebhookResponse(
                status="skipped",
                message="Ticket already has acceptance criteria",
                ticket_key=ticket_key,
            )

        # Get assignee email and find Slack user
        assignee_email = payload.get_assignee_email()
        if not assignee_email:
            logger.warning(
                "webhook_no_assignee",
                ticket_key=ticket_key,
            )
            return WebhookResponse(
                status="skipped",
                message="No assignee on ticket",
                ticket_key=ticket_key,
            )

        # Look up Slack user by email
        slack_user_id = await self._find_slack_user_by_email(assignee_email)
        if not slack_user_id:
            logger.warning(
                "webhook_slack_user_not_found",
                ticket_key=ticket_key,
                email=assignee_email,
            )
            return WebhookResponse(
                status="skipped",
                message=f"Slack user not found for email: {assignee_email}",
                ticket_key=ticket_key,
            )

        # Send proactive DM offering AC generation
        await self._send_ac_offer(
            slack_user_id=slack_user_id,
            ticket_key=ticket_key,
            ticket_title=ticket.title,
            ticket_url=ticket.url,
            ticket_type=ticket.ticket_type,
        )

        logger.info(
            "webhook_ac_offer_sent",
            ticket_key=ticket_key,
            slack_user_id=slack_user_id,
        )

        return WebhookResponse(
            status="success",
            message="AC generation offer sent to assignee",
            ticket_key=ticket_key,
            action_taken="dm_sent",
        )

    async def _find_slack_user_by_email(self, email: str) -> str | None:
        """
        Find Slack user ID by email address.

        Args:
            email: User's email address

        Returns:
            Slack user ID or None if not found
        """
        # Check cache first
        if email in self._user_email_cache:
            return self._user_email_cache[email]

        try:
            response = await self.slack_client.users_lookupByEmail(email=email)

            if response["ok"]:
                user_id = response["user"]["id"]
                self._user_email_cache[email] = user_id
                return user_id
            else:
                self._user_email_cache[email] = None
                return None

        except Exception as e:
            logger.warning(
                "slack_user_lookup_failed",
                email=email,
                error=str(e),
            )
            self._user_email_cache[email] = None
            return None

    async def _send_ac_offer(
        self,
        slack_user_id: str,
        ticket_key: str,
        ticket_title: str,
        ticket_url: str,
        ticket_type: str,
    ) -> None:
        """
        Send a proactive DM offering AC generation.

        Args:
            slack_user_id: Slack user ID to message
            ticket_key: Jira ticket key
            ticket_title: Ticket title
            ticket_url: URL to the ticket
            ticket_type: Ticket type (Story/Task)
        """
        message = (
            f"*{ticket_key}* has been moved to *To Do* but doesn't have acceptance criteria yet.\n\n"
            f"*{ticket_title}*\n"
            f"Type: {ticket_type}\n"
            f"<{ticket_url}|View in Jira>\n\n"
            f"Would you like me to generate acceptance criteria for this ticket?\n\n"
            f"Reply with the ticket link to start: `{ticket_url}`\n"
            f"Or mention me in a channel: `@Agent for AC {ticket_key}`"
        )

        try:
            # Open DM channel with user
            dm_response = await self.slack_client.conversations_open(users=[slack_user_id])

            if dm_response["ok"]:
                channel_id = dm_response["channel"]["id"]

                # Send message
                await self.slack_client.chat_postMessage(
                    channel=channel_id,
                    text=message,
                    unfurl_links=False,
                )

                logger.info(
                    "ac_offer_dm_sent",
                    slack_user_id=slack_user_id,
                    ticket_key=ticket_key,
                )
            else:
                logger.error(
                    "failed_to_open_dm",
                    slack_user_id=slack_user_id,
                    error=dm_response.get("error"),
                )

        except Exception as e:
            logger.error(
                "ac_offer_dm_failed",
                slack_user_id=slack_user_id,
                ticket_key=ticket_key,
                error=str(e),
            )
            raise


# Singleton instance
_webhook_service: WebhookService | None = None


async def get_webhook_service(slack_client: AsyncWebClient) -> WebhookService:
    """
    Get or create the webhook service instance.

    Args:
        slack_client: Slack Web API client

    Returns:
        WebhookService instance
    """
    global _webhook_service

    if _webhook_service is None:
        _webhook_service = WebhookService(slack_client)

    return _webhook_service
