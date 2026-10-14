FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Presidio's default NLP engine requires the spaCy en_core_web_lg model.
# It is not a pip dependency, so download it explicitly or AnalyzerEngine()
# crashes at import time (anonymization/anonymizer.py instantiates it eagerly).
RUN python -m spacy download en_core_web_lg

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
