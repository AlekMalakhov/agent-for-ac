"""Jira integration service using REST API with API Token authentication."""

import base64
import re

import httpx
import structlog

from src.config.settings import get_settings
from src.core.exceptions import (
    JiraConnectionError,
    JiraInvalidTicketLinkError,
    JiraPermissionError,
    JiraTicketNotFoundError,
    JiraUnsupportedTicketTypeError,
)
from src.schemas.jira import (
    AcceptanceCriteriaDetectionResult,
    JiraTicket,
    JiraUpdateResult,
)

logger = structlog.get_logger()

# Supported ticket types for AC generation
SUPPORTED_TICKET_TYPES = {"Story", "Task"}

# Regex patterns for ticket link parsing
TICKET_URL_PATTERN = re.compile(
    r"https://([a-zA-Z0-9-]+)\.atlassian\.net/browse/([A-Z]+-\d+)"
)
TICKET_KEY_PATTERN = re.compile(r"^([A-Z]+-\d+)$")

# Regex pattern for detecting AC block in description
AC_HEADING_PATTERN = re.compile(
    r"(?:^|\n)(#+\s*)?(?:Acceptance Criteria|AC)(?:\s*:)?\s*\n",
    re.IGNORECASE | re.MULTILINE,
)


class JiraService:
    """
    Jira integration service using REST API with API Token authentication.

    This service handles:
    - Authenticating with Jira Cloud via API Token (Basic Auth)
    - Reading Jira ticket content
    - Detecting existing acceptance criteria
    - Writing/updating acceptance criteria in tickets
    """

    def __init__(self):
        """Initialize Jira service with HTTP client configuration."""
        self.settings = get_settings()
        self._client: httpx.AsyncClient | None = None
        self._base_url = self.settings.jira_site_url.rstrip("/")
        logger.info("jira_service_initialized", base_url=self._base_url)

    def _get_auth_header(self) -> str:
        """
        Generate Basic Auth header for Jira API.

        Returns:
            str: Base64 encoded auth string
        """
        auth_string = f"{self.settings.jira_user_email}:{self.settings.jira_api_token.get_secret_value()}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {auth_bytes}"

    async def connect(self) -> None:
        """
        Initialize HTTP client for Jira API calls.

        Raises:
            JiraConnectionError: If connection test fails
        """
        try:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": self._get_auth_header(),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )

            # Test connection by fetching server info
            response = await self._client.get("/rest/api/3/serverInfo")
            response.raise_for_status()

            server_info = response.json()
            logger.info(
                "jira_connected",
                base_url=server_info.get("baseUrl"),
                version=server_info.get("version"),
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise JiraConnectionError(
                    "Invalid Jira credentials. Check your email and API token."
                ) from e
            raise JiraConnectionError(
                f"Failed to connect to Jira: {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.error("jira_connection_failed", error=str(e), exc_info=True)
            raise JiraConnectionError(
                f"Failed to connect to Jira: {str(e)}"
            ) from e

    async def disconnect(self) -> None:
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("jira_disconnected")

    def parse_ticket_identifier(self, ticket_input: str) -> str:
        """
        Parse ticket identifier from URL or key.

        Accepts:
        - Full URL: https://site.atlassian.net/browse/PROJ-123
        - Short key: PROJ-123

        Args:
            ticket_input: Ticket URL or key string

        Returns:
            str: Normalized ticket key (e.g., "PROJ-123")

        Raises:
            JiraInvalidTicketLinkError: If format is invalid
        """
        ticket_input = ticket_input.strip()

        # Try matching full URL
        url_match = TICKET_URL_PATTERN.search(ticket_input)
        if url_match:
            ticket_key = url_match.group(2)
            logger.debug("parsed_ticket_url", ticket_key=ticket_key)
            return ticket_key

        # Try matching short key
        key_match = TICKET_KEY_PATTERN.match(ticket_input)
        if key_match:
            ticket_key = key_match.group(1)
            logger.debug("parsed_ticket_key", ticket_key=ticket_key)
            return ticket_key

        # Invalid format
        raise JiraInvalidTicketLinkError(
            f"Invalid ticket format: '{ticket_input}'. "
            f"Expected format: https://site.atlassian.net/browse/PROJ-123 or PROJ-123"
        )

    async def get_ticket(self, ticket_input: str) -> JiraTicket:
        """
        Retrieve Jira ticket details via REST API.

        Args:
            ticket_input: Ticket URL or key

        Returns:
            JiraTicket: Ticket data model

        Raises:
            JiraInvalidTicketLinkError: If ticket format is invalid
            JiraTicketNotFoundError: If ticket doesn't exist
            JiraPermissionError: If user lacks permission
            JiraUnsupportedTicketTypeError: If ticket type not supported
            JiraConnectionError: If API call fails
        """
        # Parse ticket identifier
        ticket_key = self.parse_ticket_identifier(ticket_input)

        if not self._client:
            raise JiraConnectionError("Jira client not connected. Call connect() first.")

        try:
            # Fetch issue from Jira REST API
            response = await self._client.get(
                f"/rest/api/3/issue/{ticket_key}",
                params={"fields": "summary,description,issuetype,status"},
            )

            if response.status_code == 404:
                raise JiraTicketNotFoundError(
                    f"Ticket {ticket_key} not found"
                )
            elif response.status_code == 403:
                raise JiraPermissionError(
                    f"You don't have permission to view ticket {ticket_key}"
                )
            elif response.status_code == 401:
                raise JiraConnectionError(
                    "Authentication failed. Check your Jira credentials."
                )

            response.raise_for_status()
            issue_data = response.json()

            # Extract description - handle Atlassian Document Format (ADF)
            description = self._extract_description(issue_data.get("fields", {}).get("description"))

            # Build ticket model
            ticket = JiraTicket(
                key=issue_data.get("key", ticket_key),
                title=issue_data.get("fields", {}).get("summary", ""),
                ticket_type=issue_data.get("fields", {})
                .get("issuetype", {})
                .get("name", "Unknown"),
                description=description,
                status=issue_data.get("fields", {})
                .get("status", {})
                .get("name", "Unknown"),
                url=f"{self._base_url}/browse/{ticket_key}",
            )

            # Validate ticket type
            if ticket.ticket_type not in SUPPORTED_TICKET_TYPES:
                raise JiraUnsupportedTicketTypeError(
                    f"AC generation is only supported for Story and Task ticket types. "
                    f"This ticket is a {ticket.ticket_type}."
                )

            logger.info(
                "jira_ticket_retrieved",
                ticket_key=ticket.key,
                ticket_type=ticket.ticket_type,
                status=ticket.status,
            )

            return ticket

        except (JiraTicketNotFoundError, JiraPermissionError, JiraUnsupportedTicketTypeError, JiraConnectionError):
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "jira_api_error",
                ticket_key=ticket_key,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise JiraConnectionError(
                f"Jira API error: {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.error(
                "jira_ticket_retrieval_failed",
                ticket_key=ticket_key,
                error=str(e),
                exc_info=True,
            )
            raise JiraConnectionError(
                f"Failed to retrieve ticket {ticket_key}: {str(e)}"
            ) from e

    def _extract_description(self, description_field) -> str:
        """
        Extract plain text from Jira description field.

        Jira Cloud uses Atlassian Document Format (ADF) for descriptions.
        This method converts ADF to plain text.

        Args:
            description_field: Description field from Jira API (can be None, str, or ADF dict)

        Returns:
            str: Plain text description
        """
        if description_field is None:
            return ""

        if isinstance(description_field, str):
            return description_field

        if isinstance(description_field, dict):
            # ADF format - extract text content
            return self._adf_to_text(description_field)

        return str(description_field)

    def _adf_to_text(self, adf_node: dict) -> str:
        """
        Convert Atlassian Document Format node to plain text.

        Args:
            adf_node: ADF node dict

        Returns:
            str: Plain text content
        """
        if not isinstance(adf_node, dict):
            return ""

        node_type = adf_node.get("type", "")
        text_parts = []

        # Handle text nodes
        if node_type == "text":
            return adf_node.get("text", "")

        # Handle content arrays
        content = adf_node.get("content", [])
        for child in content:
            text_parts.append(self._adf_to_text(child))

        # Add appropriate separators based on node type
        if node_type in ("paragraph", "heading", "bulletList", "orderedList", "listItem"):
            return "\n".join(filter(None, text_parts)) + "\n"

        return "".join(text_parts)

    def detect_acceptance_criteria(
        self, description: str
    ) -> AcceptanceCriteriaDetectionResult:
        """
        Detect existing acceptance criteria in ticket description.

        Looks for "Acceptance Criteria" heading (case-insensitive) in the description.
        Variations supported:
        - "Acceptance Criteria"
        - "AC"
        - "## Acceptance Criteria"
        - "Acceptance Criteria:"

        Args:
            description: Ticket description text

        Returns:
            AcceptanceCriteriaDetectionResult: Detection result with AC content and position
        """
        if not description:
            return AcceptanceCriteriaDetectionResult(has_ac=False)

        # Search for AC heading
        match = AC_HEADING_PATTERN.search(description)

        if not match:
            logger.debug("no_ac_block_detected")
            return AcceptanceCriteriaDetectionResult(has_ac=False)

        # Found AC block - extract content
        ac_start = match.end()

        # Find the end of AC block (next heading or end of description)
        next_heading = re.search(r"\n#+\s+\w+", description[ac_start:])
        ac_end = (
            ac_start + next_heading.start() if next_heading else len(description)
        )

        ac_content = description[ac_start:ac_end].strip()

        logger.debug(
            "ac_block_detected",
            ac_start=match.start(),
            ac_end=ac_end,
            ac_length=len(ac_content),
        )

        return AcceptanceCriteriaDetectionResult(
            has_ac=True,
            ac_content=ac_content,
            ac_start_index=match.start(),
            ac_end_index=ac_end,
        )

    async def update_ticket_ac(
        self,
        ticket_key: str,
        new_ac: str,
        detection_result: AcceptanceCriteriaDetectionResult,
        current_description: str,
    ) -> JiraUpdateResult:
        """
        Update ticket with new acceptance criteria.

        Behavior:
        - If AC exists: Replaces existing AC block
        - If no AC exists: Appends AC to end of description

        Args:
            ticket_key: Jira ticket key (e.g., "PROJ-123")
            new_ac: New acceptance criteria content
            detection_result: Result from detect_acceptance_criteria()
            current_description: Current ticket description

        Returns:
            JiraUpdateResult: Update operation result

        Raises:
            JiraPermissionError: If user lacks permission to edit
            JiraConnectionError: If API call fails
        """
        if not self._client:
            raise JiraConnectionError("Jira client not connected. Call connect() first.")

        try:
            # Build new description based on whether AC exists
            if detection_result.has_ac and detection_result.ac_start_index is not None:
                # Replace existing AC block
                new_description = (
                    current_description[: detection_result.ac_start_index]
                    + f"\n## Acceptance Criteria\n\n{new_ac}\n"
                    + current_description[detection_result.ac_end_index :]
                )
                action = "updated"
            else:
                # Append AC to end of description
                separator = "\n\n" if current_description.strip() else ""
                new_description = (
                    f"{current_description}{separator}## Acceptance Criteria\n\n{new_ac}"
                )
                action = "added"

            # Convert plain text to ADF format for Jira Cloud
            adf_description = self._text_to_adf(new_description)

            # Update ticket via REST API
            response = await self._client.put(
                f"/rest/api/3/issue/{ticket_key}",
                json={"fields": {"description": adf_description}},
            )

            if response.status_code == 403:
                raise JiraPermissionError(
                    f"You don't have permission to edit ticket {ticket_key}"
                )
            elif response.status_code == 401:
                raise JiraConnectionError(
                    "Authentication failed. Check your Jira credentials."
                )

            response.raise_for_status()

            ticket_url = f"{self._base_url}/browse/{ticket_key}"

            logger.info(
                "jira_ticket_updated",
                ticket_key=ticket_key,
                action=action,
            )

            return JiraUpdateResult(
                success=True,
                ticket_key=ticket_key,
                ticket_url=ticket_url,
                message=f"Acceptance criteria {action} in {ticket_key}",
            )

        except JiraPermissionError:
            raise
        except JiraConnectionError:
            raise
        except Exception as e:
            logger.error(
                "jira_ticket_update_failed",
                ticket_key=ticket_key,
                error=str(e),
                exc_info=True,
            )

            return JiraUpdateResult(
                success=False,
                ticket_key=ticket_key,
                ticket_url=f"{self._base_url}/browse/{ticket_key}",
                message=f"Failed to update ticket {ticket_key}",
                error=str(e),
            )

    def _text_to_adf(self, text: str) -> dict:
        """
        Convert plain text to Atlassian Document Format (ADF).

        This creates a simple ADF document with paragraphs.

        Args:
            text: Plain text content

        Returns:
            dict: ADF document structure
        """
        paragraphs = text.split("\n\n")
        content = []

        for para in paragraphs:
            if para.strip():
                # Handle lines within paragraph
                lines = para.split("\n")
                para_content = []

                for i, line in enumerate(lines):
                    if line.strip():
                        para_content.append({"type": "text", "text": line})
                        if i < len(lines) - 1:
                            para_content.append({"type": "hardBreak"})

                if para_content:
                    content.append({
                        "type": "paragraph",
                        "content": para_content,
                    })

        return {
            "version": 1,
            "type": "doc",
            "content": content,
        }


# Singleton instance
_jira_service: JiraService | None = None


async def get_jira_service() -> JiraService:
    """
    Get or create the singleton Jira service instance.

    Returns:
        JiraService: Configured Jira service instance
    """
    global _jira_service

    if _jira_service is None:
        _jira_service = JiraService()
        await _jira_service.connect()

    return _jira_service


async def close_jira_service() -> None:
    """Close and clean up Jira service connection."""
    global _jira_service

    if _jira_service is not None:
        await _jira_service.disconnect()
        _jira_service = None
