#!/usr/bin/env bash
set -euo pipefail

LOG_FILE=${LOG_FILE:-/var/log/lethal-expenses-renew.log}

stamp() {
    date --iso-8601=seconds
}

{
    printf '[%s] certbot renew start\n' "$(stamp)"
    certbot renew --quiet
    printf '[%s] certbot renew finish\n' "$(stamp)"
} >>"$LOG_FILE" 2>&1
