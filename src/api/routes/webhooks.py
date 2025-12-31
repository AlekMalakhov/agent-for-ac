"""Webhook endpoints for Jira integration."""

import hashlib
import hmac

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from src.config.settings import Settings, get_settings
from src.schemas.webhook import JiraWebhookPayload, WebhookResponse
from src.services.webhook import get_webhook_service

logger = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_webhook_signature(
    request_body: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    """
    Verify Jira webhook signature.

    Args:
        request_body: Raw request body
        signature: Signature from X-Hub-Signature header
        secret: Webhook secret

    Returns:
        True if signature is valid
    """
    if not signature:
        return False

    expected = hmac.new(
        secret.encode(),
        request_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/jira", response_model=WebhookResponse)
async def handle_jira_webhook(
    request: Request,
    x_hub_signature: str | None = Header(default=None, alias="X-Hub-Signature"),
    settings: Settings = Depends(get_settings),
) -> WebhookResponse:
    """
    Handle Jira webhook events.

    This endpoint receives webhook events from Jira when issues are updated.
    When a ticket moves to a target status (e.g., "To Do"), it checks for
    acceptance criteria and sends a proactive DM to the assignee if missing.

    Webhook Configuration in Jira:
    1. Go to Jira Settings > System > Webhooks
    2. Create a webhook with URL: https://your-domain/webhooks/jira
    3. Select events: Issue > Updated
    4. Optionally add a secret for signature verification

    Args:
        request: FastAPI request object
        x_hub_signature: Optional webhook signature for verification
        settings: Application settings

    Returns:
        WebhookResponse with processing result
    """
    # Check if webhooks are enabled
    if not settings.webhook_enabled:
        logger.info("webhook_disabled")
        return WebhookResponse(
            status="disabled",
            message="Webhooks are disabled",
        )

    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if secret is configured
    if settings.webhook_secret:
        secret = settings.webhook_secret.get_secret_value()
        if not verify_webhook_signature(body, x_hub_signature, secret):
            logger.warning("webhook_signature_invalid")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse payload
    try:
        payload = JiraWebhookPayload.model_validate_json(body)
    except Exception as e:
        logger.error("webhook_parse_failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")

    # Log webhook event
    logger.info(
        "webhook_received",
        event=payload.webhookEvent,
        ticket_key=payload.get_ticket_key(),
    )

    # Only process issue_updated events
    if payload.webhookEvent != "jira:issue_updated":
        return WebhookResponse(
            status="skipped",
            message=f"Event type '{payload.webhookEvent}' not handled",
            ticket_key=payload.get_ticket_key(),
        )

    # Get Slack client - lazy initialization for serverless
    slack_client = getattr(request.app.state, "slack_client", None)
    if not slack_client:
        # Lazy initialization for serverless environments (Vercel)
        from slack_sdk.web.async_client import AsyncWebClient
        slack_client = AsyncWebClient(
            token=settings.slack_bot_token.get_secret_value()
        )
        request.app.state.slack_client = slack_client
        logger.info("slack_client_lazy_initialized")

    # Process the webhook
    webhook_service = await get_webhook_service(slack_client)
    return await webhook_service.process_issue_updated(payload)
