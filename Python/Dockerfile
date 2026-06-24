FROM python:3.14-slim AS python-apps

ARG USERNAME="appuser"
ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/apps"

RUN mkdir -p /home/${USERNAME} && \
    groupadd -r -g ${USER_GID} ${USERNAME} && \
    useradd -r -d /home/${USERNAME} -u ${USER_UID} -g ${USER_GID} ${USERNAME} && \
    chown ${USERNAME}:${USERNAME} /home/${USERNAME} && \
    mkdir ${APP_DIR} && \
    chmod 750 ${APP_DIR} && \
    chown ${USERNAME}:${USERNAME} ${APP_DIR}

RUN mkdir /var/log/app
RUN chown ${USERNAME}:${USERNAME} /var/log/app

USER ${USER_UID}

# install requirements
COPY ./requirements.txt ./
RUN ["python3", "-m", "pip", "install", "--no-deps", "--no-cache-dir", "-r", "requirements.txt"]

WORKDIR "${APP_DIR}"
# run
COPY ./apps/ ./
ENTRYPOINT ["python3", "-m", "uvicorn"]

FROM python:3.14-slim AS db-migration

ARG USERNAME="appuser"
ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/app"

RUN mkdir -p /home/${USERNAME} && \
    groupadd -r -g ${USER_GID} ${USERNAME} && \
    useradd -r -d /home/${USERNAME} -u ${USER_UID} -g ${USER_GID} ${USERNAME} && \
    chown ${USERNAME}:${USERNAME} /home/${USERNAME} && \
    mkdir ${APP_DIR} && \
    chmod 750 ${APP_DIR} && \
    chown ${USERNAME}:${USERNAME} ${APP_DIR}

USER ${USER_UID}

# install requirements
COPY ./requirements.txt ./
RUN ["python3", "-m", "pip", "install", "--no-deps", "--no-cache-dir", "-r", "requirements.txt"]

WORKDIR "${APP_DIR}"
# run
COPY ./alembic.ini ./alembic.ini
COPY ./alembic/ ./alembic/
COPY ./apps/ ./apps/

ENTRYPOINT ["python3", "-m", "alembic"]

FROM python:3.14-slim AS test-runner

ARG USERNAME="appuser"
ARG USER_UID=1000
ARG USER_GID=1000
ARG APP_DIR="/app"

RUN mkdir -p /home/${USERNAME} && \
    groupadd -r -g ${USER_GID} ${USERNAME} && \
    useradd -r -d /home/${USERNAME} -u ${USER_UID} -g ${USER_GID} ${USERNAME} && \
    chown ${USERNAME}:${USERNAME} /home/${USERNAME} && \
    mkdir ${APP_DIR} && \
    chmod 750 ${APP_DIR} && \
    chown ${USERNAME}:${USERNAME} ${APP_DIR}

USER ${USER_UID}

COPY ./requirements-tests.txt ./
RUN ["python3", "-m", "pip", "install", "--no-cache-dir", "-r", "requirements-tests.txt"]

WORKDIR "${APP_DIR}"
COPY ./apps/ ./apps/
COPY ./tests/ ./tests/

ENTRYPOINT ["python3", "-m", "pytest"]
CMD ["/app/tests/", "-v", "--tb=short", "--override-ini=pythonpath=/app/apps", "--override-ini=asyncio_mode=auto", "--rootdir=/app"]
