FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg colmap \
    && rm -rf /var/lib/apt/lists/*
COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api/app /app/app
COPY packages /app/packages
RUN pip install --no-cache-dir .
RUN python -c "import packages.camera_math; import packages.geometry; import app.main"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
