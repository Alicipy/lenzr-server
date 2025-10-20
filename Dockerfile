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

RUN apk add --no-cache \
    git

RUN addgroup -g ${APP_USER_GID} -S appgroup && adduser -u ${APP_USER_UID} -S appuser -G appgroup

RUN chown appuser:appgroup /app/

# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /bin/

COPY ./pyproject.toml ./uv.lock ./
USER appuser

# Fix as mounting .git has a dubios ownership
RUN git config --global --add safe.directory /app

# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/appuser/.cache/uv \
    --mount=type=bind,source=.git,target=/app/.git \
    uv sync --frozen --no-install-project

COPY ./README.md ./
COPY ./src ./src

RUN --mount=type=cache,target=/appuser/.cache/uv \
    --mount=type=bind,source=.git,target=/app/.git \
    uv sync --frozen

CMD ["uvicorn", "lenzr_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
