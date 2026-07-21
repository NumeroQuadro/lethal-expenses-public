#!/usr/bin/env bash
set -euo pipefail

require_env() {
    local name="$1"

    if [ -z "${!name:-}" ]; then
        printf 'error: %s\n' "$name" >&2
        exit 1
    fi
}

require_env DOMAIN
require_env VPS

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
WEB_ROOT=${WEB_ROOT:-/var/www/lethal-expenses}
SSH_TARGET="root@${VPS}"
CURRENT_SHA=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || true)
ARTIFACT=""

if [ -n "$CURRENT_SHA" ] && [ -f "dist/lethal-expenses-${CURRENT_SHA}.tar.gz" ]; then
    ARTIFACT="dist/lethal-expenses-${CURRENT_SHA}.tar.gz"
else
    ARTIFACT=$(ls -t dist/lethal-expenses-*.tar.gz 2>/dev/null | head -n 1 || true)
fi

if [ -z "$ARTIFACT" ]; then
    printf 'error: no dist/lethal-expenses-*.tar.gz artifact found. Run make dist first.\n' >&2
    exit 1
fi

WORK_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

tar -xzf "$ARTIFACT" -C "$WORK_DIR"

ssh "$SSH_TARGET" install -d -o www-data -g www-data -m 0755 "$WEB_ROOT"
rsync -az --delete "$WORK_DIR/" "$SSH_TARGET:$WEB_ROOT/"
ssh "$SSH_TARGET" "chown -R www-data:www-data '$WEB_ROOT' && nginx -t && systemctl reload nginx"

DOMAIN="$DOMAIN" "$SCRIPT_DIR/smoke.sh" "$DOMAIN"
printf 'Deployment verification passed for %s\n' "$DOMAIN"
