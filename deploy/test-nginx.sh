#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
    printf 'error: docker is required for nginx config validation\n' >&2
    exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
    printf 'error: openssl is required for fake certificate generation\n' >&2
    exit 1
fi

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
WORK_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$WORK_DIR/fake-certs"
openssl req \
    -x509 \
    -nodes \
    -newkey rsa:2048 \
    -keyout "$WORK_DIR/fake-certs/privkey.pem" \
    -out "$WORK_DIR/fake-certs/fullchain.pem" \
    -days 1 \
    -subj '/CN=example.test' >/dev/null 2>&1

sed \
    -e 's|{{DOMAIN}}|example.test|g' \
    -e 's|{{WEB_ROOT}}|/usr/share/nginx/html|g' \
    -e 's|/etc/letsencrypt/live/example.test/fullchain.pem|/etc/nginx/conf.d/fake-certs/fullchain.pem|g' \
    -e 's|/etc/letsencrypt/live/example.test/privkey.pem|/etc/nginx/conf.d/fake-certs/privkey.pem|g' \
    "$SCRIPT_DIR/nginx.conf" >"$WORK_DIR/lethal-expenses.conf"

docker run --rm -v "$WORK_DIR:/etc/nginx/conf.d" nginx:alpine nginx -t
