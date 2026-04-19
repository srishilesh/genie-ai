FROM python:3.11

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
