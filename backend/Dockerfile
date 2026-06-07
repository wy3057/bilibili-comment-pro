FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential git && rm -rf /var/lib/apt/lists/*

COPY vendor/bilibili-api /app/vendor/bilibili-api
RUN pip install --upgrade pip && pip install /app/vendor/bilibili-api

COPY backend /app/backend

WORKDIR /app/backend

RUN pip install .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
