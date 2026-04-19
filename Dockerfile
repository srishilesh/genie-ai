FROM python:3.11

RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY src/ src/
COPY data/ data/
COPY alembic/ alembic/

RUN pip install --no-cache-dir .

EXPOSE 8000

COPY scripts/start.sh .
RUN chmod +x start.sh

CMD ["bash", "start.sh"]
