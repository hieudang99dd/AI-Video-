FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg colmap && rm -rf /var/lib/apt/lists/*
COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api/app /app/app
RUN pip install --no-cache-dir .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
