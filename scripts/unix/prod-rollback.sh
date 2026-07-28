#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR" || exit 1

CURRENT_TAG="${1:?Usage: prod-rollback.sh <current_tag> <target_tag> [target_revision]}"
TARGET_TAG="${2:?Usage: prod-rollback.sh <current_tag> <target_tag> [target_revision]}"
TARGET_REVISION="${3:-}"

echo "=== Rollback: $CURRENT_TAG -> $TARGET_TAG ==="

if [ -n "$TARGET_REVISION" ]; then
    echo "=== Step 1: Downgrading migrations to $TARGET_REVISION (using current image $CURRENT_TAG) ==="
    DOCKER_PROD_IMAGES_TAG="$CURRENT_TAG" ./scripts/unix/prod-db-migrate.sh downgrade "$TARGET_REVISION"
else
    echo "=== Step 1: No migration downgrade needed ==="
fi

echo "=== Step 2: Switching to tag: $TARGET_TAG ==="
git fetch -p --tags
git checkout --detach "$TARGET_TAG"

echo "=== Step 3: Updating .env DOCKER_PROD_IMAGES_TAG to $TARGET_TAG ==="
if [ -f .env ]; then
    if grep -q '^DOCKER_PROD_IMAGES_TAG=' .env; then
        sed -i 's/^DOCKER_PROD_IMAGES_TAG=.*/DOCKER_PROD_IMAGES_TAG="'"$TARGET_TAG"'"/' .env
    else
        echo 'DOCKER_PROD_IMAGES_TAG="'"$TARGET_TAG"'"' >> .env
    fi
else
    echo 'DOCKER_PROD_IMAGES_TAG="'"$TARGET_TAG"'"' > .env
fi

export DOCKER_PROD_IMAGES_TAG="$TARGET_TAG"
mkdir -p logs

echo "=== Step 4: Pulling new images (Background) ==="
docker compose pull

echo "=== Step 5: Restarting services ==="
docker compose down
docker compose up -d

echo "=== Rollback complete ==="
