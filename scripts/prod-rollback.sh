#!/usr/bin/env bash

set -euo pipefail

# Rollback to the pre-deploy state recorded by prod-update.sh.
# The state file is parsed, never sourced, and left untouched,
# so repeated rollbacks are idempotent.

STATE_FILE=".deploy-state"

if [ ! -f "$STATE_FILE" ]; then
    echo "ERROR: no deploy state found at $STATE_FILE. Deploy by tag explicitly instead." >&2
    exit 1
fi

PREV_TAG="$(grep -oP '^PREV_TAG="?\K[^"]+' "$STATE_FILE" || true)"

if [ -z "$PREV_TAG" ]; then
    echo "ERROR: deploy state has no previous tag. Deploy by tag explicitly instead." >&2
    exit 1
fi

echo "=== Rollback to pre-deploy tag: $PREV_TAG ==="
# Pass the tag as the git ref too, so no branch pull can block the rollback.
ROLLBACK=1 ./scripts/prod-update.sh "$PREV_TAG" "$PREV_TAG"
