# Cloud Run image for the Intake agent service.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# The templates are the product's configuration, not sample data — the image is
# useless without them (ADR-0003).
COPY intake_agent ./intake_agent
COPY templates ./templates
ENV INTAKE_TEMPLATE_DIR=/app/templates

# Cloud Run sets $PORT; honour it rather than hard-coding 8080.
CMD exec uvicorn intake_agent.main:app --host 0.0.0.0 --port ${PORT}
