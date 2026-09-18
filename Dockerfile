FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUTOAPPLY_HOME=/app \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin agent

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY config /app/config

RUN pip install --no-cache-dir . \
    && playwright install-deps chromium \
    && mkdir -p /opt/ms-playwright /app/data /app/secrets \
    && playwright install chromium \
    && chmod -R 755 /opt/ms-playwright \
    && chown -R agent:agent /app

USER agent

VOLUME ["/app/data", "/app/secrets", "/app/config"]

CMD ["python", "-m", "autoapply", "run"]
