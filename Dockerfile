FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency files first — layer is cached unless deps change
COPY pyproject.toml README.md alembic.ini ./

# Install deps with retries and higher timeout to survive flaky PyPI
RUN pip install --no-cache-dir --timeout 120 --retries 5 \
    fastapi uvicorn[standard] python-dotenv pydantic pydantic-settings \
    langgraph langchain-openai langchain-anthropic \
    chromadb \
    sqlalchemy[asyncio] asyncpg psycopg2-binary alembic \
    openai anthropic \
    pypdf beautifulsoup4 lxml \
    langsmith \
    httpx tenacity \
    streamlit \
    hatchling

# Now install the app package itself (fast, no network deps)
COPY src/ src/
COPY data/ data/
COPY alembic/ alembic/

RUN pip install --no-cache-dir --no-deps .

EXPOSE 8000

COPY scripts/start.sh .
RUN chmod +x start.sh

CMD ["bash", "start.sh"]
