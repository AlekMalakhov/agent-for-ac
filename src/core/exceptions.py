"""Core exception hierarchy for the application."""


class ApplicationError(Exception):
    """
    Base exception for all application errors.

    All custom exceptions in the application should inherit from this base class
    to enable consistent error handling and logging.
    """

    pass


class ConfigurationError(ApplicationError):
    """
    Raised when configuration is invalid or missing.

    Examples:
        - Missing required environment variables
        - Invalid configuration values
        - Configuration file parsing errors
    """

    pass


class SlackConnectionError(ApplicationError):
    """
    Raised when Slack connection fails.

    Examples:
        - Invalid Slack tokens
        - Slack API connection timeout
        - Socket mode connection failure
    """

    pass


class JiraError(ApplicationError):
    """
    Base exception for all Jira-related errors.

    All Jira integration exceptions should inherit from this base class.
    """

    pass


class JiraConnectionError(JiraError):
    """
    Raised when connection to Jira MCP server fails.

    Examples:
        - MCP server unreachable
        - OAuth authentication failure
        - Invalid MCP configuration
    """

    pass


class JiraTicketNotFoundError(JiraError):
    """
    Raised when a Jira ticket is not found.

    Examples:
        - Invalid ticket key
        - Ticket deleted
        - Ticket does not exist
    """

    pass


class JiraPermissionError(JiraError):
    """
    Raised when user lacks permission to access a Jira ticket.

    Examples:
        - User cannot view ticket
        - User cannot edit ticket
        - Ticket in restricted project
    """

    pass


class JiraUnsupportedTicketTypeError(JiraError):
    """
    Raised when ticket type is not supported.

    Only Story and Task ticket types are supported for AC generation.
    """

    pass


class JiraInvalidTicketLinkError(JiraError):
    """
    Raised when ticket link format is invalid.

    Examples:
        - Malformed URL
        - Invalid ticket key format
        - Missing ticket identifier
    """

    pass


class SlackContextError(ApplicationError):
    """
    Base exception for Slack context gathering errors.

    All Slack context exceptions should inherit from this base class.
    """

    pass


class SlackAPIError(SlackContextError):
    """
    Raised when Slack API call fails.

    Examples:
        - API rate limiting
        - Network errors
        - Invalid channel access
    """

    pass


class SlackScopeError(SlackContextError):
    """
    Raised when required Slack scopes are missing.

    Examples:
        - Missing channels:history scope
        - Missing groups:history scope
    """

    pass
