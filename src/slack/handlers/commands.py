"""Slack command handlers."""

from typing import Literal

import structlog
from slack_bolt.async_app import AsyncApp

from src.agents import create_ac_workflow, create_chat_refinement_workflow, create_initial_state
from src.agents.information_gatherer import add_user_answer
from src.agents.refiner import add_user_message_to_chat
from src.core.exceptions import (
    JiraConnectionError,
    JiraInvalidTicketLinkError,
    JiraPermissionError,
    JiraTicketNotFoundError,
    JiraUnsupportedTicketTypeError,
)
from src.services.jira import get_jira_service

logger = structlog.get_logger()

# Store active workflows by user_id for multi-step interactions
_active_workflows: dict = {}


async def handle_health_check(say) -> None:
    """Handle health check command and report system status."""
    message = (
        "✅ *System Health Status*\n\n"
        "✅ Service: `running`\n\n"
        "_All systems operational._"
    )

    await say(message)
    logger.info("health_check_completed")


async def handle_ac_agent_command(ack, command, say):
    """
    Handle /ac-agent slash command.

    This handler processes the /ac-agent command and provides placeholder responses.
    It enforces DM-only usage, provides a welcome message for empty commands,
    and echoes back commands with text.

    Args:
        ack: Slack acknowledgment function (must be called immediately)
        command: Command payload dict with user_id, text, channel_name, etc.
        say: Function to send messages back to the user
    """
    # Acknowledge command immediately to prevent Slack timeout
    await ack()

    # Extract command details
    user_id = command.get("user_id")
    text = command.get("text", "").strip()
    channel_name = command.get("channel_name", "")

    # Log command received with structured logging
    logger.info(
        "command_received",
        user_id=user_id,
        command_text=text,
        channel_name=channel_name,
    )

    # Check if command is in DM (Slack Bolt uses "directmessage" for DM channels)
    if channel_name != "directmessage":
        await say(
            "Slack does not support running slash commands inside threads. "
            "Please use `/ac-agent` in a direct message with me, or mention this app "
            "in a channel or thread (for example: `@Agent for AC health`)."
        )
        return

    # Handle health check command
    if text.lower() == "health":
        await handle_health_check(say)
        return

    # Handle empty command - show welcome message
    if not text:
        welcome_message = (
            "👋 Hello! I'm the Agent for AC bot.\n\n"
            "I can help you generate and evaluate acceptance criteria for Jira tickets.\n\n"
            "*Available commands:*\n"
            "• `/ac-agent health` - Check system health\n"
            "• `/ac-agent <jira-link>` - Generate or evaluate acceptance criteria (coming soon)\n\n"
            "Try sending me a command!"
        )
        await say(welcome_message)
        return

    # Handle Jira ticket link - process AC generation
    await handle_jira_ticket(say, text, user_id)


async def handle_jira_ticket(say, ticket_input: str, user_id: str) -> None:
    """
    Handle Jira ticket processing for AC generation using AI agents.

    This function:
    1. Reads the Jira ticket
    2. Starts the AI agent workflow
    3. Handles information gathering interactions
    4. Presents generated AC for user approval

    Args:
        say: Slack say function for sending messages
        ticket_input: Jira ticket URL or key
        user_id: Slack user ID for tracking workflow state
    """
    try:
        # Get Jira service
        jira_service = await get_jira_service()

        # Step 1: Read ticket
        await say("Reading ticket...")
        ticket = await jira_service.get_ticket(ticket_input)

        await say(
            f"*{ticket.key}* - {ticket.title}\n"
            f"Type: {ticket.ticket_type} | Status: {ticket.status}"
        )

        # Step 2: Detect existing AC
        detection_result = jira_service.detect_acceptance_criteria(ticket.description)

        if detection_result.has_ac:
            await say(
                f"Existing acceptance criteria detected in {ticket.key}. "
                "I will update them with improved criteria."
            )
        else:
            await say(
                f"No acceptance criteria found in {ticket.key}. "
                "I will generate new criteria."
            )

        # Step 3: Ask for AC format preference
        await say(
            "*Choose acceptance criteria format:*\n"
            "• `checklist` - Simple checkbox format (default)\n"
            "• `bdd` - Gherkin Given/When/Then format\n"
            "• `free` - Narrative format\n\n"
            "Reply with your preferred format or press Enter for checklist."
        )

        # Store workflow context for format selection
        _active_workflows[user_id] = {
            "stage": "format_selection",
            "ticket": ticket,
            "detection_result": detection_result,
            "jira_service": jira_service,
        }

        logger.info(
            "workflow_started",
            ticket_key=ticket.key,
            user_id=user_id,
        )

    except JiraInvalidTicketLinkError as e:
        await say(
            f"*Invalid ticket link*\n\n"
            f"{str(e)}\n\n"
            f"Please provide either:\n"
            f"• Full URL: `https://site.atlassian.net/browse/PROJ-123`\n"
            f"• Ticket key: `PROJ-123`"
        )
        logger.warning("invalid_ticket_link", error=str(e))

    except JiraTicketNotFoundError as e:
        await say(
            f"*Ticket not found*\n\n"
            f"{str(e)}\n\n"
            f"Please verify the ticket key is correct and the ticket exists."
        )
        logger.warning("ticket_not_found", error=str(e))

    except JiraPermissionError as e:
        await say(
            f"*Permission denied*\n\n"
            f"{str(e)}\n\n"
            f"Please check your Jira permissions and ensure you have access to this ticket."
        )
        logger.warning("permission_denied", error=str(e))

    except JiraUnsupportedTicketTypeError as e:
        await say(
            f"*Unsupported ticket type*\n\n"
            f"{str(e)}\n\n"
            f"I can only generate acceptance criteria for *Story* and *Task* ticket types."
        )
        logger.warning("unsupported_ticket_type", error=str(e))

    except JiraConnectionError as e:
        await say(
            f"*Connection error*\n\n"
            f"{str(e)}\n\n"
            f"There was a problem connecting to Jira. Please try again in a moment."
        )
        logger.error("jira_connection_error", error=str(e), exc_info=True)

    except Exception as e:
        await say(
            f"*Unexpected error*\n\n"
            f"An unexpected error occurred while processing your request.\n\n"
            f"Error: {str(e)}"
        )
        logger.error("unexpected_error", error=str(e), exc_info=True)


async def handle_format_selection(
    say, user_id: str, format_text: str
) -> None:
    """
    Handle user's format selection and start the agent workflow.

    Args:
        say: Slack say function
        user_id: Slack user ID
        format_text: User's format choice
    """
    workflow_context = _active_workflows.get(user_id)
    if not workflow_context or workflow_context.get("stage") != "format_selection":
        return

    # Parse format selection
    format_text = format_text.lower().strip()
    if format_text in ("bdd", "gherkin"):
        selected_format: Literal["checklist", "bdd", "free"] = "bdd"
    elif format_text == "free":
        selected_format = "free"
    else:
        selected_format = "checklist"

    ticket = workflow_context["ticket"]

    await say(f"Format selected: *{selected_format}*\n\nAnalyzing ticket information...")

    # Create initial workflow state
    initial_state = create_initial_state(
        ticket_key=ticket.key,
        ticket_title=ticket.title,
        ticket_description=ticket.description or "",
        ticket_type=ticket.ticket_type,
        ticket_url=ticket.url,
        user_id=user_id,
        selected_format=selected_format,
    )

    # Create and run workflow
    workflow = create_ac_workflow()

    try:
        # Run workflow until it pauses (for user input) or completes
        result = await workflow.ainvoke(initial_state)

        # Update workflow context
        workflow_context["state"] = result
        workflow_context["workflow"] = workflow

        # Check if we need to ask a question
        if result.get("current_question"):
            workflow_context["stage"] = "gathering_info"
            await say(f"*Question:* {result['current_question']}")
        elif result.get("generated_ac"):
            # AC generated, enter chat refinement mode
            workflow_context["stage"] = "chat_refinement"
            workflow_context["chat_workflow"] = create_chat_refinement_workflow()
            await show_ac_for_approval(say, result)
        elif result.get("error"):
            await say(f"*Error:* {result['error']}")
            _active_workflows.pop(user_id, None)
        else:
            await say("Workflow completed without generating AC.")
            _active_workflows.pop(user_id, None)

    except Exception as e:
        logger.error("workflow_error", error=str(e), exc_info=True)
        await say(f"*Error during AC generation:* {str(e)}")
        _active_workflows.pop(user_id, None)


async def handle_user_answer(say, user_id: str, answer: str) -> None:
    """
    Handle user's answer to a clarifying question.

    Args:
        say: Slack say function
        user_id: Slack user ID
        answer: User's answer
    """
    workflow_context = _active_workflows.get(user_id)
    if not workflow_context or workflow_context.get("stage") != "gathering_info":
        return

    state = workflow_context["state"]
    workflow = workflow_context["workflow"]

    # Add user answer to state
    state_updates = add_user_answer(state, answer)
    state = {**state, **state_updates}

    await say("Processing your answer...")

    try:
        # Continue workflow
        result = await workflow.ainvoke(state)
        workflow_context["state"] = result

        # Check next step
        if result.get("current_question"):
            await say(f"*Question:* {result['current_question']}")
        elif result.get("generated_ac"):
            workflow_context["stage"] = "chat_refinement"
            workflow_context["chat_workflow"] = create_chat_refinement_workflow()
            await show_ac_for_approval(say, result)
        elif result.get("error"):
            await say(f"*Error:* {result['error']}")
            _active_workflows.pop(user_id, None)
        else:
            await say("Workflow completed.")
            _active_workflows.pop(user_id, None)

    except Exception as e:
        logger.error("workflow_continuation_error", error=str(e), exc_info=True)
        await say(f"*Error:* {str(e)}")
        _active_workflows.pop(user_id, None)


async def show_ac_for_approval(say, state: dict) -> None:
    """
    Display generated AC and enter chat refinement mode.

    Args:
        say: Slack say function
        state: Current workflow state
    """
    generated_ac = state.get("generated_ac", "")
    quality_score = state.get("quality_score", 0)
    ticket_key = state.get("ticket_key", "")
    refinement_count = state.get("refinement_count", 0)

    # Different header for initial vs refined AC
    if refinement_count == 0:
        header = f"*Generated Acceptance Criteria for {ticket_key}*"
    else:
        header = f"*Updated Acceptance Criteria for {ticket_key}* (revision {refinement_count})"

    message = (
        f"{header}\n"
        f"Quality Score: {quality_score}/10\n\n"
        f"```\n{generated_ac}\n```\n\n"
        "*You can now refine these criteria. Try:*\n"
        "• _\"Make criterion #3 more specific\"_\n"
        "• _\"Add an error handling criterion\"_\n"
        "• _\"Convert to BDD format\"_\n"
        "• _\"Remove the last one\"_\n"
        "• _\"Regenerate focusing on edge cases\"_\n\n"
        "Or reply `approve` to save to Jira, `cancel` to abort."
    )

    await say(message)


async def handle_chat_refinement(say, user_id: str, message: str) -> None:
    """
    Handle user message in chat refinement mode.

    Routes to refiner agent, applies modifications, and shows updated AC.

    Args:
        say: Slack say function
        user_id: Slack user ID
        message: User's message
    """
    workflow_context = _active_workflows.get(user_id)
    if not workflow_context or workflow_context.get("stage") != "chat_refinement":
        return

    state = workflow_context["state"]
    chat_workflow = workflow_context.get("chat_workflow")
    jira_service = workflow_context["jira_service"]
    detection_result = workflow_context["detection_result"]
    ticket = workflow_context["ticket"]

    if not chat_workflow:
        chat_workflow = create_chat_refinement_workflow()
        workflow_context["chat_workflow"] = chat_workflow

    # Add user message to chat history and prepare for refiner
    state_updates = add_user_message_to_chat(state, message)
    state = {**state, **state_updates}

    await say("Processing your request...")

    try:
        # Run chat refinement workflow
        result = await chat_workflow.ainvoke(state)
        workflow_context["state"] = result

        intent = result.get("refiner_intent")

        if intent == "approve":
            # User approved, save to Jira
            await say(f"Saving acceptance criteria to {ticket.key}...")

            try:
                update_result = await jira_service.update_ticket_ac(
                    ticket_key=ticket.key,
                    new_ac=result["generated_ac"],
                    detection_result=detection_result,
                    current_description=ticket.description,
                )

                if update_result.success:
                    await say(
                        f"*Success!* {update_result.message}\n"
                        f"View ticket: {update_result.ticket_url}"
                    )
                else:
                    await say(
                        f"*Update failed:* {update_result.message}\n"
                        f"Error: {update_result.error}"
                    )

            except Exception as e:
                logger.error("jira_update_error", error=str(e), exc_info=True)
                await say(f"*Error saving to Jira:* {str(e)}")

            _active_workflows.pop(user_id, None)

        elif intent == "cancel":
            await say("Operation cancelled.")
            _active_workflows.pop(user_id, None)

        elif intent == "clarification":
            # Ask clarification question
            clarification = result.get(
                "clarification_question", "Could you please clarify what you'd like to change?"
            )
            await say(f"*Clarification needed:* {clarification}")

        else:
            # Show updated AC (for modify, add, remove, change_format, regenerate)
            if result.get("generated_ac"):
                await show_ac_for_approval(say, result)
            elif result.get("error"):
                await say(f"*Error:* {result['error']}\n\nYou can try again or reply `cancel` to abort.")
            else:
                await say("Something went wrong. Please try again or reply `cancel` to abort.")

    except Exception as e:
        logger.error("chat_refinement_error", error=str(e), exc_info=True)
        await say(f"*Error:* {str(e)}\n\nYou can try again or reply `cancel` to abort.")


def generate_placeholder_ac(title: str, description: str) -> str:
    """
    Generate placeholder acceptance criteria.

    This is a temporary implementation. Will be replaced with AI-powered generation.

    Args:
        title: Ticket title
        description: Ticket description

    Returns:
        str: Generated acceptance criteria
    """
    return f"""**Given** a user wants to {title.lower()}
**When** they interact with the feature
**Then** the following conditions should be met:

- [ ] The feature is accessible to authorized users
- [ ] The feature performs the expected functionality
- [ ] The feature provides appropriate feedback to the user
- [ ] The feature handles errors gracefully

**Additional Criteria:**
- [ ] All automated tests pass
- [ ] The implementation follows coding standards
- [ ] The feature is documented appropriately

_Note: This is AI-generated placeholder content. Full AC generation will be implemented in the next phase._
"""


def register(app: AsyncApp) -> None:
    """
    Register all command handlers with the Slack app.

    This function registers the /ac-agent command handler using the
    Slack Bolt decorator pattern.

    Args:
        app: AsyncApp instance to register handlers on
    """
    app.command("/ac-agent")(handle_ac_agent_command)
    logger.info("command_handlers_registered")
