# Agent for AC - Product Summary

## Vision

To empower project managers and QA engineers to create comprehensive, high-quality acceptance criteria in minutes instead of hours, by intelligently gathering context from Jira and Slack and using AI to generate and validate clear requirements that developers can confidently execute.

## Target Audience

Project managers and QA engineers working on software development teams who need to create clear, complete acceptance criteria for Jira tickets (Stories and Tasks). Users may work in international teams and communicate in various languages, but need standardized English acceptance criteria.

## Core Features

- **Jira Ticket Analysis & AC Detection** – Automatically determines if acceptance criteria exist on a ticket
- **Slack Conversation Context Gathering** – Extracts relevant discussions and requirements from Slack threads
- **Multilingual Interactive Q&A** – Asks clarifying questions in the user's language when information is insufficient
- **AI-Powered AC Generation (Agent 1)** – Creates comprehensive acceptance criteria in English
- **AI-Powered AC Quality Evaluation (Agent 2)** – Evaluates AC quality and provides improvement recommendations
- **Automated Jira Ticket Updates** – Writes generated/improved acceptance criteria back to Jira tickets
- **Support for Stories and Tasks** – Handles both Jira Story and Task ticket types

## Key Workflow

1. User provides Jira ticket link
2. System analyzes ticket and checks for existing AC
3. Gathers context from Jira and Slack
4. Asks clarifying questions if needed (in user's language)
5. AI Agent 1 generates AC in English
6. AI Agent 2 evaluates quality and suggests improvements
7. User reviews and approves
8. System updates Jira ticket automatically
