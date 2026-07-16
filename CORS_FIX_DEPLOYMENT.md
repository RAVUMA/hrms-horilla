# CORS Fix — Deployment Instructions

## What this is

A new web app (mobile-responsive HR portal) calls this server's `/api/...`
endpoints directly from the browser, from a different origin than
`hrms.hjholdings.lk`. The browser blocks this by default — Django's
`corsheaders` middleware is already installed and enabled here, but no
allowed origins were ever configured, so it silently rejects every
cross-origin request. This is why the web app gets a network error while
everything else (the existing website, the mobile app) works fine — only
browsers enforce CORS, so this never showed up before.

Confirmed via direct testing: the server's preflight response has no
`Access-Control-Allow-Origin` header at all.

## What changed (already committed, just needs deploying)

- `horilla/settings.py` — added a new `CORS_ALLOWED_ORIGINS` setting, read
  from the environment the same way `CSRF_TRUSTED_ORIGINS` already is.
  Defaults to empty (blocks everything) if not set, so this change alone is
  a no-op until the env var below is actually configured.
- `.env.dist` — documents the new variable.

## What you need to do on the server

1. **Pull the latest code** (this branch/commit includes the two file
   changes above).

2. **Add to the production `.env` file**:
   ```
   CORS_ALLOWED_ORIGINS=https://mobile.hjholdings.lk
   ```
   The web app is now live at `https://mobile.hjholdings.lk` — that's the
   exact origin that must be allowed. Comma-separate additional origins if
   needed (e.g. `http://localhost:5173` too, for local development testing):
   ```
   CORS_ALLOWED_ORIGINS=https://mobile.hjholdings.lk,http://localhost:5173
   ```
   Each entry must include the scheme (`http://` or `https://`) and no
   trailing slash.

3. **Restart the Django process** (gunicorn/whatever service manager is in
   use) so it picks up the new `.env` value.

## How to verify it worked

```
curl -s -i -X OPTIONS "https://hrms.hjholdings.lk/api/auth/login/" \
  -H "Origin: https://mobile.hjholdings.lk" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
```
Should return a header `access-control-allow-origin: https://mobile.hjholdings.lk`
in the response. If that header is missing, the `.env` value wasn't picked
up (check for typos, confirm the service actually restarted).

**Status as of last check: still not deployed** — the live server still
returns no `Access-Control-Allow-Origin` header at all for this origin, so
the mobile web app's login is still blocked.
