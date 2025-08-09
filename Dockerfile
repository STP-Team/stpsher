FROM python:3.13-slim

WORKDIR /usr/src/app/stpsher-bot

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files first for better caching
COPY pyproject.toml uv.lock* /usr/src/app/stpsher-bot/

# Install Python dependencies with uv (this will create .venv)
RUN uv sync --frozen

# Copy application code
COPY . /usr/src/app/stpsher-bot

# Set the PATH to include the virtual environment
ENV PATH="/usr/src/app/stpsher-bot/.venv/bin:$PATH"