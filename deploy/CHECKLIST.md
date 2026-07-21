# First Deploy Checklist

Fill this out against the live site after the first real deploy.

Domain: ______________________________
Date: ________________________________
Operator: ____________________________

## Automated Checks

- [ ] `DOMAIN=<your-domain> ./deploy/smoke.sh` returns success.
- [ ] `https://<your-domain>/robots.txt` returns `200` and contains `Disallow: /`.
- [ ] `curl -sSI https://<your-domain>/ | grep -i content-security-policy` shows `connect-src 'none'`.
- [ ] `echo | openssl s_client -connect <your-domain>:443 -servername <your-domain> 2>/dev/null | openssl x509 -noout -dates` shows a valid, non-expired certificate.

## Manual Browser Checks

- [ ] The page loads on desktop and mobile without layout breakage.
- [ ] CRT scanlines and frame styling render as expected.
- [ ] Sidebar navigation works and the Overview screen is visible.
- [ ] DevTools console shows no runtime errors.
- [ ] DevTools Network shows no requests outside the app's own origin.
- [ ] The main JS bundle under `/assets/` is cached with `immutable`.

## User Sign-Off

- [ ] I manually verified the items above against the live deployment.

Name: ________________________________
Date: _________________________________
Notes: ________________________________
