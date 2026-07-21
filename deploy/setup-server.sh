#!/usr/bin/env bash
set -euo pipefail

require_env() {
    local name="$1"

    if [ -z "${!name:-}" ]; then
        printf 'error: %s must be set\n' "$name" >&2
        exit 1
    fi
}

render_bootstrap_conf() {
    cat >"$SITE_AVAILABLE" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    root $WEB_ROOT;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF
}

render_final_conf() {
    sed \
        -e "s|{{DOMAIN}}|$DOMAIN|g" \
        -e "s|{{WEB_ROOT}}|$WEB_ROOT|g" \
        "$SCRIPT_DIR/nginx.conf" >"$SITE_AVAILABLE"
}

if [ "$(id -u)" -ne 0 ]; then
    printf 'error: run this script as root (or via sudo)\n' >&2
    exit 1
fi

require_env DOMAIN
require_env EMAIL

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
WEB_ROOT=${WEB_ROOT:-/var/www/lethal-expenses}
SITE_NAME=${SITE_NAME:-lethal-expenses}
SITE_AVAILABLE="/etc/nginx/sites-available/${SITE_NAME}.conf"
SITE_ENABLED="/etc/nginx/sites-enabled/${SITE_NAME}.conf"

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot python3-certbot-nginx ufw rsync

ufw allow OpenSSH
ufw allow 'Nginx Full'

install -d -o www-data -g www-data -m 0755 "$WEB_ROOT"

render_bootstrap_conf
ln -sfn "$SITE_AVAILABLE" "$SITE_ENABLED"

nginx -t
systemctl enable --now nginx
systemctl reload nginx

certbot --nginx -d "$DOMAIN" --redirect --agree-tos -m "$EMAIL" -n

render_final_conf
nginx -t
systemctl reload nginx
