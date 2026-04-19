FROM python:3.11

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/
COPY data/ data/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
