"""Vercel serverless function entry point."""

from src.api.app import create_app

# Create the FastAPI app instance for Vercel
app = create_app()
