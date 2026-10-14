#!/usr/bin/env bash

set -euo pipefail

GIT_REF="${1:-master}"
DOCKER_TAG="${2:-}"

if [ -z "$DOCKER_TAG" ]; then
    if [ -f .env ]; then
        DOCKER_TAG=$(grep -oP '^DOCKER_PROD_IMAGES_TAG="?\K[^"]+' .env || echo "latest")
    else
        DOCKER_TAG="latest"
    fi
else
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
fi

# Tags are created in CI, never on the server.
# When DOCKER_TAG looks like a versioned tag (not latest/latest-stable),
# verify it exists and check it out so the server runs the tagged code.
if [ -n "$DOCKER_TAG" ] && [ "$DOCKER_TAG" != "latest" ] && [ "$DOCKER_TAG" != "latest-stable" ]; then
    if printf '%s' "$DOCKER_TAG" | grep -Eq '^[A-Za-z0-9._-]+$'; then
        if git rev-parse --verify --quiet "refs/tags/$DOCKER_TAG" >/dev/null; then
            echo "=== Switching to existing tag: $DOCKER_TAG ==="
            git checkout "$DOCKER_TAG"
        else
            echo "ERROR: tag '$DOCKER_TAG' not found. Tags are created in CI before the build; refusing to create tags on the server." >&2
            exit 1
        fi
    fi
fi

export DOCKER_PROD_IMAGES_TAG="$DOCKER_TAG"

mkdir -p logs
docker compose down
docker compose pull
docker compose -f docker-compose.migrate.yml pull
./scripts/prod-db-migrate.sh upgrade head
docker compose up -d
