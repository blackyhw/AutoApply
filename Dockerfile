FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUTOAPPLY_HOME=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin agent

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY config /app/config

RUN pip install --no-cache-dir . \
    && mkdir -p /app/data /app/secrets \
    && chown -R agent:agent /app

USER agent

VOLUME ["/app/data", "/app/secrets", "/app/config"]

CMD ["python", "-m", "autoapply", "run"]
