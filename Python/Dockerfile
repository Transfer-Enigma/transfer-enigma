FROM ghcr.io/astral-sh/uv:latest AS uv

FROM python:3.14-slim AS python-base

ARG USERNAME="appuser"
ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/workspace"

RUN mkdir -p /home/${USERNAME} && \
    groupadd -r -g ${USER_GID} ${USERNAME} && \
    useradd -r -d /home/${USERNAME} -u ${USER_UID} -g ${USER_GID} ${USERNAME} && \
    chown ${USERNAME}:${USERNAME} /home/${USERNAME} && \
    mkdir ${APP_DIR} && \
    chmod 750 ${APP_DIR} && \
    chown ${USERNAME}:${USERNAME} ${APP_DIR}

RUN mkdir /var/log/app
RUN chown ${USERNAME}:${USERNAME} /var/log/app

COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=/usr/local/bin/python

WORKDIR "${APP_DIR}"

USER ${USER_UID}


# Builds one wheel per workspace package and installs only the
# backend (+ its workspace dependencies) needed for the image.
# Application code comes from the installed wheels, not COPY.
FROM python-base AS builder-base

ARG APP_DIR="/workspace"

USER root

COPY pyproject.toml uv.lock ./
COPY apps/backend_auth/pyproject.toml apps/backend_auth/
COPY apps/backend_user/pyproject.toml apps/backend_user/
COPY apps/backend_admin/pyproject.toml apps/backend_admin/
COPY apps/module_shared/pyproject.toml apps/module_shared/
COPY apps/module_data_internal/pyproject.toml apps/module_data_internal/
COPY apps/module_data_fesco_api_adapter/pyproject.toml apps/module_data_fesco_api_adapter/


# Two-step sync per image: third-party deps first (cacheable layer without
# source), then workspace sources are copied and wheels are built+installed.
FROM builder-base AS builder-auth

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend-auth --no-install-workspace
COPY apps/ apps/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend-auth --no-editable


FROM builder-base AS builder-user

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend-user --no-install-workspace
COPY apps/ apps/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend-user --no-editable


FROM builder-base AS builder-admin

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend-admin --no-install-workspace
COPY apps/ apps/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package backend-admin --no-editable


FROM builder-base AS builder-tests

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group tests --package backend-user --no-install-workspace
COPY apps/ apps/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group tests --package backend-user --no-editable


FROM python-base AS python-apps

ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/workspace"

COPY --from=builder-user --chown=${USER_UID}:${USER_GID} ${APP_DIR}/.venv ${APP_DIR}/.venv
ENV PATH="${APP_DIR}/.venv/bin:$PATH"

ENTRYPOINT ["python3", "-m", "uvicorn"]


FROM python-base AS db-migration

ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/workspace"

COPY --from=builder-admin --chown=${USER_UID}:${USER_GID} ${APP_DIR}/.venv ${APP_DIR}/.venv
ENV PATH="${APP_DIR}/.venv/bin:$PATH"

COPY ./alembic.ini ./alembic.ini
COPY ./alembic/ ./alembic/

ENTRYPOINT ["python3", "-m", "alembic"]


FROM python-base AS test-runner

ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/workspace"

COPY --from=builder-tests --chown=${USER_UID}:${USER_GID} ${APP_DIR}/.venv ${APP_DIR}/.venv
ENV PATH="${APP_DIR}/.venv/bin:$PATH"

COPY ./tests/ ./tests/

ENTRYPOINT ["python3", "-m", "pytest"]
# ENV does not work properly in JSON mode
CMD ["/workspace/tests", "-v", "--tb=short", "--override-ini=asyncio_mode=auto", "--rootdir=/workspace"]
