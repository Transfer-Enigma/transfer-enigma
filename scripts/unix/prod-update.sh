#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR" || exit 1

GIT_REF="${1:-master}"
DOCKER_TAG="${2:-}"
GIT_TAG="${3:-}"
TAG_MESSAGE="${4:-}"

if [ -z "$GIT_TAG" ]; then
    GIT_TAG="$DOCKER_TAG"
fi

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

if [ "$GIT_TAG" ]; then
    if [ -n "$TAG_MESSAGE" ]; then
        echo "=== Creating and pushing git tag '$GIT_TAG' with message '$TAG_MESSAGE' from '$GIT_REF' ==="
        git tag -a "$GIT_TAG" -m "$TAG_MESSAGE"
    else
        echo "=== Creating and pushing git tag '$GIT_TAG' from '$GIT_REF' ==="
        git tag "$GIT_TAG"
    fi

    git push origin "$GIT_TAG"
fi

export DOCKER_PROD_IMAGES_TAG="$DOCKER_TAG"

mkdir -p logs
docker compose down
docker compose pull
docker compose -f docker-compose.migrate.yml pull
"$SCRIPT_DIR/prod-db-migrate.sh" upgrade head
docker compose up -d
