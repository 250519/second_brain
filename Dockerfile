FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock* ./

# Install dependencies (no dev deps, frozen lockfile)
RUN uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/

# Pre-create wiki directories so the app starts cleanly
RUN mkdir -p \
    data/wiki/summary data/wiki/concept data/wiki/connection \
    data/wiki/insight data/wiki/qa data/wiki/lint \
    data/output data/infranodus data/todos data/raw

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "second_brain.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
