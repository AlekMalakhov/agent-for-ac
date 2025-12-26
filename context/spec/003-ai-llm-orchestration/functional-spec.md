# Functional Specification: AI/LLM Orchestration for AC Generation

- **Roadmap Item:** Basic AC Generation (Agent 1) + Quality Evaluation (Agent 2)
- **Status:** Draft
- **Author:** Product Team

---

## 1. Overview and Rationale (The "Why")

### Problem Statement

Project Managers spend significant time writing acceptance criteria for Jira tickets. The quality often suffers due to:
- Rushed writing while juggling multiple responsibilities
- Missing important details and edge cases
- Scattered context across Slack conversations
- Inconsistent formatting across tickets

This leads to developer clarification questions during sprints, causing delays and rework.

### Goal

Implement an AI-powered multi-agent system that:
1. Analyzes Jira ticket content
2. Gathers missing information through conversational Q&A
3. Generates high-quality acceptance criteria in English
4. Evaluates and improves AC quality automatically
5. Writes approved AC back to Jira

### Success Metrics

- Reduce AC writing time by 60%
- Generated AC achieves quality score of 7+ out of 10
- Reduce developer clarification questions by 50%
- User satisfaction score of 8/10 or higher

---

## 2. Functional Requirements (The "What")

### 2.1 Agent Architecture Overview

The system uses a **hybrid multi-agent architecture** with four specialized agents:

```
User → Orchestrator Agent
              ↓
      [Sufficient information?]
              ↓
        NO          YES
        ↓            ↓
  Information    [Ask AC format preference]
  Gatherer              ↓
        ↓         Generator Agent
  [Sufficient?]         ↓
        ↓         Evaluator Agent
       YES              ↓
        ↓         [Score >= 7?]
        └──────→       ↓
                 [User Approval]
                       ↓
                 [Save to Jira]
```

---

### 2.2 Orchestrator Agent

**Purpose:** Lightweight agent that analyzes ticket content and decides the flow.

**Functional Requirements:**

- **FR-ORC-1:** When user submits a Jira ticket link, Orchestrator receives ticket data (title, description, comments).
  - **Acceptance Criteria:**
    - [ ] Orchestrator receives parsed ticket data from Jira service
    - [ ] Orchestrator analyzes whether sufficient information exists for AC generation

- **FR-ORC-2:** Orchestrator decides whether to invoke Information Gatherer or proceed directly to Generator.
  - **Acceptance Criteria:**
    - [ ] If information is insufficient, Orchestrator routes to Information Gatherer
    - [ ] If information is sufficient, Orchestrator asks user about AC format preference
    - [ ] Decision is logged for debugging purposes

---

### 2.3 Information Gatherer Agent

**Purpose:** Specialized agent for collecting missing information through conversational Q&A.

**Functional Requirements:**

- **FR-IG-1:** Agent asks clarifying questions one at a time and waits for user response.
  - **Acceptance Criteria:**
    - [ ] Questions are asked one by one (not batched)
    - [ ] Agent waits for user response before asking next question
    - [ ] Questions are asked in user's language (multilingual support)

- **FR-IG-2:** Agent asks a maximum of 5 questions per session.
  - **Acceptance Criteria:**
    - [ ] Question counter tracks number of questions asked
    - [ ] After 5 questions, agent stops and passes context to Generator
    - [ ] User can interrupt at any time by saying "enough" or "generate"

- **FR-IG-3:** If user doesn't understand or ignores a question, agent reformulates (max 3 times per question).
  - **Acceptance Criteria:**
    - [ ] Agent detects unclear/ignored responses
    - [ ] Agent reformulates question up to 3 times
    - [ ] After 3 failed attempts on a question, agent moves to next question or concludes

- **FR-IG-4:** If insufficient information after max attempts, ticket is marked with [NEEDS CLARIFICATION].
  - **Acceptance Criteria:**
    - [ ] If agent cannot gather minimum required information, AC is NOT generated
    - [ ] Message "[NEEDS CLARIFICATION]" is added to Jira ticket description
    - [ ] User is notified in Slack that more information is needed

---

### 2.4 Generator Agent

**Purpose:** Generates acceptance criteria based on gathered context.

**Functional Requirements:**

- **FR-GEN-1:** Before generating, agent asks user to choose AC format.
  - **Acceptance Criteria:**
    - [ ] User is presented with format options via Slack interactive buttons/menu
    - [ ] Default format is "Checklist"
    - [ ] Available formats: Checklist, Given/When/Then (BDD), Free format
    - [ ] User's preference can be remembered for future generations

- **FR-GEN-2:** Agent generates acceptance criteria in English based on all gathered context.
  - **Acceptance Criteria:**
    - [ ] AC is generated in selected format
    - [ ] AC is always in English regardless of input language
    - [ ] AC includes relevant edge cases and error scenarios
    - [ ] Generated AC is passed to Evaluator Agent

- **FR-GEN-3:** If Evaluator returns score < 7, Generator regenerates AC (max 2 total attempts).
  - **Acceptance Criteria:**
    - [ ] Generator receives feedback from Evaluator
    - [ ] Generator attempts to improve AC based on Evaluator's comments
    - [ ] Maximum 2 generation attempts total
    - [ ] After 2 attempts, best result is used regardless of score

---

### 2.5 Evaluator Agent

**Purpose:** Evaluates quality of generated AC text (clarity, structure, formulation).

**Functional Requirements:**

- **FR-EVAL-1:** Agent evaluates AC quality and provides numerical score (1-10).
  - **Acceptance Criteria:**
    - [ ] Score is provided on scale of 1-10
    - [ ] Score evaluates: clarity, structure, formulation, completeness of text
    - [ ] Score does NOT evaluate business completeness (that is the user's responsibility)

- **FR-EVAL-2:** Agent provides textual comments explaining the score.
  - **Acceptance Criteria:**
    - [ ] Comments explain strengths and weaknesses
    - [ ] Comments provide specific improvement suggestions
    - [ ] Comments are actionable for Generator to improve

- **FR-EVAL-3:** If score < 7, feedback is sent to Generator for retry.
  - **Acceptance Criteria:**
    - [ ] Scores 7-10 are considered acceptable quality
    - [ ] Scores 1-6 trigger regeneration (up to max attempts)
    - [ ] Feedback includes specific areas to improve

---

### 2.6 Interactive Chat Refinement (Refiner & Modifier Agents)

**Purpose:** Enable users to refine generated AC through natural language conversation.

**Functional Requirements:**

- **FR-REF-1:** After AC generation, user enters interactive chat refinement mode.
  - **Acceptance Criteria:**
    - [x] User can provide natural language feedback instead of approve/regenerate/cancel
    - [x] System maintains chat history for context
    - [x] User can make multiple refinements before final approval

- **FR-REF-2:** Refiner Agent classifies user intent from natural language messages.
  - **Acceptance Criteria:**
    - [x] Classifies intent: modify_specific, add_criterion, remove_criterion, change_format, regenerate, approve, cancel, clarification
    - [x] Identifies target criterion by number (e.g., "criterion #3")
    - [x] Extracts modification details from user message
    - [x] Asks for clarification when intent is ambiguous

- **FR-REF-3:** Modifier Agent applies surgical modifications to existing AC.
  - **Acceptance Criteria:**
    - [x] Modifies specific criteria without affecting others
    - [x] Adds new criteria in appropriate locations
    - [x] Removes criteria and renumbers remaining ones
    - [x] Preserves AC format (checklist/BDD/free)
    - [x] Maintains consistent style and structure

- **FR-REF-4:** System supports format changes through chat.
  - **Acceptance Criteria:**
    - [x] User can request format change via natural language (e.g., "Convert to BDD")
    - [x] Generator regenerates AC in new format
    - [x] Quality evaluation performed after format change

- **FR-REF-5:** System supports full regeneration with additional context.
  - **Acceptance Criteria:**
    - [x] User can request regeneration with guidance (e.g., "Regenerate focusing on edge cases")
    - [x] Additional context is incorporated into generation prompt
    - [x] Regeneration resets attempt counters

**Supported Modification Types:**

| User Input Example | Classified Intent | Handler |
|--------------------|-------------------|---------|
| "Make criterion #3 more specific" | modify_specific | Modifier Agent |
| "Add error handling criterion" | add_criterion | Modifier Agent |
| "Remove the last one" | remove_criterion | Modifier Agent |
| "Convert to BDD format" | change_format | Generator Agent |
| "Regenerate focusing on security" | regenerate | Generator Agent |
| "approve" or "looks good" | approve | Save to Jira |
| "cancel" | cancel | End workflow |

---

### 2.7 User Approval & Jira Update

**Functional Requirements:**

- **FR-APP-1:** After successful generation or refinement, AC is shown to user in Slack.
  - **Acceptance Criteria:**
    - [x] Generated AC is displayed in formatted Slack message
    - [x] Quality score and evaluation results are shown
    - [x] Chat refinement instructions are provided
    - [x] User can refine via natural language or approve/cancel

- **FR-APP-2:** Upon approval, AC is written to Jira ticket.
  - **Acceptance Criteria:**
    - [x] AC is added to ticket description
    - [x] AC is added under "Acceptance Criteria" heading
    - [x] Existing AC is replaced if detected
    - [x] Existing ticket content is preserved

- **FR-APP-3:** User receives confirmation with link to updated ticket.
  - **Acceptance Criteria:**
    - [x] Slack message confirms: "Acceptance criteria saved"
    - [x] Message includes clickable link to Jira ticket
    - [x] Message includes final quality score

---

### 2.8 LLM Provider Configuration

**Functional Requirements:**

- **FR-LLM-1:** System supports AWS Bedrock and Anthropic API as LLM providers.
  - **Acceptance Criteria:**
    - [ ] AWS Bedrock (Claude models) is supported
    - [ ] Direct Anthropic API is supported
    - [ ] Provider is configured via environment variables at deployment

- **FR-LLM-2:** Administrator configures LLM provider through environment variables.
  - **Acceptance Criteria:**
    - [ ] `LLM_PROVIDER` variable selects provider ("bedrock" or "anthropic")
    - [ ] Provider-specific credentials are configured via environment variables
    - [ ] System validates configuration on startup

---

## 3. Scope and Boundaries

### In-Scope

- Orchestrator Agent for flow control
- Information Gatherer Agent for Q&A (max 5 questions, 3 reformulations per question)
- Generator Agent for AC creation (max 2 attempts)
- Evaluator Agent for quality scoring (1-10 scale with comments)
- **Refiner Agent for intent classification (chat refinement)**
- **Modifier Agent for surgical AC modifications**
- **Interactive chat refinement mode** with natural language processing
- **Format changes** through conversational commands
- User approval workflow before Jira update
- AC format selection (Checklist default, BDD, Free format)
- Support for AWS Bedrock and Anthropic API
- Multilingual user input, English-only AC output
- Writing AC to Jira ticket description

### Out-of-Scope

- Fine-tuning LLM models
- Learning from historical ticket data
- Support for other LLM providers (OpenAI, Google, etc.)
- Caching of LLM responses
- Streaming responses (real-time generation display)
- Bulk processing of multiple tickets
- Custom AC templates per project/team (beyond format selection)
- Persistent conversation history across sessions
