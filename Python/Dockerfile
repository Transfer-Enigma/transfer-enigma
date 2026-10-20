FROM ghcr.io/astral-sh/uv:0.13.3 AS uv

FROM python:3.15-slim AS python-base

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

WORKDIR "${APP_DIR}"

USER ${USER_UID}


FROM python-base AS builder

USER root

COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=/usr/local/bin/python

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM builder AS builder-tests

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group tests


FROM python-base AS python-apps

ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/workspace"

COPY --from=builder --chown=${USER_UID}:${USER_GID} ${APP_DIR}/.venv ${APP_DIR}/.venv
ENV PATH="${APP_DIR}/.venv/bin:$PATH"

COPY ./apps/ ./
ENTRYPOINT ["python3", "-m", "uvicorn"]


FROM python-base AS db-migration

ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/workspace"

COPY --from=builder --chown=${USER_UID}:${USER_GID} ${APP_DIR}/.venv ${APP_DIR}/.venv
ENV PATH="${APP_DIR}/.venv/bin:$PATH"

COPY ./alembic.ini ./alembic.ini
COPY ./alembic/ ./alembic/
COPY ./apps/ ./apps/

ENTRYPOINT ["python3", "-m", "alembic"]


FROM python-base AS test-runner

ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/workspace"

COPY --from=builder-tests --chown=${USER_UID}:${USER_GID} ${APP_DIR}/.venv ${APP_DIR}/.venv
ENV PATH="${APP_DIR}/.venv/bin:$PATH"

COPY ./apps/ ./apps/
COPY ./tests/ ./tests/

ENTRYPOINT ["python3", "-m", "pytest"]
# ENV does not work properly in JSON mode
CMD ["/workspace/tests", "-v", "--tb=short", "--override-ini=pythonpath=/workspace/apps", "--override-ini=asyncio_mode=auto", "--rootdir=/workspace"]
