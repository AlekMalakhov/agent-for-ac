# Documentation

Welcome to the Agent for AC documentation.

## Getting Started

- [Quick Start Guide](../QUICKSTART.md) - Get running in 5 minutes
- [README](../README.md) - Project overview and features

## Setup Guides

- [Slack Setup](SLACK_SETUP.md) - Configure your Slack app
- [Jira Setup](JIRA_SETUP.md) - Get Jira API credentials

## Development

- [Development Guide](DEVELOPMENT.md) - Architecture, patterns, and workflows
- [Block Kit Guide](BLOCK_KIT_GUIDE.md) - Slack UI development

## Testing

- [Testing Guide](TESTING_GUIDE.md) - Overview of all tests
- [Testing Quick Reference](TESTING_QUICK_REFERENCE.md) - Quick command reference
- [Test Slack Commands](TEST_SLACK_COMMANDS.md) - Slack integration testing
- [Test Health Check](TEST_HEALTH_CHECK.md) - Health check testing
- [Test AI Orchestration](TEST_AI_ORCHESTRATION.md) - AI agent testing

## AI Agents

- [AI Orchestration Quick Reference](AI_ORCHESTRATION_QUICK_REFERENCE.md) - Agent system overview

## Reference

- [Implementation History](IMPLEMENTATION_HISTORY.md) - Historical implementation notes (outdated - reflects DB-based architecture)

## Architecture

The application uses a **stateless architecture** without databases:
- State managed in-memory during active workflows
- Conversation context in Slack threads
- Jira data fetched on-demand
- No persistent storage required

See [../context/product/architecture.md](../context/product/architecture.md) for detailed architecture documentation.
