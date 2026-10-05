FROM python:3.13.8-alpine3.22

VOLUME ["/var/lib/lenzr"]
WORKDIR /app/

ARG APP_USER_UID=1000
ARG APP_USER_GID=1000

EXPOSE 8000
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONPATH=/app
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"
# Embedding model cache: a mounted volume, never baked into the image.
ENV HF_HOME=/opt/model-cache

RUN apk add --no-cache \
    git \
    jpeg-dev \
    zlib-dev

RUN addgroup -g ${APP_USER_GID} -S appgroup && adduser -u ${APP_USER_UID} -S appuser -G appgroup

RUN chown appuser:appgroup /app/

# A fresh named volume inherits this ownership, so appuser can fill the cache.
RUN mkdir -p /opt/model-cache && chown appuser:appgroup /opt/model-cache

# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /bin/

COPY ./pyproject.toml ./uv.lock ./
USER appuser

# Fix as mounting .git has a dubios ownership
RUN git config --global --add safe.directory /app

# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=${APP_USER_UID},gid=${APP_USER_GID} \
    --mount=type=bind,source=.git,target=/app/.git \
    uv sync --frozen --no-dev --no-install-project

COPY ./README.md ./alembic.ini ./
COPY ./alembic ./alembic
COPY ./src ./src

RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=${APP_USER_UID},gid=${APP_USER_GID} \
    --mount=type=bind,source=.git,target=/app/.git \
    uv sync --frozen --no-dev

# start-period covers the first-start model download. BusyBox wget avoids a
# CPython start per probe; 127.0.0.1 because BusyBox resolves localhost to ::1
# while uvicorn binds IPv4 only.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["wget", "-q", "-T", "4", "-O", "/dev/null", "http://127.0.0.1:8000/health"]

CMD ["uvicorn", "lenzr_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
