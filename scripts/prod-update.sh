#!/usr/bin/env bash

set -euo pipefail

GIT_REF="${1:-master}"
DOCKER_TAG="${2:-}"
REQUESTED_TAG="$DOCKER_TAG"
ROLLBACK="${ROLLBACK:-0}"
STATE_FILE=".deploy-state"

PREV_TAG=""
if [ -f .env ]; then
    PREV_TAG=$(grep -oP '^DOCKER_PROD_IMAGES_TAG="?\K[^"]+' .env || echo "")
fi

if [ -z "$DOCKER_TAG" ]; then
    if [ -f .env ]; then
        DOCKER_TAG=$(grep -oP '^DOCKER_PROD_IMAGES_TAG="?\K[^"]+' .env || echo "latest")
    else
        DOCKER_TAG="latest"
    fi
fi

# "latest" and "latest-stable" match this class too, so one check covers all.
if ! printf '%s' "$DOCKER_TAG" | grep -Eq '^[A-Za-z0-9._-]+$'; then
    echo "ERROR: invalid docker tag '$DOCKER_TAG'. Must match ^[A-Za-z0-9._-]+$" >&2
    exit 1
fi

echo "=== Git ref: $GIT_REF ==="
echo "=== Docker tag: $DOCKER_TAG ==="

git fetch -p --tags

if git show-ref --verify --quiet "refs/tags/$GIT_REF"; then
    echo "=== Switching to tag: $GIT_REF ==="
    git checkout "$GIT_REF"
elif git show-ref --verify --quiet "refs/heads/$GIT_REF"; then
    echo "=== Switching to branch: $GIT_REF ==="
    git checkout "$GIT_REF"
    git pull origin "$GIT_REF"
else
    echo "ERROR: unknown git ref '$GIT_REF' (no such tag or branch)." >&2
    exit 1
fi

# Tags are created in CI, never on the server.
# When DOCKER_TAG looks like a versioned tag (not latest/latest-stable),
# verify it exists and check it out so the server runs the tagged code.
if [ "$DOCKER_TAG" != "latest" ] && [ "$DOCKER_TAG" != "latest-stable" ]; then
    if git rev-parse --verify --quiet "refs/tags/$DOCKER_TAG" >/dev/null; then
        echo "=== Switching to existing tag: $DOCKER_TAG ==="
        git checkout "$DOCKER_TAG"
    else
        echo "ERROR: tag '$DOCKER_TAG' not found. Tags are created in CI before the build; refusing to create tags on the server." >&2
        exit 1
    fi
fi

export DOCKER_PROD_IMAGES_TAG="$DOCKER_TAG"

mkdir -p logs

echo "=== Pulling images ==="
docker compose pull
docker compose -f docker-compose.migrate.yml pull

MIGRATION_IMAGE="danielgreen1806/calculator-db-migration:${DOCKER_TAG}"
echo "=== Resolving migration head for $DOCKER_TAG ==="
HEADS="$(docker run --rm "$MIGRATION_IMAGE" heads)"
HEAD_COUNT="$(printf '%s\n' "$HEADS" | grep -c . || true)"
if [ "$HEAD_COUNT" -ne 1 ]; then
    echo "ERROR: expected exactly one alembic head for $DOCKER_TAG, got $HEAD_COUNT: $HEADS" >&2
    exit 1
fi
TARGET_REV="$(printf '%s\n' "$HEADS" | head -n 1 | awk '{print $1}')"
echo "=== Migration target revision: $TARGET_REV ==="

if [ -n "$REQUESTED_TAG" ]; then
    echo "=== Updating .env DOCKER_PROD_IMAGES_TAG to $DOCKER_TAG ==="
    if [ -f .env ]; then
        if grep -qP '^DOCKER_PROD_IMAGES_TAG=' .env; then
            sed -i 's/^DOCKER_PROD_IMAGES_TAG=.*/DOCKER_PROD_IMAGES_TAG="'"$DOCKER_TAG"'"/' .env
        else
            echo 'DOCKER_PROD_IMAGES_TAG="'"$DOCKER_TAG"'"' >> .env
        fi
    else
        echo 'DOCKER_PROD_IMAGES_TAG="'"$DOCKER_TAG"'"' > .env
    fi
fi

# Record the pre-deploy state so a rollback knows where to return.
# Rollbacks must not rewrite it, otherwise a repeated rollback would ping-pong.
if [ "$ROLLBACK" != "1" ] && [ -n "$REQUESTED_TAG" ]; then
    if [ -z "$PREV_TAG" ]; then
        echo "WARNING: no previous tag recorded — rollback will not be possible until the next tagged deploy." >&2
    fi
    echo "=== Recording pre-deploy state (previous tag: $PREV_TAG) ==="
    echo "PREV_TAG=\"$PREV_TAG\"" > "$STATE_FILE"
elif [ "$ROLLBACK" != "1" ]; then
    echo "WARNING: tag-less deploy — pre-deploy state is not recorded and rollback will not be possible." >&2
fi

# Best effort: if anything fails after the services are stopped, try to start
# them again instead of leaving production fully down. The pipes' auto-rollback
# (or a manual call-rollback) then restores the correct version.
STOPPED=0
on_error() {
    trap - ERR
    if [ "$STOPPED" = "1" ]; then
        echo "ERROR: deploy failed after stopping services, attempting to start containers..." >&2
        docker compose up -d || true
    fi
}
trap on_error ERR

docker compose down
STOPPED=1

read_current_rev() {
    ./scripts/prod-db-migrate.sh current 2>logs/migrate-current.log | awk 'NF {print $1; exit}'
}

./scripts/prod-db-migrate.sh upgrade "$TARGET_REV" || ./scripts/prod-db-migrate.sh downgrade "$TARGET_REV"
# NOTE: `alembic upgrade` to a lower revision exits 0 without doing anything,
# so a mismatch below means the upgrade silently no-oped and we must go down.
if ! CURRENT_REV="$(read_current_rev)"; then
    echo "ERROR: cannot read the current database revision, aborting. See logs/migrate-current.log." >&2
    exit 1
fi
if [ "$CURRENT_REV" != "$TARGET_REV" ]; then
    echo "Database is at $CURRENT_REV, expected $TARGET_REV — downgrading..." >&2
    ./scripts/prod-db-migrate.sh downgrade "$TARGET_REV"
    if ! CURRENT_REV="$(read_current_rev)"; then
        echo "ERROR: cannot read the current database revision, aborting. See logs/migrate-current.log." >&2
        exit 1
    fi
fi
if [ "$CURRENT_REV" != "$TARGET_REV" ]; then
    echo "ERROR: database is at '$CURRENT_REV', expected '$TARGET_REV' after migration." >&2
    exit 1
fi
docker compose up -d
