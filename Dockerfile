FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml .
COPY uv.lock* .
COPY src/ src/

# Install dependencies
RUN uv sync --frozen

# Default command (can be overridden in docker-compose.yml)
CMD ["uv", "run", "python", "-m", "src.api"]
