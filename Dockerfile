FROM python:3.14-slim

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY src ./src
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
