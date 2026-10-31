FROM python:3.12-slim AS build

ENV PATH=/opt/venv/bin:$PATH \
    VIRTUAL_ENV=/opt/venv \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential ca-certificates cmake \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /opt/venv

WORKDIR /app
ARG CATCHALL_ASSET_VERSION=manual
COPY . .
RUN cp catchall/static/styles.css \
        "catchall/static/styles.${CATCHALL_ASSET_VERSION}.css" \
    && for source_file in catchall/static/*.js; do \
        cp "$source_file" "${source_file%.js}.${CATCHALL_ASSET_VERSION}.js"; \
    done \
    && sed -i \
        -e "s|href=\"/static/styles.css\"|href=\"static/styles.${CATCHALL_ASSET_VERSION}.css\"|" \
        -e "s|src=\"/static/app.js\"|src=\"static/app.${CATCHALL_ASSET_VERSION}.js\"|" \
        -e 's|href="/static/|href="static/|g' \
        -e 's|src="/static/|src="static/|g' \
        catchall/static/index.html \
    && for versioned_file in catchall/static/*."${CATCHALL_ASSET_VERSION}".js; do \
        sed -i \
            -e 's|new URL("/ws", window.location.origin)|new URL("ws", window.location.href)|g' \
            -e 's|workletUrl = "/static/|workletUrl = "static/|g' \
            -e "s|\\.js\"|.${CATCHALL_ASSET_VERSION}.js\"|g" \
            "$versioned_file"; \
    done \
    && sed -i \
        's|new URL("/ws", window.location.origin)|new URL("ws", window.location.href)|g' \
        catchall/static/app.js \
    && sed -i \
        's|workletUrl = "/static/|workletUrl = "static/|g' \
        catchall/static/audio-capture.js \
    && pip install --no-cache-dir . \
    && python -c "from faster_whisper.utils import download_model; download_model('tiny.en', output_dir='/opt/models')"

FROM python:3.12-slim

ENV PATH=/opt/venv/bin:$PATH \
    VIRTUAL_ENV=/opt/venv \
    CATCHALL_WHISPER_MODEL=/opt/models \
    HF_HUB_OFFLINE=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --gid 10001 catchall \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin catchall

COPY --from=build /opt/venv /opt/venv
COPY --from=build /opt/models /opt/models

USER 10001:10001
WORKDIR /app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "catchall.app:app", "--host", "0.0.0.0", "--port", "8000"]
