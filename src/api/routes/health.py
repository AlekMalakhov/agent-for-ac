"""Health check endpoints."""

from fastapi import APIRouter, status

from src.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Returns HTTP 200 to indicate the API is running.

    Returns:
        HealthResponse: Health status and service name.
    """
    return HealthResponse(
        status="healthy",
        service="agent-for-ac",
    )
