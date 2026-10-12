# Deploying on Oracle Cloud (Always Free)

One free Oracle Cloud ARM server runs the whole stack from `docker-compose.prod.yml`:
Postgres, Redis, API, worker (with Chromium), beat, the web app, nginx, and Caddy for HTTPS.
Everything is served from **one hostname**: the web app at `/`, the API at `/api`, the snippet
at `/public/v1/agent.js`. Because it's one site, login cookies work without extra setup.

```
Internet ──443──> Caddy (free Let's Encrypt cert) ──> nginx ──┬─> web (SPA)
                                                              └─> api ──> Postgres, Redis
                                                     worker + beat ──> Postgres, Redis
```

Free-tier limits change. As of mid-2026, Always Free ARM is **2 OCPU / 12 GB RAM** in total
and 200 GB of block storage. Check Oracle's "Always Free Resources" page when you sign up.

---

## 1. Create the Oracle account

1. Sign up at **cloud.oracle.com** ("Start for free"). A card is needed for identity
   verification only. Always Free resources are not charged.
2. **Pick your home region carefully.** You can't change it later, and Always Free ARM
   servers only run in your home region. For Saudi/GCC users, Jeddah or Riyadh are closest.
   If ARM servers keep showing "out of capacity" there, a larger region (Frankfurt, London,
   Ashburn) usually has more.

## 2. Get a free hostname (DuckDNS)

HTTPS needs a hostname. Until you own a domain, use DuckDNS (free):

1. Sign in at **duckdns.org** with GitHub or Google.
2. Create a subdomain, e.g. `omnirank` → `omnirank.duckdns.org`. Leave the IP for now;
   you'll set it in step 4.

## 3. Create the server

In the Oracle console: **☰ → Compute → Instances → Create instance**.

| Setting | Value |
| --- | --- |
| Name | `omnirank` |
| Image | **Canonical Ubuntu 24.04** (click "Change image") |
| Shape | **Ampere → VM.Standard.A1.Flex**, **2 OCPU, 12 GB memory** (shows "Always Free-eligible") |
| Networking | Create new VCN + public subnet, **Assign a public IPv4 address** = yes |
| SSH keys | "Generate a key pair for me" → **Download private key** (keep it safe) |
| Boot volume | 100 GB is plenty |

Click **Create**. "Out of host capacity" means no free ARM servers are available right now.
Try again later or pick a different availability domain.

When it's running, copy the **Public IP address** from the instance page.

## 4. Point DuckDNS at the server

On duckdns.org, paste the public IP into your subdomain's **current ip** box and click
**update ip**.

## 5. Open ports 80 and 443

Oracle blocks web traffic in **two** places. Both must be opened.

**a) Oracle network (Security List).** Instance page → click the **subnet** → **Security
Lists** → the default list → **Add Ingress Rules**:

- Source CIDR `0.0.0.0/0`, IP protocol TCP, destination port `80`
- Source CIDR `0.0.0.0/0`, IP protocol TCP, destination port `443`

**b) The server's own firewall.** Done after you log in, in step 6.

## 6. Log in to the server

On your Mac:

```bash
chmod 400 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<PUBLIC_IP>
```

Then open the server firewall (Oracle's Ubuntu image rejects everything except SSH by default):

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 7. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
exit
```

Log back in with the same `ssh` command (so the docker group applies), then check:
`docker run --rm hello-world`.

## 8. Get the code

```bash
git clone https://github.com/adarshh-s/SEO-AEO-GEO-Agent.git omnirank
cd omnirank
```

If the repo is private, GitHub asks for a username and password. Use a **personal access
token** (GitHub → Settings → Developer settings → Fine-grained tokens, read-only "Contents"
on this repo) as the password. You don't need the submodule; the worker image downloads
claude-seo itself.

## 9. Create the `.env` file

Generate secrets on the server:

```bash
openssl rand -hex 32        # → JWT_SECRET
openssl rand -hex 16        # → POSTGRES_PASSWORD
python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"   # → APP_ENCRYPTION_KEY
```

```bash
cp .env.example .env
nano .env
```

Change these lines (replace `omnirank.duckdns.org` with your hostname). Leave the rest as is.

```ini
ENV=production
COOKIE_SECURE=true
SEED_DEMO=false
SITE_DOMAIN=omnirank.duckdns.org
APP_URL=https://omnirank.duckdns.org
API_URL=https://omnirank.duckdns.org/api
CORS_ORIGINS=https://omnirank.duckdns.org
VITE_API_URL=/api
POSTGRES_PASSWORD=<generated>
DATABASE_URL=postgresql://app:<same POSTGRES_PASSWORD>@postgres:5432/app
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<generated>
APP_ENCRYPTION_KEY=<generated>
WORKER_CONCURRENCY=2
# AI + data providers: add the keys and model names you use
GEMINI_API_KEY=...
GEMINI_MODEL=...
DATAFORSEO_LOGIN=...
DATAFORSEO_PASSWORD=...
```

Save with `Ctrl+O`, `Enter`, then exit with `Ctrl+X`. `EMAIL_PROVIDER=console` (the default)
prints emails to the logs. Switch to `resend` + `RESEND_API_KEY` when you want real email.

## 10. Start everything

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The first build takes 15–30 minutes on the free ARM server (Chromium and the frontend are the
slow parts). The API runs the database migrations itself when it starts. Check progress:

```bash
docker compose -f docker-compose.prod.yml ps          # all should be "running"/"healthy"
docker compose -f docker-compose.prod.yml logs -f api  # Ctrl+C to stop watching
```

Then open **https://omnirank.duckdns.org**. Caddy fetches the certificate on the first
request (a few seconds). `https://omnirank.duckdns.org/healthz` should say `healthy`.

## 11. Pre-flight check

```bash
docker compose -f docker-compose.prod.yml exec api python /repo/scripts/verify_prod_env.py
```

It should end with `PRE-FLIGHT CHECK PASSED`.

---

## Everyday commands

Run these from `~/omnirank` on the server.

| Task | Command |
| --- | --- |
| Deploy new code | `git pull && docker compose -f docker-compose.prod.yml up -d --build` |
| See logs | `docker compose -f docker-compose.prod.yml logs -f --tail=100 worker` |
| Restart one service | `docker compose -f docker-compose.prod.yml restart api` |
| Stop everything | `docker compose -f docker-compose.prod.yml down` (data is kept in volumes) |

**Backups.** The database lives only on this server. Use the daily `pg_dump` cron script
in [deployment.md §7](deployment.md#7-operational-runbook), and copy the dumps off the
server (e.g. to Oracle Object Storage, which has a free tier, or your own machine).

**Idle reclamation.** Oracle may reclaim Always Free servers that stay almost completely idle
for a week. The scheduled tracking jobs normally keep this server above that threshold.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Browser can't connect at all | Port 80/443 not open in **both** places (step 5a and the `iptables` commands in step 6) |
| Certificate error | DuckDNS IP doesn't match the server, or ports closed. `docker compose -f docker-compose.prod.yml logs caddy` |
| `api` keeps restarting | `docker compose -f docker-compose.prod.yml logs api`; usually a missing `JWT_SECRET` / `APP_ENCRYPTION_KEY` or a wrong `DATABASE_URL` password |
| Login doesn't stick | You're on `http://` instead of `https://`, or `APP_URL`/`CORS_ORIGINS` don't match the hostname |
