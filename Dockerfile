FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir fastapi uvicorn pydantic

COPY web-console/server.py /app/server.py
COPY web-console/index.html /app/index.html

EXPOSE 8500

CMD ["python", "server.py"]
