FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/memoryd/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r /tmp/requirements.txt

COPY services /app/services
COPY specs /app/specs
COPY docs /app/docs
COPY adapters /app/adapters
COPY third_party /app/third_party
COPY artifacts /app/artifacts

EXPOSE 8787

CMD ["uvicorn", "services.memoryd.app.main:app", "--host", "0.0.0.0", "--port", "8787"]
