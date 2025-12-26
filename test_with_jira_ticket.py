#!/usr/bin/env python3
"""
Generate AC for a real Jira ticket.

Usage:
    USE_REAL_LLM=true uv run python test_with_jira_ticket.py PROJ-123
"""

import asyncio
import sys
from datetime import datetime

sys.path.insert(0, ".")

from src.agents.workflow import create_ac_workflow, create_initial_state
from src.services.jira import JiraService


async def main():
    if len(sys.argv) < 2:
        print("Usage: USE_REAL_LLM=true uv run python test_with_jira_ticket.py PROJ-123")
        sys.exit(1)

    ticket_input = sys.argv[1]

    print(f"🔍 Fetching Jira ticket: {ticket_input}\n")

    # Initialize Jira service
    jira_service = JiraService()
    await jira_service.connect()

    try:
        # Fetch ticket from Jira
        ticket = await jira_service.get_ticket(ticket_input)

        print("✅ Ticket retrieved successfully!")
        print(f"   Key: {ticket.key}")
        print(f"   Title: {ticket.title}")
        print(f"   Type: {ticket.ticket_type}")
        print(f"   Status: {ticket.status}")
        print(f"   Description length: {len(ticket.description)} chars\n")

        # Check if AC already exists
        detection = jira_service.detect_acceptance_criteria(ticket.description)
        if detection.has_ac:
            print("⚠️  Note: This ticket already has acceptance criteria")
            print(f"   Existing AC length: {len(detection.ac_content or '')} chars\n")

        # Ask for format preference
        print("Select format:")
        print("  1. Checklist (default)")
        print("  2. BDD (Given/When/Then)")
        print("  3. Free format")
        format_choice = input("Enter choice (1-3, default=1): ").strip() or "1"

        format_map = {"1": "checklist", "2": "bdd", "3": "free"}
        selected_format = format_map.get(format_choice, "checklist")

        print(f"\n🚀 Generating acceptance criteria in {selected_format} format...")
        print("This may take 10-30 seconds...\n")

        # Create workflow
        workflow = create_ac_workflow()

        # Create initial state
        state = create_initial_state(
            ticket_key=ticket.key,
            ticket_title=ticket.title,
            ticket_description=ticket.description,
            ticket_type=ticket.ticket_type,
            ticket_url=ticket.url,
            user_id="CLI_USER",
            selected_format=selected_format,
        )

        # Run workflow
        result = await workflow.ainvoke(state)

        # Display results
        print("=" * 80)
        print("📋 GENERATED ACCEPTANCE CRITERIA")
        print("=" * 80)
        print()
        print(result.get("generated_ac", "No AC generated"))
        print()
        print("=" * 80)
        print(f"⭐ Quality Score: {result.get('quality_score', 'N/A')}/10")
        print(f"🔄 Generation Attempts: {result.get('generation_attempts', 0)}")
        print(f"❓ Questions Asked: {result.get('questions_asked', 0)}")
        print(f"✅ Complete: {result.get('is_complete', False)}")
        print("=" * 80)

        if result.get("evaluation_feedback"):
            print()
            print("📝 EVALUATOR FEEDBACK:")
            print(result["evaluation_feedback"])

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_key = ticket.key.replace("-", "_")
        filename = f"generated_ac_{safe_key}_{timestamp}.txt"

        with open(filename, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("GENERATED ACCEPTANCE CRITERIA\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Ticket: {ticket.key}\n")
            f.write(f"Title: {ticket.title}\n")
            f.write(f"Type: {ticket.ticket_type}\n")
            f.write(f"Status: {ticket.status}\n")
            f.write(f"Format: {selected_format}\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"URL: {ticket.url}\n\n")
            f.write("=" * 80 + "\n\n")
            f.write(result.get("generated_ac", "No AC generated"))
            f.write("\n\n" + "=" * 80 + "\n")
            f.write(f"Quality Score: {result.get('quality_score', 'N/A')}/10\n")
            f.write(f"Generation Attempts: {result.get('generation_attempts', 0)}\n")
            f.write(f"Questions Asked: {result.get('questions_asked', 0)}\n")
            f.write("=" * 80 + "\n")

            if result.get("evaluation_feedback"):
                f.write("\nEvaluator Feedback:\n")
                f.write(result["evaluation_feedback"])
                f.write("\n")

        print()
        print(f"💾 Results saved to: {filename}")

        # Ask if user wants to update Jira
        update = input("\nUpdate Jira ticket with generated AC? (y/N): ").strip().lower()

        if update == "y":
            print("\n📝 Updating Jira ticket...")
            update_result = await jira_service.update_ticket_ac(
                ticket_key=ticket.key,
                new_ac=result["generated_ac"],
                detection_result=detection,
                current_description=ticket.description,
            )

            if update_result.success:
                print(f"✅ {update_result.message}")
                print(f"🔗 View ticket: {update_result.ticket_url}")
            else:
                print(f"❌ Failed to update: {update_result.error}")
        else:
            print("\nℹ️  Jira ticket not updated. AC saved to file only.")

    finally:
        await jira_service.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
