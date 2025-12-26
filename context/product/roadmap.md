# Product Roadmap: Agent for AC

_This roadmap outlines our strategic direction based on customer needs and business goals. It focuses on the "what" and "why," not the technical "how."_

---

### Phase 1: Foundation & Core AC Generation (Local Deployment)

_The highest priority features that form the core foundation of the product - enabling basic AC generation workflow through Slack bot interaction. Designed for local deployment._

- [x] **Slack Bot Interface & Authentication** ✅ _Completed_
  - [x] **Slack Bot Setup:** Deploy and configure the Slack bot within the company workspace for local testing.
  - [x] **Workspace-Based Authentication:** Authenticate users through Slack workspace permissions - no separate login required.
  - [x] **Basic Bot Commands:** Implement core slash commands (e.g., `/ac-agent <jira-link>`) to trigger AC generation.
  - [x] **Direct Messaging Support:** Enable users to interact with the bot via direct messages for a conversational experience.

- [x] **Jira Integration Fundamentals** ✅ _Completed_
  - [x] **Jira Ticket Analysis:** Connect to Jira and read ticket content (title, description, comments, fields) for Stories and Tasks.
  - [x] **AC Detection:** Automatically determine whether acceptance criteria already exist on a given ticket.
  - [x] **Jira Ticket Updates:** Write generated or improved acceptance criteria back to the specified Jira ticket field.

- [x] **AI/LLM Orchestration (Multi-Agent System)** ✅ _Completed_
  - [x] **Orchestrator Agent:** Analyzes ticket information and decides workflow routing (Information Gatherer vs. Generator).
  - [x] **Information Gatherer Agent:** Asks clarifying questions when information is insufficient (max 5 questions).
  - [x] **Generator Agent:** Generates acceptance criteria in multiple formats (Checklist, BDD, Free format).
  - [x] **Evaluator Agent:** Scores AC quality (1-10 scale) and provides improvement feedback.
  - [x] **LangGraph Workflow:** Multi-agent orchestration with conditional routing and retry logic.
  - [x] **LLM Provider Support:** Anthropic API and AWS Bedrock integration.

- [x] **End-to-End Integration & User Approval** ✅ _Completed_
  - [x] **Slack Command Integration:** Wire `/ac-agent <jira-link>` to trigger full workflow (Jira → AI → Slack).
  - [x] **Format Selection UI:** Allow users to choose AC format (Checklist, BDD, Free) via Slack messages.
  - [x] **Progress Feedback:** Display real-time progress messages during AC generation.
  - [x] **Interactive Chat Refinement:** Allow users to refine AC through natural language conversation.
  - [x] **Approval Workflow:** Show generated AC with approval options.
  - [x] **Jira Update on Approval:** Automatically write approved AC to Jira ticket description.

---

### Phase 2: Context Enrichment & Quality Evaluation

_Once the foundational features are complete, we will enhance AC quality through Slack context gathering and introduce quality evaluation._

- [ ] **Slack Context Gathering**
  - [ ] **Slack Thread Access:** Access and read Slack channel threads and conversations related to the ticket.
  - [ ] **Smart Context Extraction:** Automatically scan related Slack conversations and extract relevant discussions about the ticket or feature.
  - [ ] **Enriched AC Generation:** Enhance Agent 1 to incorporate Slack conversation context into AC generation for more comprehensive results.

- [ ] **Interactive Q&A Flow (via Slack)**
  - [ ] **Gap Detection:** Identify when gathered information is insufficient for high-quality AC generation.
  - [ ] **Conversational Questions:** Ask clarifying questions to the user through Slack messages in their preferred language.
  - [ ] **Interactive Buttons/Menus:** Use Slack's interactive components (buttons, select menus) for quick responses when applicable.
  - [ ] **Answer Integration:** Process user responses and incorporate them into the AC generation process.

- [x] **Quality Evaluation (Agent 2)** ✅ _Core Completed, Slack Display Pending_
  - [x] **AC Quality Assessment:** Evaluate generated or existing acceptance criteria against quality standards (completeness, clarity, testability).
  - [x] **Actionable Recommendations:** Provide specific, actionable suggestions for improving AC quality.
  - [ ] **Quality Scoring Display:** Show quality scores and evaluation results in a clear, formatted Slack message.

---

### Phase 3: Workflow Optimization & Production Readiness

_Features planned to streamline workflows, improve user satisfaction, and prepare for broader deployment based on feedback from earlier phases._

- [x] **User Review & Approval Workflow (in Slack)** ✅ _Completed_
  - [x] **Side-by-Side Review:** Display generated AC and evaluation results together in formatted Slack messages.
  - [x] **In-Chat Editing:** Allow users to request modifications to generated AC through conversational commands.
  - [x] **Natural Language Refinement:** Refiner agent classifies user intent (modify, add, remove, format change, regenerate).
  - [x] **Surgical Modifications:** Modifier agent applies targeted edits without full regeneration.
  - [x] **Approval Actions:** Simple text commands for "Approve & Update Jira" or other actions.

- [ ] **Production Deployment & Scaling**
  - [ ] **Cloud Deployment:** Deploy the bot to a cloud environment for reliable 24/7 availability.
  - [ ] **Multi-Workspace Support:** Enable the bot to work across multiple Slack workspaces if needed.
  - [ ] **Performance Optimization:** Ensure fast response times even under heavy usage.

- [ ] **Enhanced Features & Analytics**
  - [ ] **Processing History in Slack:** Allow users to view their recently processed tickets using bot commands (e.g., `/ac-agent history`).
  - [ ] **Quick Re-Generation:** Enable users to quickly regenerate AC with additional context through simple commands.
  - [ ] **Usage Metrics:** Provide users with personal statistics (time saved, quality improvements, tickets processed) via bot command.
  - [ ] **API Access (Future):** Consider offering an API for programmatic access to AC generation capabilities.
