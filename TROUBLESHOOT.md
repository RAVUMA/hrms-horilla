# Troubleshooting Guide — HJ Holdings HRMS

This document records real issues encountered on the production/staging server, what caused them, how they were fixed, and how to prevent them in future.

---

## Issue #1 — Internal Server Error: PostgreSQL ran out of connections

**Date:** 2026-07-09
**Environment:** Both staging and production
**Symptom:** Website shows "Internal Server Error" with no code changes made

---

### What Happened

PostgreSQL has a maximum number of simultaneous connections it allows. The default limit is **100**. When that limit is hit, any new connection attempt is rejected with:

```
FATAL: remaining connection slots are reserved for non-replication superuser connections
```

Django cannot connect to the database → every page request fails → "Internal Server Error".

---

### Why It Happened

Three things combined to exhaust the connection limit:

**1. Two apps running simultaneously**
- `hjholdings-staging` on port 8001
- `hjholdings-production` on port 8002

**2. Each app had 3 Gunicorn workers**
Each worker holds its own open DB connection. With 2 apps × 3 workers = 6 persistent connections minimum — but Django was opening a new connection per request rather than reusing them.

**3. Horilla's background scheduler runs every 20-25 seconds**
The app runs two background jobs continuously:
- `leave_reset` — every 20 seconds
- `block_unblock_disciplinary` — every 25 seconds

Each job opens a new DB connection. When the server is under any load, old connections don't close before new ones open — they pile up rapidly.

**Result:**
```
hrms_prod    →  56 connections
hrms_staging →  41 connections
Total        →  97 out of 100 max → CRASH
```

---

### How to Detect It

**Check PM2 logs:**
```bash
pm2 logs hjholdings-staging --lines 50
```

Look for:
```
FATAL: remaining connection slots are reserved for non-replication superuser connections
```

**Check current connection count:**
```bash
sudo -u postgres psql -p 5433 -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname ORDER BY count DESC;"
```

**Check the PostgreSQL connection limit:**
```bash
sudo -u postgres psql -p 5433 -c "SHOW max_connections;"
```

If count is close to or equal to max_connections — this is the issue.

---

### How It Was Fixed

**Step 1 — Restart apps to immediately release all connections:**
```bash
pm2 restart hjholdings-staging
pm2 restart hjholdings-production
```

**Step 2 — Increase PostgreSQL max connections:**
```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```
Changed:
```
max_connections = 200
```
Restarted PostgreSQL:
```bash
sudo pg_ctlcluster 14 main restart
```

**Step 3 — Added connection reuse in Django settings:**

In both `/var/www/hjholdings/staging/horilla/settings.py` and `/var/www/hjholdings/production/horilla/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": ...,
        "NAME": ...,
        ...
        "CONN_MAX_AGE": 60,   # reuse connections for 60 seconds
    }
}
```

`CONN_MAX_AGE: 60` tells Django to reuse an existing DB connection for 60 seconds instead of opening a new one for every request. This dramatically reduces connection count.

**Step 4 — Reduced Gunicorn workers from 3 to 2:**

In `/var/www/hjholdings/ecosystem.config.js`:
```js
// staging
args: "--bind 127.0.0.1:8001 --workers 2 --timeout 120 horilla.wsgi:application",

// production
args: "--bind 127.0.0.1:8002 --workers 2 --timeout 120 horilla.wsgi:application",
```

```bash
pm2 reload /var/www/hjholdings/ecosystem.config.js --update-env
pm2 save
```

**Result after fix:**
```
hrms_staging →  6 connections
hrms_prod    →  6 connections
Total        →  12 out of 200 max ✓
```

---

### Why 2 Workers is Enough

For a 30-person HR team, 2 workers per app is more than sufficient:

- Each request takes 50-200ms to complete
- A worker is free again immediately after
- 2 workers can handle ~20 requests/second
- 30 HR staff realistically generate 2-3 requests/second combined
- You have ~10x more capacity than needed

---

### How to Prevent It in Future

| Prevention | Detail |
|---|---|
| `CONN_MAX_AGE: 60` in settings | Reuses connections instead of creating new ones per request — already applied |
| Max connections set to 200 | Gives headroom if connections spike again |
| Workers set to 2 per app | Reduces idle connections sitting open |
| Monitor connections regularly | Run the check query below during peak hours |

**Regular health check command:**
```bash
sudo -u postgres psql -p 5433 -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname ORDER BY count DESC;"
```

If `hrms_staging` or `hrms_prod` shows above **40 connections**, investigate immediately before it crashes.

---

### When to Add More Workers

Only increase workers if you genuinely experience slow response times under real load. The formula is:

```
workers = (number of CPU cores × 2) + 1
```

Check CPU cores:
```bash
nproc
```

For the current server, maximum recommended workers per app is **3**. Never go higher without also increasing `max_connections` in PostgreSQL proportionally.

---