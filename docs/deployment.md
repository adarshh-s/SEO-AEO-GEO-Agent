# QuardLink Production Deployment Guide

This guide describes how to deploy and operate QuardLink in production. It covers both the primary PaaS architecture (**Railway + Vercel**, per architecture decision [D10](file:///Users/adarsh/Desktop/Projects/SEO%20agent/docs/decisions.md#L19)) and a self-hosted **Docker Compose** option for bare metal / VPS environments.

---

## 1. Architecture & Deployment Models

QuardLink is built with a decoupled architecture designed for multi-tenant isolation, background crawling, and AI answer engine tracking:

```
                      ┌───────────────────────────────────────┐
                      │            DNS / Cloudflare           │
                      │  quardlink.com   app.   api.   cdn.   │
                      └──────────┬─────────────────┬──────────┘
                                 │                 │
              HTTPS (Frontend)   │                 │ HTTPS (API)
                                 ▼                 ▼
                     ┌────────────────┐   ┌──────────────────────────┐
                     │ Vercel Edge/   │   │  FastAPI Backend (API)   │
                     │ Nginx SPA      │   │  (Railway / Docker)      │
                     │ (apps/web)     │   └────────┬──────┬──────────┘
                     └────────────────┘            │      │
                                                   │      │ Redis Queue
                                                   │      ▼
                                                   │  ┌───────────────────────┐
                                                   │  │ Redis 7               │
                                                   │  │ (Cache & Task Broker) │
                                                   │  └──────┬──────┬─────────┘
                                                   │         │      │
                                   SQL (psycopg3)  │         │      ▼
                                                   │         │  ┌───────────────────┐
                                                   │         │  │ Celery Beat       │
                                                   │         │  │ (Cron Scheduler)  │
                                                   │         │  └───────────────────┘
                                                   ▼         ▼
                                          ┌──────────────┐ ┌────────────────────┐
                                          │ PostgreSQL 16│ │ Celery Worker      │
                                          │ with RLS     │ │ (Playwright Headless│
                                          │ (app_tenant) │ │ Crawl, Serp, Agent)│
                                          └──────────────┘ └────────────────────┘
```

### Components

1. **Frontend (`apps/web`)**: Single-page application built with React, Vite, Tailwind v4, and `react-i18next` supporting English and Arabic (RTL).
2. **Backend API (`apps/api`)**: FastAPI service running sync SQLAlchemy 2.0 with psycopg3 threadpools, enforced by Postgres Row-Level Security (`app_tenant`).
3. **Background Worker (`apps/worker`)**: Celery prefork workers handling queues: `default`, `crawl` (with headless Chromium/Playwright), `tracking` (DataForSEO + AI engines), `agents`, and `deploy`.
4. **Scheduler (`beat`)**: Celery Beat triggering hourly/daily tracking cycles, audits, and cost budget monitoring.
5. **Datastores**: PostgreSQL 16 (relational data + RLS) and Redis 7 (broker, rate-limiting, and short-term cache).

---

## 2. Environment Variables Reference

Store these variables in your production secrets manager (Railway/Vercel dashboard or secure `.env` on VPS).

### Core & Security

| Variable             | Description                                                | Example / Default         |
| -------------------- | ---------------------------------------------------------- | ------------------------- |
| `JWT_SECRET`         | 32+ character random secret for JWT access tokens          | `openssl rand -hex 32`    |
| `APP_ENCRYPTION_KEY` | 32-byte key for AES encryption of customer API credentials | `openssl rand -base64 32` |
| `SEED_DEMO`          | Must be `false` in production                              | `false`                   |
| `SECURE_COOKIES`     | Set to `true` to require HTTPS cookies                     | `true`                    |
| `ENVIRONMENT`        | Environment tag                                            | `production`              |

### Networking & Domains

| Variable       | Description                             | Example                                           |
| -------------- | --------------------------------------- | ------------------------------------------------- |
| `APP_URL`      | Base URL of the web dashboard           | `https://app.quardlink.com`                       |
| `API_URL`      | Base URL of the API                     | `https://api.quardlink.com`                       |
| `CORS_ORIGINS` | Comma-separated list of allowed origins | `https://app.quardlink.com,https://quardlink.com` |

### Databases

| Variable       | Description                  | Example                                         |
| -------------- | ---------------------------- | ----------------------------------------------- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://app:PASSWORD@host:5432/quardlink` |
| `REDIS_URL`    | Redis connection string      | `redis://default:PASSWORD@host:6379/0`          |

### External AI & SEO Providers

| Variable              | Description                                                | Notes                            |
| --------------------- | ---------------------------------------------------------- | -------------------------------- |
| `OPENAI_API_KEY`      | OpenAI API key for ChatGPT visibility checks & suggestions | Optional if not using OpenAI     |
| `GEMINI_API_KEY`      | Google Gemini API key                                      | Optional if not using Gemini     |
| `ANTHROPIC_API_KEY`   | Anthropic Claude API key                                   | Optional if not using Claude     |
| `PERPLEXITY_API_KEY`  | Perplexity API key                                         | Optional if not using Perplexity |
| `DATAFORSEO_LOGIN`    | DataForSEO login email for rank tracking & SERPs           | Required for Google tracking     |
| `DATAFORSEO_PASSWORD` | DataForSEO password / API secret                           | Required for Google tracking     |

### Email Service

| Variable          | Description                                                                                                              | Example                  |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| `EMAIL_PROVIDER`  | Provider adapter (`resend` or `smtp`)                                                                                    | `resend`                 |
| `RESEND_API_KEY`  | Resend API key (if `EMAIL_PROVIDER=resend`)                                                                              | `re_123456789...`        |
| `EMAIL_FROM`      | Sender address                                                                                                           | `noreply@quardlink.com`  |
| `OPS_ALERT_EMAIL` | Operator address for cost ceiling alerts ([D8](file:///Users/adarsh/Desktop/Projects/SEO%20agent/docs/decisions.md#L17)) | `adarshs18400@gmail.com` |

### Frontend Build Arguments / Environment Variables

| Variable             | Description                                   | Example                         |
| -------------------- | --------------------------------------------- | ------------------------------- |
| `VITE_API_URL`       | API base URL accessed by the browser          | `https://api.quardlink.com/api` |
| `VITE_CONTACT_EMAIL` | Contact email for pricing / support inquiries | `adarshs18400@gmail.com`        |
| `VITE_CDN_URL`       | CDN base URL for hosted snippet JS            | `https://cdn.quardlink.com`     |

---

## 3. Recommended PaaS Deployment: Railway + Vercel

### Step 3.1: Railway Setup (Backend, Worker, DB, Redis)

1. **Create a Railway Project**:
   - In Railway, create a new project.
   - Provision a **PostgreSQL** plugin.
   - Provision a **Redis** plugin.

2. **Initialize Database & RLS Role**:
   Before running Alembic migrations, PostgreSQL requires the unprivileged `app_tenant` role for multi-tenant Row-Level Security:

   ```sql
   -- Connect via Railway DB query tool or psql
   DO $$
   BEGIN
     IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_tenant') THEN
       CREATE ROLE app_tenant NOLOGIN;
     END IF;
   END
   $$;
   ```

3. **Deploy Backend API Service**:
   - Add a GitHub repo service pointing to your repository.
   - Build using Dockerfile: `infra/docker/api.Dockerfile` (target: `prod`).
   - Set environment variables as listed in Section 2.
   - Expose port `8000`.
   - Add custom domain: `api.quardlink.com`.

4. **Deploy Celery Worker Service**:
   - Add a second service from the same repo.
   - Build using Dockerfile: `infra/docker/worker.Dockerfile` (target: `prod` with Playwright browsers).
   - Override start command:
     ```bash
     celery -A app_worker.celery_app worker -Q default,crawl,tracking,agents,deploy --pool=prefork --concurrency=4 --loglevel=INFO
     ```
   - Share all environment variables with the API service.

5. **Deploy Celery Beat (Scheduler)**:
   - Add a third service from the same repo.
   - Build using Dockerfile: `infra/docker/worker.Dockerfile`.
   - Override start command:
     ```bash
     celery -A app_worker.celery_app beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
     ```

6. **Run Alembic Database Migrations**:
   Run a one-off task on Railway or from the API console:
   ```bash
   uv run alembic upgrade head
   ```

### Step 3.2: Vercel Setup (Frontend)

1. In Vercel, click **Add New Project** and select your GitHub repository.
2. Configure project settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `apps/web`
   - **Build Command**: `pnpm build`
   - **Output Directory**: `dist`
   - **Install Command**: `pnpm install`
3. Configure Environment Variables:
   - `VITE_API_URL` = `https://api.quardlink.com/api`
   - `VITE_CONTACT_EMAIL` = `adarshs18400@gmail.com`
4. Add Custom Domains:
   - `app.quardlink.com` (Main web dashboard)
   - `quardlink.com` (Marketing landing & pricing pages)

---

## 4. Self-Hosted Deployment: Docker Compose

For deploying on a single VPS or dedicated Linux server (Ubuntu 22.04+ / Debian 12):

### Step 4.1: Host Prerequisites

- Install **Docker Engine** (v24.0+) and **Docker Compose** (v2.20+):
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  ```

### Step 4.2: Prepare Environment File

1. Clone the repository to the server:
   ```bash
   git clone <repo-url> /opt/quardlink
   cd /opt/quardlink
   ```
2. Create `.env` from template:
   ```bash
   cp .env.example .env
   ```
3. Update `.env` with production values:
   ```ini
   ENVIRONMENT=production
   SEED_DEMO=false
   SECURE_COOKIES=true
   JWT_SECRET=<generated-32-byte-hex>
   APP_ENCRYPTION_KEY=<generated-32-byte-base64>
   POSTGRES_PASSWORD=<strong-db-password>
   DATABASE_URL=postgresql://app:${POSTGRES_PASSWORD}@postgres:5432/app
   REDIS_URL=redis://redis:6379/0
   APP_URL=https://app.quardlink.com
   CORS_ORIGINS=https://app.quardlink.com,https://quardlink.com
   EMAIL_PROVIDER=resend
   RESEND_API_KEY=re_...
   OPS_ALERT_EMAIL=adarshs18400@gmail.com
   ```

### Step 4.3: Initialize Database & Run Migrations

1. Start postgres and redis:
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres redis
   ```
2. Wait for health check, then run migrations:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm api uv run alembic upgrade head
   ```

### Step 4.4: Run Pre-Flight Environment Validation

Run the built-in production validation script:

```bash
docker compose -f docker-compose.prod.yml run --rm api python scripts/verify_prod_env.py
```

Ensure all checks pass with: `🎉 PRE-FLIGHT CHECK PASSED! System is ready for production launch.`

### Step 4.5: Start Full Stack

```bash
docker compose -f docker-compose.prod.yml up -d
```

Verify all 7 containers are healthy:

```bash
docker compose -f docker-compose.prod.yml ps
```

### Step 4.6: SSL / TLS Certificate Setup

If using Nginx directly, obtain a certificate via Certbot or place Cloudflare Origin Certificates in `/etc/ssl/certs`:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d quardlink.com -d app.quardlink.com -d api.quardlink.com
```

---

## 5. Domain, DNS & Cookie Configuration

Configure the following DNS records at your registrar or Cloudflare:

| Type      | Host                | Target                      | Proxy Status          |
| --------- | ------------------- | --------------------------- | --------------------- |
| A / CNAME | `quardlink.com`     | Vercel / Server IP          | Proxied               |
| CNAME     | `app.quardlink.com` | Vercel / Server IP          | Proxied               |
| CNAME     | `api.quardlink.com` | Railway / Server IP         | Proxied (or DNS only) |
| CNAME     | `cdn.quardlink.com` | CDN origin / Storage bucket | Proxied               |

### Cookie Security & Cross-Domain Auth

- Access tokens are short-lived JWTs (15 min).
- Refresh tokens are stored in `httpOnly`, `Secure`, `SameSite=Lax` cookies.
- When `SECURE_COOKIES=true` is enabled, cookies are only transmitted over HTTPS.
- CSRF protection uses double-submit tokens returned in JSON responses and validated via the `X-CSRF-Token` request header.

---

## 6. Pre-Flight Verification & Health Checks

### 1. Scripted Pre-Flight Check

Run `python scripts/verify_prod_env.py` in your environment. It validates:

- [x] `JWT_SECRET` length (>= 32 chars) and absence of default dev strings.
- [x] `SEED_DEMO` is strictly `false`.
- [x] Postgres connection, ping, and existence of `app_tenant` RLS role.
- [x] Redis connection and ping.
- [x] Email provider keys and live SMTP configuration.
- [x] Production `APP_URL` and `CORS_ORIGINS` compliance.

### 2. Live Health Endpoint

Query the API health check:

```bash
curl -f https://api.quardlink.com/healthz
```

Expected output:

```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

---

## 7. Operational Runbook

### Postgres Backups

Set up a daily cron job to backup PostgreSQL:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/quardlink"
mkdir -p "$BACKUP_DIR"
docker compose -f /opt/quardlink/docker-compose.prod.yml exec -T postgres \
  pg_dump -U app app | gzip > "$BACKUP_DIR/backup-$(date +\%Y\%m\%d_\%H\%M\%S).sql.gz"
find "$BACKUP_DIR" -type f -mtime +30 -delete
```

### Rotating Secrets

1. **JWT Secret (`JWT_SECRET`)**:
   Rotating this will invalidate existing sessions and require users to log in again.
2. **App Encryption Key (`APP_ENCRYPTION_KEY`)**:
   Credential envelope keys are versioned in `integrations.encrypted_credentials`. Run the re-encryption utility prior to retiring the old key.

### Cost Guard & Spend Monitoring

- Platform admins can view real-time API provider usage, ceiling ratios, and reset billing counters at `/app/admin`.
- When an organization hits 100% of its monthly cost ceiling ([D7](file:///Users/adarsh/Desktop/Projects/SEO%20agent/docs/decisions.md#L16)), non-essential background tasks are automatically paused.
- Operator alerts are dispatched to `OPS_ALERT_EMAIL` (`adarshs18400@gmail.com`).
