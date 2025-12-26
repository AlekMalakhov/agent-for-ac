#!/usr/bin/env python3
"""
Simple script to generate AC and save to file.

Usage:
    USE_REAL_LLM=true uv run python test_generate_ac.py
"""

import asyncio
import sys
from datetime import datetime

sys.path.insert(0, ".")

from src.agents.workflow import create_ac_workflow, create_initial_state


async def main():
    print("🚀 Generating acceptance criteria with real LLM...\n")

    # Create workflow
    workflow = create_ac_workflow()

    # Create initial state with your ticket data
    state = create_initial_state(
        ticket_key="TEST-PASSWORD-RESET",
        ticket_title="Add Password Reset Feature",
        ticket_description="""As a user who forgot my password, I want to reset it via email
        so that I can regain access to my account. The system should send a reset link to
        my registered email address.""",
        ticket_type="Story",
        ticket_url="https://example.atlassian.net/browse/TEST-PASSWORD-RESET",
        user_id="U12345",
        selected_format="checklist",  # Options: checklist, bdd, free
    )

    print("Running AI workflow...")
    print("This may take 10-30 seconds...\n")

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
    filename = f"generated_ac_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("GENERATED ACCEPTANCE CRITERIA\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Ticket: {state['ticket_key']}\n")
        f.write(f"Title: {state['ticket_title']}\n")
        f.write(f"Format: {state['selected_format']}\n")
        f.write(f"Generated: {timestamp}\n\n")
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
    print()


if __name__ == "__main__":
    asyncio.run(main())
