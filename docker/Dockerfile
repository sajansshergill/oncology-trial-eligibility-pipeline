FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

ENV DUCKDB_PATH=/app/oncology.duckdb \
    DBT_PROFILES_DIR=/app/dbt \
    PREFECT_API_URL=http://prefect-server:4200/api

CMD ["bash"]
