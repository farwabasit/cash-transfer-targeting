# Ingestion image: lands raw survey files in Snowflake RAW.
# Data and the key are mounted at run time, never baked into the image.
FROM python:3.12-slim

WORKDIR /app
COPY requirements-ingest.txt .
RUN pip install --no-cache-dir -r requirements-ingest.txt

COPY ingestion/ ingestion/

ENTRYPOINT ["python", "ingestion/load_raw.py"]
