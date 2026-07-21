#!/usr/bin/env bash
set -euo pipefail

EXPECTED_CSP="default-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self'; script-src 'self'; connect-src 'none'"
ENV_DOMAIN=${DOMAIN:-}
DOMAIN=""
PIN_IP=""

usage() {
    printf 'usage: DOMAIN=example.com %s [domain] [--ip real_ip]\n' "$0" >&2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --ip)
            if [ "$#" -lt 2 ]; then
                usage
                exit 1
            fi
            PIN_IP="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            usage
            exit 1
            ;;
        *)
            if [ -n "$DOMAIN" ]; then
                usage
                exit 1
            fi
            DOMAIN="$1"
            shift
            ;;
    esac
done

DOMAIN=${DOMAIN:-$ENV_DOMAIN}

if [ -z "$DOMAIN" ]; then
    usage
    exit 1
fi

ROOT_URL="https://${DOMAIN}"
CURL_ARGS=(--silent --show-error --location)

if [ -n "$PIN_IP" ]; then
    CURL_ARGS+=(--resolve "${DOMAIN}:443:${PIN_IP}")
fi

WORK_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

fail() {
    printf 'smoke failed: %s\n' "$1" >&2
    exit 1
}

HTML_FILE="$WORK_DIR/index.html"
ROOT_HEADERS="$WORK_DIR/root.headers"
ROOT_STATUS=$(curl "${CURL_ARGS[@]}" --output "$HTML_FILE" --dump-header "$ROOT_HEADERS" --write-out '%{http_code}' "$ROOT_URL/")

if [ "$ROOT_STATUS" != '200' ]; then
    fail "expected GET ${ROOT_URL}/ to return 200, got ${ROOT_STATUS}"
fi

if ! grep -q 'ОБЗОР' "$HTML_FILE"; then
    fail "expected ${ROOT_URL}/ body to contain ОБЗОР"
fi

ASSET_PATH=$(grep -oE '/assets/index-[^" ]+\.js' "$HTML_FILE" | head -n 1 || true)
if [ -z "$ASSET_PATH" ]; then
    ASSET_PATH=$(grep -oE '/assets/[^" ]+\.js' "$HTML_FILE" | head -n 1 || true)
fi
if [ -z "$ASSET_PATH" ]; then
    fail 'could not find a hashed JS bundle path in the HTML shell'
fi

ASSET_HEADERS="$WORK_DIR/asset.headers"
ASSET_STATUS=$(curl "${CURL_ARGS[@]}" --head --output /dev/null --dump-header "$ASSET_HEADERS" --write-out '%{http_code}' "$ROOT_URL$ASSET_PATH")
if [ "$ASSET_STATUS" != '200' ]; then
    fail "expected HEAD ${ROOT_URL}${ASSET_PATH} to return 200, got ${ASSET_STATUS}"
fi
if ! grep -iq '^cache-control: .*immutable' "$ASSET_HEADERS"; then
    fail "expected ${ASSET_PATH} to be served with an immutable cache-control header"
fi

ROBOTS_FILE="$WORK_DIR/robots.txt"
ROBOTS_STATUS=$(curl "${CURL_ARGS[@]}" --output "$ROBOTS_FILE" --write-out '%{http_code}' "$ROOT_URL/robots.txt")
if [ "$ROBOTS_STATUS" != '200' ]; then
    fail "expected GET ${ROOT_URL}/robots.txt to return 200, got ${ROBOTS_STATUS}"
fi
if ! grep -iq '^user-agent:[[:space:]]*\*$' "$ROBOTS_FILE"; then
    fail 'robots.txt is missing User-agent: *'
fi
if ! grep -iq '^disallow:[[:space:]]*/$' "$ROBOTS_FILE"; then
    fail 'robots.txt is missing Disallow: /'
fi

CSP_VALUE=$(awk 'BEGIN { IGNORECASE = 1 } /^content-security-policy:/ { sub(/\r$/, ""); sub(/^[^:]+:[[:space:]]*/, ""); print; exit }' "$ROOT_HEADERS")
if [ "$CSP_VALUE" != "$EXPECTED_CSP" ]; then
    fail "expected CSP ${EXPECTED_CSP}, got ${CSP_VALUE:-<missing>}"
fi

printf 'Smoke passed for %s\n' "$DOMAIN"
printf 'Verified root marker, asset cache header, robots.txt, and CSP.\n'
