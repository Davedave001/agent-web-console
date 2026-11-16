FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir fastapi uvicorn pydantic

COPY server.py index.html /app/

EXPOSE 8500

CMD ["python", "server.py"]
