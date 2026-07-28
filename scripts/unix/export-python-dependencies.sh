#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR" || exit 1

poetry export --without-hashes -o ./Python/requirements.txt
poetry export --without-hashes --with=dev -o ./Python/requirements-dev.txt
poetry export --without-hashes --with=tests -o ./Python/requirements-tests.txt
