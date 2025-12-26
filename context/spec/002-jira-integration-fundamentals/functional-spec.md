# Functional Specification: Jira Integration Fundamentals

- **Roadmap Item:** Jira Integration Fundamentals (Phase 1)
- **Status:** Approved
- **Author:** Claude (Agent for AC Team)

---

## 1. Overview and Rationale (The "Why")

### Purpose
Agent for AC needs to integrate with Jira to enable the core workflow:
- Users share Jira ticket links in Slack
- The agent retrieves ticket content from Jira
- The agent detects whether acceptance criteria (AC) already exist
- The agent generates or updates AC and writes them back to the Jira ticket

This integration is foundational to the product's value proposition: reducing time spent on AC creation by 60% and improving AC completeness by 40%.

### Context
- **Target Users**: Product Managers and QA Engineers using Jira Cloud
- **Integration Method**: Atlassian's official Remote MCP Server (OAuth 2.1 authentication)
- **Supported Ticket Types**: Stories and Tasks only (Epics, Bugs, and other types are out of scope per product definition)

### Success Metrics
- Successfully read Jira ticket content in 95%+ of valid requests
- Accurately detect existing AC in ticket descriptions
- Successfully write AC back to Jira in 95%+ of attempts
- Clear error feedback for permission issues, invalid tickets, or unsupported ticket types

---

## 2. Functional Requirements (The "What")

### FR-1: MCP Server Setup and Authentication

**As a** system administrator, **I want to** configure the Atlassian Remote MCP Server connection, **so that** Agent for AC can securely access Jira Cloud.

**Acceptance Criteria:**
- [ ] The system uses Atlassian's official Remote MCP Server endpoint (`https://mcp.atlassian.com/v1/sse`)
- [ ] Authentication uses OAuth 2.1 authorization flow
- [ ] The system respects existing Atlassian user permissions (no privilege escalation)
- [ ] Configuration requires: Jira Cloud site URL, OAuth client credentials
- [ ] The system validates MCP server connection during setup
- [ ] Clear error messages are shown if MCP server is unreachable or authentication fails

---

### FR-2: Jira Ticket Reading

**As a** user, **I want to** share a Jira ticket link in Slack, **so that** Agent for AC can retrieve the ticket content.

**Acceptance Criteria:**
- [ ] The system accepts Jira ticket links in the format: `https://[site].atlassian.net/browse/[KEY]` (e.g., `https://company.atlassian.net/browse/PROJ-123`)
- [ ] The system accepts short ticket keys in the format: `[PROJECT-KEY]-[NUMBER]` (e.g., `PROJ-123`)
- [ ] The system retrieves the following ticket fields via MCP:
  - Ticket key (e.g., `PROJ-123`)
  - Ticket title/summary
  - Ticket type (e.g., Story, Task, Epic, Bug)
  - Ticket description (full text)
  - Ticket status (e.g., To Do, In Progress, Done)
- [ ] If the ticket link is invalid or ticket does not exist, the system shows a clear error message in Slack
- [ ] If the user lacks permission to view the ticket, the system shows a permission denied error message in Slack
- [ ] The system provides feedback in Slack during ticket retrieval (e.g., "Reading ticket PROJ-123...")

---

### FR-3: Ticket Type Validation

**As a** user, **I want** the system to validate ticket types, **so that** AC generation only works for supported ticket types (Story, Task).

**Acceptance Criteria:**
- [ ] After retrieving a ticket, the system checks the ticket type
- [ ] If the ticket type is **Story** or **Task**, the system proceeds with AC detection/generation
- [ ] If the ticket type is **Epic**, **Bug**, or any other type, the system shows an error message: "AC generation is only supported for Story and Task ticket types. This ticket is a [TYPE]."
- [ ] The error message is displayed in Slack before any AC processing begins

---

### FR-4: Acceptance Criteria Detection

**As a** user, **I want** the system to detect existing acceptance criteria in the ticket description, **so that** I know whether to generate new AC or update existing ones.

**Acceptance Criteria:**
- [ ] The system searches for an "Acceptance Criteria" block in the Jira ticket's **Description** field
- [ ] An "Acceptance Criteria" block is identified by:
  - The presence of a heading containing the text "Acceptance Criteria" (case-insensitive)
  - Common variations: "Acceptance Criteria", "AC", "Acceptance Criteria:", "## Acceptance Criteria"
- [ ] If an "Acceptance Criteria" block is found, the system marks the ticket as "has existing AC"
- [ ] If no "Acceptance Criteria" block is found, the system marks the ticket as "no existing AC"
- [ ] The detection result is used to determine where to write the generated AC (see FR-5)

---

### FR-5: Writing Acceptance Criteria to Jira

**As a** user, **I want** the system to write generated acceptance criteria to the Jira ticket, **so that** the ticket is updated with high-quality AC.

**Acceptance Criteria:**
- [ ] The system writes generated AC to the ticket's **Description** field via MCP
- [ ] **If existing AC detected** (per FR-4):
  - [ ] The system replaces the existing "Acceptance Criteria" block with the newly generated AC
  - [ ] The system preserves all other content in the description (before and after the AC block)
- [ ] **If no existing AC detected**:
  - [ ] The system appends the generated AC to the end of the description
  - [ ] The system adds a clear heading: "## Acceptance Criteria" or "Acceptance Criteria:"
- [ ] The generated AC is formatted using Jira-compatible markdown/ADF (Atlassian Document Format)
- [ ] After successfully writing AC, the system shows a success message in Slack: "Acceptance criteria added to [TICKET-KEY]" with a link to the ticket
- [ ] If the write operation fails (e.g., permission denied, ticket locked), the system shows a clear error message in Slack

---

### FR-6: User Feedback in Slack

**As a** user, **I want** clear feedback messages during Jira operations, **so that** I know what the system is doing and whether operations succeeded.

**Acceptance Criteria:**
- [ ] The system shows **progress feedback** for long-running operations:
  - "Reading ticket PROJ-123..." (while retrieving ticket)
  - "Generating acceptance criteria..." (while processing)
  - "Updating ticket PROJ-123..." (while writing to Jira)
- [ ] The system shows **success feedback** when operations complete:
  - "Acceptance criteria added to PROJ-123" with a clickable link to the ticket
  - "Acceptance criteria updated in PROJ-123" (if replacing existing AC)
- [ ] The system shows **error feedback** when operations fail:
  - "Unable to read ticket PROJ-123: Permission denied"
  - "Unable to read ticket PROJ-123: Ticket not found"
  - "AC generation is only supported for Story and Task ticket types. This ticket is a Bug."
  - "Unable to update ticket PROJ-123: Permission denied"
  - "Unable to update ticket PROJ-123: Ticket is locked or in a restricted status"
- [ ] All feedback messages are concise, user-friendly, and non-technical

---

### FR-7: Error Handling

**As a** user, **I want** the system to handle errors gracefully, **so that** I receive clear guidance when operations fail.

**Acceptance Criteria:**
- [ ] **Invalid ticket link or key**: Show error message in Slack with guidance on correct format
- [ ] **Ticket not found**: Show error message indicating the ticket does not exist or was deleted
- [ ] **Permission denied** (read): Show error message indicating the user lacks permission to view the ticket
- [ ] **Permission denied** (write): Show error message indicating the user lacks permission to edit the ticket
- [ ] **Unsupported ticket type**: Show error message listing supported types (Story, Task)
- [ ] **MCP server unavailable**: Show error message indicating a temporary connectivity issue and suggest retrying
- [ ] **Rate limit exceeded**: Show error message indicating too many requests and suggest waiting before retrying
- [ ] All error messages include actionable guidance (e.g., "Check your Jira permissions" or "Verify the ticket key is correct")

---

## 3. Scope and Boundaries

### In-Scope
- Integration with **Jira Cloud** via Atlassian's official Remote MCP Server
- OAuth 2.1 authentication and permission management
- Reading ticket content: key, title, type, description, status
- Detecting "Acceptance Criteria" blocks in ticket descriptions
- Writing/updating acceptance criteria in ticket descriptions
- Ticket type validation (Story, Task only)
- User feedback messages in Slack for progress, success, and errors
- Error handling for invalid tickets, permissions, unsupported types, connectivity issues

### Out-of-Scope
- **Jira Server/Data Center** support (only Jira Cloud is supported in Phase 1)
- Support for ticket types other than Story and Task (Epics, Bugs, Sub-tasks, etc.)
- Reading or writing custom Jira fields (only standard Description field)
- Reading or writing Jira comments, attachments, or linked issues
- Bulk operations (processing multiple tickets at once)
- Advanced JQL query support for finding tickets
- Automatic ticket status transitions
- Time tracking or worklog integration
- Notifications to Jira watchers (handled by Jira's native behavior when description is updated)
