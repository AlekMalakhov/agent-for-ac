"""Unit tests for Jira service."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from src.core.exceptions import (
    JiraInvalidTicketLinkError,
    JiraUnsupportedTicketTypeError,
)
from src.schemas.jira import AcceptanceCriteriaDetectionResult
from src.services.jira import JiraService


class TestJiraService:
    """Test suite for JiraService class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        mock = MagicMock()
        mock.jira_site_url = "https://test.atlassian.net"
        mock.jira_oauth_client_id = SecretStr("test-client-id")
        mock.jira_oauth_client_secret = SecretStr("test-client-secret")
        return mock

    @pytest.fixture
    def jira_service(self, mock_settings):
        """Create a JiraService instance for testing."""
        with patch("src.services.jira.get_settings", return_value=mock_settings):
            return JiraService()

    def test_parse_ticket_identifier_full_url(self, jira_service):
        """Test parsing ticket key from full Jira URL."""
        url = "https://mycompany.atlassian.net/browse/PROJ-123"
        result = jira_service.parse_ticket_identifier(url)
        assert result == "PROJ-123"

    def test_parse_ticket_identifier_short_key(self, jira_service):
        """Test parsing ticket key from short format."""
        key = "PROJ-456"
        result = jira_service.parse_ticket_identifier(key)
        assert result == "PROJ-456"

    def test_parse_ticket_identifier_invalid_format(self, jira_service):
        """Test parsing invalid ticket format raises error."""
        with pytest.raises(JiraInvalidTicketLinkError) as exc_info:
            jira_service.parse_ticket_identifier("invalid-ticket")

        assert "Invalid ticket format" in str(exc_info.value)

    def test_parse_ticket_identifier_with_whitespace(self, jira_service):
        """Test parsing ticket key with surrounding whitespace."""
        key_with_space = "  PROJ-789  "
        result = jira_service.parse_ticket_identifier(key_with_space)
        assert result == "PROJ-789"


class TestAcceptanceCriteriaDetection:
    """Test suite for AC detection logic."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        mock = MagicMock()
        mock.jira_site_url = "https://test.atlassian.net"
        mock.jira_oauth_client_id = SecretStr("test-client-id")
        mock.jira_oauth_client_secret = SecretStr("test-client-secret")
        return mock

    @pytest.fixture
    def jira_service(self, mock_settings):
        """Create a JiraService instance for testing."""
        with patch("src.services.jira.get_settings", return_value=mock_settings):
            return JiraService()

    def test_detect_ac_with_standard_heading(self, jira_service):
        """Test detection of AC with standard heading."""
        description = """
This is a ticket description.

## Acceptance Criteria

- User can log in
- User can log out
- Session persists

## Additional Notes
Some other content.
"""
        result = jira_service.detect_acceptance_criteria(description)

        assert result.has_ac is True
        assert "User can log in" in result.ac_content
        assert "User can log out" in result.ac_content
        assert result.ac_start_index is not None
        assert result.ac_end_index is not None

    def test_detect_ac_with_ac_abbreviation(self, jira_service):
        """Test detection of AC with 'AC' abbreviation."""
        description = """
Ticket description here.

AC:
- Criteria 1
- Criteria 2
"""
        result = jira_service.detect_acceptance_criteria(description)

        assert result.has_ac is True
        assert "Criteria 1" in result.ac_content

    def test_detect_ac_case_insensitive(self, jira_service):
        """Test AC detection is case-insensitive."""
        description = """
Description text.

acceptance criteria:
- Test case 1
- Test case 2
"""
        result = jira_service.detect_acceptance_criteria(description)

        assert result.has_ac is True
        assert "Test case 1" in result.ac_content

    def test_detect_ac_not_found(self, jira_service):
        """Test AC detection when no AC block exists."""
        description = """
This is a ticket description without any acceptance criteria section.

## Implementation Notes
Some notes here.
"""
        result = jira_service.detect_acceptance_criteria(description)

        assert result.has_ac is False
        assert result.ac_content is None
        assert result.ac_start_index is None
        assert result.ac_end_index is None

    def test_detect_ac_empty_description(self, jira_service):
        """Test AC detection with empty description."""
        result = jira_service.detect_acceptance_criteria("")

        assert result.has_ac is False

    def test_detect_ac_at_end_of_description(self, jira_service):
        """Test AC detection when AC is at the end."""
        description = """
Ticket description.

## Acceptance Criteria
- Final criteria
- Last point
"""
        result = jira_service.detect_acceptance_criteria(description)

        assert result.has_ac is True
        assert "Final criteria" in result.ac_content
        assert "Last point" in result.ac_content


class TestTicketLinkParsing:
    """Test suite for ticket link parsing edge cases."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        mock = MagicMock()
        mock.jira_site_url = "https://test.atlassian.net"
        mock.jira_oauth_client_id = SecretStr("test-client-id")
        mock.jira_oauth_client_secret = SecretStr("test-client-secret")
        return mock

    @pytest.fixture
    def jira_service(self, mock_settings):
        """Create a JiraService instance for testing."""
        with patch("src.services.jira.get_settings", return_value=mock_settings):
            return JiraService()

    def test_parse_url_with_query_parameters(self, jira_service):
        """Test parsing URL with query parameters."""
        url = "https://mycompany.atlassian.net/browse/PROJ-123?filter=myfilter"
        result = jira_service.parse_ticket_identifier(url)
        assert result == "PROJ-123"

    def test_parse_url_with_anchor(self, jira_service):
        """Test parsing URL with anchor."""
        url = "https://mycompany.atlassian.net/browse/PROJ-123#comment-12345"
        result = jira_service.parse_ticket_identifier(url)
        assert result == "PROJ-123"

    def test_parse_key_with_multiple_digits(self, jira_service):
        """Test parsing ticket key with many digits."""
        key = "PROJECT-123456"
        result = jira_service.parse_ticket_identifier(key)
        assert result == "PROJECT-123456"

    def test_parse_invalid_lowercase_key(self, jira_service):
        """Test parsing lowercase key (should fail)."""
        with pytest.raises(JiraInvalidTicketLinkError):
            jira_service.parse_ticket_identifier("proj-123")

    def test_parse_invalid_no_number(self, jira_service):
        """Test parsing key without number (should fail)."""
        with pytest.raises(JiraInvalidTicketLinkError):
            jira_service.parse_ticket_identifier("PROJ-")


class TestAcceptanceCriteriaDetectionResult:
    """Test suite for AcceptanceCriteriaDetectionResult schema."""

    def test_detection_result_with_ac(self):
        """Test creating detection result with AC found."""
        result = AcceptanceCriteriaDetectionResult(
            has_ac=True,
            ac_content="Sample AC content",
            ac_start_index=100,
            ac_end_index=200,
        )

        assert result.has_ac is True
        assert result.ac_content == "Sample AC content"
        assert result.ac_start_index == 100
        assert result.ac_end_index == 200

    def test_detection_result_without_ac(self):
        """Test creating detection result without AC."""
        result = AcceptanceCriteriaDetectionResult(has_ac=False)

        assert result.has_ac is False
        assert result.ac_content is None
        assert result.ac_start_index is None
        assert result.ac_end_index is None
