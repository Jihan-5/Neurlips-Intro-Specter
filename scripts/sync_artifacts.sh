#!/usr/bin/env bash
# Preserve all worktrees and existing local outputs. For publishing completed
# cells, pass --include outputs/path (repeatable). Live bootstrap files protected.
set -euo pipefail
exec python3 "$(dirname "$0")/sync_artifacts_safe.py" "$@"
