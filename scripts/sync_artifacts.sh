#!/usr/bin/env bash
# Sync the gitignored outputs/ artifact tree through the orphan 'artifacts' branch,
# so experiment artifacts move between machines without zip files.
#
#   scripts/sync_artifacts.sh pull              # fetch teammates' artifacts into outputs/
#   scripts/sync_artifacts.sh push "message"    # publish your outputs/ (ALWAYS pull first)
#
# Rules:
# - pull uses rsync --update: a file is only overwritten if the branch copy is NEWER
#   than yours, so an in-progress local run is never clobbered by a stale upload.
# - push snapshots your entire outputs/ tree. Pull before push; if the push is
#   rejected (non-fast-forward), pull and push again.
# - One cell = one owner at a time (per JAZZ_INSTRUCTIONS track ownership); the
#   branch is a transport, not a merge tool.
set -euo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel)
WT="$REPO_ROOT/.artifacts-worktree"
BRANCH=artifacts
cd "$REPO_ROOT"

git fetch origin "$BRANCH"

if [ ! -d "$WT" ]; then
  git worktree add "$WT" -B "$BRANCH" "origin/$BRANCH"
fi

case "${1:-}" in
  pull)
    git -C "$WT" fetch origin "$BRANCH"
    git -C "$WT" reset --hard "origin/$BRANCH"
    mkdir -p outputs
    rsync -a --update --exclude .DS_Store "$WT/outputs/" outputs/
    echo "[sync_artifacts] pulled; files newer locally were kept."
    ;;
  push)
    git -C "$WT" fetch origin "$BRANCH"
    git -C "$WT" reset --hard "origin/$BRANCH"
    rsync -a --exclude .DS_Store outputs/ "$WT/outputs/"
    git -C "$WT" add -A
    if git -C "$WT" diff --cached --quiet; then
      echo "[sync_artifacts] nothing new to push."
      exit 0
    fi
    git -C "$WT" commit -m "${2:-artifact sync $(date +%F)} [$(hostname -s), $(git config user.name)]"
    git -C "$WT" push origin "$BRANCH"
    echo "[sync_artifacts] pushed."
    ;;
  *)
    echo "usage: $0 pull | push [message]" >&2
    exit 1
    ;;
esac
