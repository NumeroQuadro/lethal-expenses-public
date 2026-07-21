# Deploying Lethal Expenses

This directory contains the committed deployment artifacts for shipping the static `web/dist/` bundle to an Ubuntu VPS behind nginx.

## Prerequisites

- Ubuntu 22.04 or 24.04 LTS VPS
- `root` access or `sudo`
- A DNS `A` record for your domain that points to the VPS IP
- A local build artifact from `make dist`

## Environment Variables

Set these on the machine where you are running the commands:

```bash
export DOMAIN=example.com
export EMAIL=ops@example.com
export VPS=203.0.113.10
```

Optional:

```bash
export WEB_ROOT=/var/www/lethal-expenses
```

## 1. Provision the VPS

Copy the deploy directory to the server and run the setup script there:

```bash
rsync -az deploy/ root@$VPS:/root/lethal-expenses-deploy/
ssh root@$VPS "cd /root/lethal-expenses-deploy && DOMAIN='$DOMAIN' EMAIL='$EMAIL' ./setup-server.sh"
```

What this does:

- installs `nginx`, `certbot`, `python3-certbot-nginx`, `ufw`, and `rsync`
- opens `OpenSSH` and `Nginx Full` in `ufw`
- creates the web root at `/var/www/lethal-expenses`
- provisions the TLS certificate for `DOMAIN`
- renders the committed nginx config template with your domain and web root

## 2. Build the Static Artifact Locally

```bash
make dist
```

If you need a safe public demo build without personal financial data, seed the parser output from the synthetic fixture first:

```bash
make prepare-web-test-data
cd web && npm ci && npm run build
mkdir -p ../dist
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo smoke)
tar -C dist -czf ../dist/lethal-expenses-$GIT_SHA.tar.gz .
```

## 3. Deploy the Build

```bash
DOMAIN="$DOMAIN" VPS="$VPS" WEB_ROOT="$WEB_ROOT" ./deploy/deploy.sh
```

The deploy script:

- verifies a `dist/lethal-expenses-*.tar.gz` artifact exists
- extracts it locally into a temporary directory
- `rsync`s the static files to `root@$VPS:$WEB_ROOT/`
- validates nginx on the VPS and reloads it
- runs `deploy/smoke.sh` against `https://$DOMAIN/`

You can also run the smoke check manually at any time:

```bash
DOMAIN="$DOMAIN" ./deploy/smoke.sh
```

If local DNS is being intercepted by WARP, a VPN, or another tunnel, pin the real server IP while preserving the production hostname and TLS SNI:

```bash
DOMAIN="$DOMAIN" ./deploy/smoke.sh --ip "$VPS"
```

## 4. Renewal Logging Wrapper

`certbot` normally installs a systemd timer automatically. This repo also includes a lightweight weekly cron wrapper that writes to `/var/log/lethal-expenses-renew.log`.

Install it on the VPS with:

```bash
scp deploy/cron-renew.sh root@$VPS:/usr/local/sbin/lethal-expenses-renew
ssh root@$VPS "chmod 0755 /usr/local/sbin/lethal-expenses-renew && (crontab -l 2>/dev/null; echo '17 4 * * 0 /usr/local/sbin/lethal-expenses-renew') | crontab -"
```

Dry-run renewals remain useful before major DNS or proxy changes:

```bash
ssh root@$VPS "certbot renew --dry-run"
```

## 5. Manual Review Checklist

Use the operator checklist after the first real deploy:

```bash
sed -n '1,240p' deploy/CHECKLIST.md
```

## Optional GoAccess

GoAccess is off by default. To enable nightly static reports on a VPS:

```bash
ssh root@$VPS "apt-get update && apt-get install -y goaccess && install -d -m 0755 /var/log/goaccess"
ssh root@$VPS "(crontab -l 2>/dev/null; echo '43 1 * * * /usr/bin/goaccess /var/log/nginx/access.log -o /var/log/goaccess/lethal-expenses.html --log-format=COMBINED') | crontab -"
```

Adjust `/var/log/nginx/access.log` if your vhost writes to a dedicated access log.

## Optional Local Validation

Validate the nginx config in Docker with fake certificates:

```bash
./deploy/test-nginx.sh
```
