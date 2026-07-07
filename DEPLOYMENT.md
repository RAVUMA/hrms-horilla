# Deployment Guide — HJ Holdings HRMS

Forked from [Horilla](https://github.com/horilla/horilla-hr). This guide covers the full manual deployment process on Ubuntu 22.04 LTS using Python/Gunicorn, PostgreSQL, PM2, and CloudPanel (Nginx).

---

## Architecture Overview

```
Internet → CloudPanel (Nginx)
                ├── hrms-staging.hjholdings.lk  → 127.0.0.1:8001  (branch: staging)
                └── hrms.hjholdings.lk          → 127.0.0.1:8002  (branch: master)

PM2 manages:
  ├── hjholdings-staging    (gunicorn on port 8001)
  └── hjholdings-production (gunicorn on port 8002)

PostgreSQL 14 runs on port 5433 (non-default)
  ├── Database: hrms_staging  / User: hrms_staging
  └── Database: hrms_prod     / User: hrms_prod
```

---

## Directory Structure

```
/var/www/hjholdings/
├── ecosystem.config.js       # PM2 process config
├── logs/
│   ├── staging-out.log
│   ├── staging-error.log
│   ├── production-out.log
│   └── production-error.log
├── staging/                  # branch: staging
│   ├── .env
│   ├── venv/
│   └── ...
└── production/               # branch: master
    ├── .env
    ├── venv/
    └── ...
```

---

## Initial Server Setup (One-Time)

### 1. System Dependencies

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y python3 python3-venv python3-pip python3-dev \
    build-essential libpq-dev gettext libcairo2-dev git curl
```

### 2. Node.js + PM2

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2
```

### 3. PostgreSQL

PostgreSQL 14 is installed and runs on **port 5433** (non-default).

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo pg_ctlcluster 14 main start
```

Check cluster status and port:

```bash
sudo pg_lsclusters
```

#### Create Staging Database

```bash
sudo -u postgres psql -p 5433
```

```sql
CREATE ROLE hrms_staging LOGIN PASSWORD 'your_strong_password';
CREATE DATABASE hrms_staging OWNER hrms_staging;
\q
```

#### Create Production Database (when ready)

```bash
sudo -u postgres psql -p 5433
```

```sql
CREATE ROLE hrms_prod LOGIN PASSWORD 'another_strong_password';
CREATE DATABASE hrms_prod OWNER hrms_prod;
\q
```

### 4. Directory Setup

```bash
sudo mkdir -p /var/www/hjholdings/staging
sudo mkdir -p /var/www/hjholdings/production
sudo mkdir -p /var/www/hjholdings/logs
sudo chown -R administrator:administrator /var/www/hjholdings
```

---

## Staging Deployment

### 1. Clone the Repository

```bash
cd /var/www/hjholdings/staging
git clone -b staging https://github.com/RAVUMA/hrms-horilla.git .
```

### 2. Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 3. Configure Environment Variables

```bash
cp .env.dist .env
nano .env
```

```env
DEBUG=False
SECRET_KEY=<generate at https://djecrety.ir>
ALLOWED_HOSTS=hrms-staging.hjholdings.lk
CSRF_TRUSTED_ORIGINS=https://hrms-staging.hjholdings.lk
TIME_ZONE=Asia/Colombo

DB_INIT_PASSWORD=<strong password — used for the DB initialization page>
DB_ENGINE=django.db.backends.postgresql
DB_NAME=hrms_staging
DB_USER=hrms_staging
DB_PASSWORD=<password set during database creation>
DB_HOST=localhost
DB_PORT=5433

# Leave DATABASE_URL blank — individual DB_* fields above are used instead
```

### 4. Initialize the Application

```bash
source venv/bin/activate
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --noinput
# Note: compilemessages may show a French locale error — this is a known upstream
# bug and can be safely ignored. The app runs fine without compiled translations.
```

### 5. Start with PM2

The PM2 ecosystem config lives at `/var/www/hjholdings/ecosystem.config.js`.

```bash
pm2 start /var/www/hjholdings/ecosystem.config.js --only hjholdings-staging
pm2 save
```

On first setup, also run:

```bash
pm2 startup
# Copy and run the command that PM2 prints — it makes PM2 survive reboots
```

### 6. CloudPanel Reverse Proxy

In CloudPanel, add a reverse proxy for `hrms-staging.hjholdings.lk`:

- **Target:** `http://127.0.0.1:8001`
- Enable SSL via Let's Encrypt in CloudPanel

---

## Production Deployment

### 1. Clone the Repository

```bash
cd /var/www/hjholdings/production
git clone -b master https://github.com/RAVUMA/hrms-horilla.git .
```

### 2. Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
```

### 3. Configure Environment Variables

```bash
cp .env.dist .env
nano .env
```

```env
DEBUG=False
SECRET_KEY=<generate a NEW key at https://djecrety.ir — different from staging>
ALLOWED_HOSTS=hrms.hjholdings.lk
CSRF_TRUSTED_ORIGINS=https://hrms.hjholdings.lk
TIME_ZONE=Asia/Colombo

DB_INIT_PASSWORD=<strong password — used for the DB initialization page>
DB_ENGINE=django.db.backends.postgresql
DB_NAME=hrms_prod
DB_USER=hrms_prod
DB_PASSWORD=<password set during database creation>
DB_HOST=localhost
DB_PORT=5433

# Leave DATABASE_URL blank — individual DB_* fields above are used instead
```

### 4. Initialize the Application

```bash
source venv/bin/activate
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py collectstatic --noinput
# Note: compilemessages may show a French locale error — this is a known upstream
# bug and can be safely ignored. The app runs fine without compiled translations.
```

### 5. Start with PM2

Uncomment the production block in `/var/www/hjholdings/ecosystem.config.js`, then:

```bash
pm2 start /var/www/hjholdings/ecosystem.config.js --only hjholdings-production
pm2 save
```

### 6. CloudPanel Reverse Proxy

In CloudPanel, add a reverse proxy for `hrms.hjholdings.lk`:

- **Target:** `http://127.0.0.1:8002`
- Enable SSL via Let's Encrypt in CloudPanel

---

## PM2 Reference

### Process Management

```bash
pm2 status                              # Show all running apps
pm2 start /var/www/hjholdings/ecosystem.config.js --only hjholdings-staging
pm2 stop hjholdings-staging             # Stop
pm2 restart hjholdings-staging          # Restart (after code changes)
pm2 reload hjholdings-staging           # Zero-downtime reload
pm2 delete hjholdings-staging           # Remove from PM2
```

### Logs

```bash
pm2 logs hjholdings-staging             # Live log tail
pm2 logs hjholdings-staging --lines 100 # Last 100 lines
pm2 logs --err hjholdings-staging       # Errors only
pm2 flush hjholdings-staging            # Clear log files
```

### Monitoring

```bash
pm2 monit                               # Real-time CPU/memory dashboard
pm2 show hjholdings-staging             # Detailed process info
```

### Persistence

```bash
pm2 save                                # Save current process list (run after any change)
pm2 startup                             # Generate systemd startup script
pm2 unstartup                           # Remove startup script
pm2 resurrect                           # Manually restore saved processes
```

### Changing the Port

Edit the ecosystem config:

```bash
nano /var/www/hjholdings/ecosystem.config.js
```

Change the port in the `args` line, then reload:

```bash
pm2 reload /var/www/hjholdings/ecosystem.config.js --update-env
pm2 save
```

Then update the CloudPanel reverse proxy to the new port.

**Reserved ports:**

- `8001` — Staging
- `8002` — Production

---

## Deploying Code Changes

### To Staging

```bash
cd /var/www/hjholdings/staging
git pull origin staging

source venv/bin/activate

# Only if requirements.txt changed:
pip install -r requirements.txt

# Only if there are new migrations:
python3 manage.py migrate

# Only if templates/static files changed:
python3 manage.py collectstatic --noinput

deactivate
pm2 restart hjholdings-staging
pm2 logs hjholdings-staging
```

### To Production

```bash
cd /var/www/hjholdings/production
git pull origin master

source venv/bin/activate
pip install -r requirements.txt      # if changed
python3 manage.py migrate            # if migrations exist
python3 manage.py collectstatic --noinput
deactivate

pm2 reload hjholdings-production     # zero-downtime reload for production
pm2 logs hjholdings-production
```

> Use `pm2 reload` (not `restart`) for production — it keeps the old workers alive until new ones are ready, avoiding downtime.

---

## Database Management

### Connect to Staging DB

```bash
psql -h localhost -p 5433 -U hrms_staging -d hrms_staging -W
```

### Connect to Production DB

```bash
psql -h localhost -p 5433 -U hrms_prod -d hrms_prod -W
```

### Backup Staging DB

```bash
pg_dump -h localhost -p 5433 -U hrms_staging hrms_staging > /var/www/hjholdings/staging_backup_$(date +%Y%m%d).sql
```

### Restore Staging DB

```bash
psql -h localhost -p 5433 -U hrms_staging -d hrms_staging < staging_backup_YYYYMMDD.sql
```

---

## Troubleshooting

### App not responding

```bash
pm2 status
pm2 logs hjholdings-staging --lines 50
```

### Database connection refused

```bash
sudo pg_lsclusters                          # Check PostgreSQL is online
sudo pg_ctlcluster 14 main start            # Start if offline
```

### Check what's running on a port

```bash
sudo ss -tlnp | grep 8001
```

### App starts then crashes repeatedly

```bash
pm2 logs hjholdings-staging --lines 100    # Read the actual error
```

### Environment variables not picked up after .env change

```bash
pm2 restart hjholdings-staging --update-env
```

---

## Initial App Setup (First Login)

After deployment, visit the relevant URL. You will see two options:

- Staging: `https://hrms-staging.hjholdings.lk`
- Production: `https://hrms.hjholdings.lk`

1. **Initialize Database** — Creates the super admin, company, department, and job position. Authenticate with the `DB_INIT_PASSWORD` from your `.env`.
2. **Load Demo Data** — Loads sample data. Authenticate with `DB_INIT_PASSWORD`.

Use option 1 for staging and production. Option 2 is only for testing purposes.
