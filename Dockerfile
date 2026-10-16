FROM ghcr.io/astral-sh/uv:0.8.22 AS uv
FROM python:3.12.11-slim

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY queries ./queries
COPY web ./web
COPY data/snapshot ./data/snapshot
RUN uv sync --frozen --no-dev --no-install-project && uv sync --frozen --no-dev
RUN useradd --create-home --uid 10001 busfactor && chown -R busfactor:busfactor /app
USER busfactor
EXPOSE 8000
CMD ["uv", "run", "--frozen", "python", "-m", "busfactor.bootstrap"]
