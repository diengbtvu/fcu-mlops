# Hydrogen Production Rate Prediction — MLOps Platform

[![CI - Testing & Quality Checks](https://github.com/diengbtvu/fcu-mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/diengbtvu/fcu-mlops/actions/workflows/ci.yml)
[![PHP](https://img.shields.io/badge/PHP-8.2-blue.svg)](https://www.php.net/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Laravel](https://img.shields.io/badge/Laravel-12.x-red.svg)](https://laravel.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-brightgreen.svg)](https://www.docker.com/)

End-to-end platform for predicting **Hydrogen Production Rate (HPR)** from dark-fermentation
process data: a Laravel web application (auth, admin panel, dataset & model management) in
front of a Python/Flask ML service that trains models, runs inference, tracks experiments in
MLflow, and generates LLM-assisted analysis reports.

**Contents** — [Quick start](#quick-start-local) · [Configuration](#configuration) ·
[Manual setup](#manual-setup-without-docker) · [Project structure](#project-structure) ·
[CI/CD](#cicd) · [Production deploy (blue/green)](#production-deploy-bluegreen) ·
[Troubleshooting](#troubleshooting)

---

## Architecture

### Local / development stack (`docker-compose.yml`)

```
                    :52025
   browser ───────────────────▶  nginx  ──── php-fpm :9000 ───▶  laravel-webapp
                                   │                                   │
                                   └──── /predict/, /train/ ──▶  predict-service :5000
                                                                       │
                                             mysql :3306  ◀────────────┘
```

| Service | Image / build | Port | Role |
|---|---|---|---|
| `nginx` | `nginx:alpine` | `52025 → 80` | Reverse proxy, serves `public/`, routes `/predict/` + `/train/` to the ML service |
| `laravel-webapp` | `WebApp/dockerfile` (php 8.2-fpm) | `9000` (internal) | Web app, admin panel, business logic |
| `predict-service` | `predict-service/dockerfile` (python 3.11) | `5000` | Training, inference, MLflow, report generation |
| `mysql` | `mysql:8.0` | internal | Users, datasets, model metadata, prediction history |

### Prediction contract

11 biochemical input features → `HPR` (L/h/L):

`ph`, `vss`, `ethanol`, `acetate`, `propionate`, `butyrate`, `sucrose_degradation`,
`orp_mid`, `orp_low`, `vfa`, `cod_o`

---

## Quick start (local)

**Requirements:** Docker 28.1+ and Docker Compose v2. Nothing else — PHP, Python and MySQL
all run inside containers. Budget ~15 GB of free disk: the `predict-service` image alone is
about 8 GB (TensorFlow, MLflow, ZenML).

```bash
git clone git@github.com:diengbtvu/fcu-mlops.git
cd fcu-mlops

# First run: creates .env.docker from the example, builds images, starts everything,
# runs migrations + seeders.
./deploy.sh --fresh
```

Then open **http://localhost:52025**.

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `Admin@123` |
| Regular user | `testuser` | `Test@123` |
| Sample users | `johnsmith`, `janewilson`, `mikebrown`, `sarahdavis` | `User@123` |

> Log in with the **username**, not the email address.

Swagger docs for the ML service: **http://localhost:5000/api-docs/**

The first build takes 10–20 minutes (mostly the ML dependencies). Subsequent
`./deploy.sh` runs reuse the cached layers.

### `deploy.sh` / `quick-docker.sh` (local orchestration)

`deploy.sh` in the repository root is the local convenience wrapper — **not** the production
deployer, which lives in [`deploy/`](deploy/).

| Command | What it does |
|---|---|
| `./deploy.sh` | Start / update the stack, keep existing data |
| `./deploy.sh --fresh` | Wipe volumes, rebuild, migrate + seed from scratch |
| `./deploy.sh --build` | Rebuild images without cache |
| `./deploy.sh --restart` | Restart containers |
| `./deploy.sh --stop` | Stop containers |
| `./deploy.sh --logs` | Follow logs |

`./quick-docker.sh up|fresh|build|stop|restart|logs` is a shorter alias for the same thing.
Windows: `.\deploy.ps1` with `-Fresh`, `-Build`, `-Stop`, `-Logs`, `-Restart`.

---

## Configuration

All local settings live in **`.env.docker`** (created from `.env.docker.example` on first
run, gitignored). `deploy.sh` copies it into `WebApp/.env` and generates `APP_KEY`.

| Key | Meaning |
|---|---|
| `APP_URL` / `PUBLIC_APP_URL` | Public base URL. Set `PUBLIC_APP_URL` when serving from a public IP or domain instead of `localhost`. |
| `DB_*` | Must match the credentials of the `mysql` service in `docker-compose.yml`. |
| `PREDICT_SERVICE_URL` | In-cluster URL of the ML service (`http://predict-service:5000`). |
| `PREDICT_SERVICE_PUBLIC_URL` | URL the *browser* uses to poll training progress. |
| `JWT_SECRET` | Shared secret for Laravel ↔ predict-service calls. **Change it outside of local dev.** |
| `REPORT_LLM_PROVIDER`, `OPENAI_*` | LLM used for training reports and benchmark evaluation. `OPENAI_BASE_URL` accepts any OpenAI-compatible endpoint. |

Local-only tweaks (extra services, changed ports) belong in `docker-compose.override.yml` —
copy `docker-compose.override.yml.example` to get started. Production values are **not**
configured here; each color has its own env file under `deploy/` (see below).

---

## Manual setup (without Docker)

Only needed if you want to run the pieces natively.

**1. Laravel web app**

```bash
cd WebApp
composer install
cp .env.example .env
php artisan key:generate
php artisan migrate
php artisan db:seed
php artisan serve            # http://localhost:8000
```

**2. Predict service**

```bash
cd predict-service
cp .env.example .env
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py                # http://localhost:5000
```

Point `PREDICT_SERVICE_URL` in `WebApp/.env` at `http://localhost:5000`, and make sure
`JWT_SECRET` is identical on both sides.

---

## Project structure

```
fcu-mlops/
├── docker-compose.yml            # Local dev stack (nginx / laravel / predict / mysql)
├── deploy.sh · deploy.ps1        # LOCAL orchestration helpers
├── quick-docker.sh               # Short aliases for deploy.sh
├── docker/nginx/                 # Nginx config + the frontend image used in production
│
├── WebApp/                       # Laravel 12 application
│   ├── app/{Http,Models,Services}
│   ├── resources/views/          # Blade + AdminLTE
│   ├── database/{migrations,seeders}
│   └── tests/Feature/
│
├── predict-service/              # Python / Flask ML service
│   ├── app/{routes,models,ml_model,reports}
│   ├── tests/                    # pytest suite (incl. benchmarking)
│   └── requirements.txt
│
├── deploy/                       # PRODUCTION blue/green deployment (runs on the server)
│   ├── deploy.sh · rollback.sh · switch_proxy.sh · smoke_test.sh · migrate.sh
│   ├── docker-compose.app.yml    # One color's stack
│   ├── docker-compose.db.yml     # Shared MySQL
│   └── README.md                 # Full blue/green documentation
│
└── .github/workflows/            # ci.yml · deploy-prod.yml · rollback.yml
```

---

## CI/CD

Three workflows. CI is automatic; **both deployment workflows are manual
(`workflow_dispatch`)** — nothing ever reaches production without someone pressing the
button.

```
push / PR to main|dev ──▶ ci.yml
                            ├── Laravel Tests      (PHPUnit + Pint, SQLite)
                            ├── Python/ML Tests    (flake8, black, isort, pytest)
                            ├── Security Scanning  (composer audit, safety)
                            ├── Build Summary
                            └── Build & Push Images   ← only on push to main
                                     │
                                     ▼
                          ghcr.io/diengbtvu/fcu-mlops-{webapp,frontend,predict}:<sha12>
                                     │
       manual: "Deploy to Production (blue/green)"  ──SSH──▶  deploy/deploy.sh prod <tag>
       manual: "Rollback (blue/green)"              ──SSH──▶  deploy/rollback.sh <color>
```

### `ci.yml` — Testing & Quality Checks

Runs on every push and pull request to `main` or `dev`. Concurrent runs on the same ref are
cancelled.

| Job | What it does | Blocking? |
|---|---|---|
| **Laravel Tests** | PHP 8.2 + Composer (cached), SQLite database, `php artisan migrate`, `php artisan test`, `pint --test`, uploads coverage | Reported, non-blocking |
| **Python/ML Tests** | Python 3.11 (pip cached), `flake8`, `black`/`isort` checks, `safety`, `pytest --cov` | flake8 syntax/undefined-name errors fail the job; the rest report only |
| **Security Scanning** | `composer audit` + `safety check` | Reports only |
| **Build Summary** | Writes a status table to the GitHub Step Summary; fails the run if a test job failed | Yes |
| **Build & Push Images** | Builds the three production images with Buildx (GHA layer cache) and pushes them to GHCR | Runs **only** on `push` to `main`, after both test jobs pass |

The image tag is the **first 12 characters of the commit SHA**, and that same tag is what you
hand to the deploy workflow — so every production release traces back to exactly one commit:

```
ghcr.io/diengbtvu/fcu-mlops-webapp:<sha12>      # php-fpm + Laravel app code
ghcr.io/diengbtvu/fcu-mlops-frontend:<sha12>    # nginx + public/ assets
ghcr.io/diengbtvu/fcu-mlops-predict:<sha12>     # Flask + ML stack
```

### `deploy-prod.yml` — Deploy to Production (blue/green)

Manual dispatch with two inputs:

| Input | Required | Notes |
|---|---|---|
| `confirm` | yes | Must be exactly `DEPLOY` — a guard job fails the run otherwise |
| `tag` | no | 12-char image tag. Empty = current `HEAD` of `main` |

The concurrency group `prod-deploy` (shared with rollback, `cancel-in-progress: false`) makes
overlapping deploys impossible. The job SSHes into the server, refreshes only the deployment
files from `origin/main` (`deploy/`, `docker/`, the two dockerfiles), then runs
`deploy/deploy.sh prod <tag>`.

### `rollback.yml` — Rollback (blue/green)

Manual dispatch, one input: `color` (`blue` | `green`). SSHes in and runs
`deploy/rollback.sh <color>`, which restarts that color's existing containers, waits for
health, smoke-tests them, and flips the proxy back. It recovers the image tag from the
container itself, so you don't have to remember what was running.

### Required GitHub secrets

| Secret | Purpose |
|---|---|
| `SSH_HOST` | Production server address |
| `SSH_USER` | SSH user |
| `SSH_PRIVATE_KEY` | Private key for that user |
| `SSH_PORT` | Optional, defaults to `22` |
| `DEPLOY_PATH` | Absolute path of the repository checkout on the server |

Pushing to GHCR uses the built-in `GITHUB_TOKEN` with `packages: write` — no extra secret.

---

## Production deploy (blue/green)

Two identical application stacks — **blue** and **green** — sit behind an edge Caddy proxy
that points at exactly one of them at a time. A deploy brings the *idle* color up, verifies
it while it still receives zero traffic, flips the proxy, then drains and stops the old
color. MySQL and the proxy are permanent stacks that outlive every deploy.

```
   internet ──:443──▶  edge Caddy  ──── imports active-upstream.caddy ("to frontend-blue:80")
                            │
              ┌─────────────┴─────────────┐
        ┌─────▼──────┐              ┌─────▼──────┐
        │ hydrogen-  │   ACTIVE     │ hydrogen-  │   idle
        │   blue     │              │   green    │
        │  nginx     │              │  nginx     │
        │  webapp    │              │  webapp    │
        │  predict   │              │  predict   │
        └─────┬──────┘              └─────┬──────┘
              └────────────┬──────────────┘
                    ┌──────▼──────┐
                    │   mysql     │   shared, never redeployed
                    └─────────────┘
```

### What one deploy does (`deploy/deploy.sh prod <tag>`)

| Step | Action | If it fails |
|---|---|---|
| 1 | Acquire the `flock` deploy lock | Abort — another deploy is running |
| 2 | Preflight: ≥ 500 MB RAM and ≥ 5 GB disk free (both colors coexist during the window) | Abort, nothing touched |
| 3 | Read `.active-color`, derive the idle color | Abort |
| 4 | `mysqldump` backup of the shared DB (cache/session/queue tables excluded) | Abort |
| 5 | Run migrations with the **new** image against the shared DB | Abort — active color untouched |
| 6 | `pull` + `up -d` the idle color | Abort — active color untouched |
| 7 | Wait ≤ 120 s for all three containers to report `healthy` | Tear down the idle color |
| 8 | Smoke test the idle color via `docker exec` (never through the proxy) | Tear down the idle color |
| 9 | `switch_proxy.sh`: rewrite `active-upstream.caddy` in place, `caddy validate` + `reload` | Tear down the idle color |
| 10 | Verify `https://<domain>/health` through the real traffic path | **Auto-rollback**: proxy flipped back, new color left running for inspection |
| 11 | Background: 5-minute drain, stop the old color, prune old images and backups | — |

**Everything before step 9 is safe**: any failure leaves the previously-active color serving
traffic, untouched.

### Deploying

1. Merge to `main` → `ci.yml` builds and pushes the three images tagged with the commit SHA.
2. Actions → **Deploy to Production (blue/green)** → Run workflow → type `DEPLOY`; leave
   `tag` empty for the latest `main`, or paste an older tag to redeploy it.
3. Watch the job log — it streams the 11 steps above.

To roll back: Actions → **Rollback (blue/green)** → pick the other color. On the server the
equivalent is `cd deploy && ./rollback.sh blue`.

### The one rule for migrations

Both colors share **one** MySQL, and during the switch window old and new code run against
the same schema. Every migration must therefore be **additive and idempotent**: `ADD COLUMN`,
new tables, backfills with defaults. Never `DROP`, rename, or change a column type in the
same release that starts using the new shape — split it across two deploys.

### Checking state on the server

```bash
cat deploy/.active-color            # which color deploy.sh believes is live
cat deploy/active-upstream.caddy    # which color the proxy is actually routing to
docker compose -p hydrogen-blue ps
docker compose -p hydrogen-green ps
ls -lt deploy/backups/              # pre-deploy DB backups (10 most recent are kept)
tail -f deploy/logs/drain_*.log     # background drain of the old color
```

First-time server bootstrap, the shared-proxy wiring, the env-file layout and known
limitations are all documented in **[`deploy/README.md`](deploy/README.md)**.

---

## Development

```bash
# Laravel
cd WebApp
php artisan test                     # test suite
./vendor/bin/pint                    # auto-fix code style
php artisan migrate                  # apply new migrations
php artisan cache:clear && php artisan view:clear

# Predict service
cd predict-service
pytest tests/ -v
flake8 . --max-line-length=127
black . && isort .

# Repository-wide domain-terminology guard
./scripts/check-legacy-terms.sh
```

Inside the Docker stack, prefix with `docker compose exec`:

```bash
docker compose exec laravel-webapp php artisan migrate:status
docker compose exec predict-service pytest tests/ -v
```

---

## Troubleshooting

**Stack won't come up**

```bash
docker compose logs laravel-webapp
docker compose logs predict-service
docker compose down && docker compose up -d --build
```

**Database problems**

```bash
docker compose exec laravel-webapp php artisan migrate:status
docker compose exec mysql mysql -u laravel_user -p laravel_db
./deploy.sh --fresh          # nuclear option: wipes volumes and reseeds
```

**Assets 404 or links point at the wrong host** — `APP_URL` in `.env.docker` doesn't match
how you're actually reaching the app. Set `PUBLIC_APP_URL` to the real base URL and re-run
`./deploy.sh`.

**Permission errors on `storage/`**

```bash
docker compose exec laravel-webapp chown -R www-data:www-data storage bootstrap/cache
```

**The build fills the disk** — the ML image is ~8 GB and Buildx keeps a layer cache on top of
that. `docker builder prune -af` reclaims the cache; `docker system df` shows what is left.

**A production deploy failed** — check which step it died on. Steps 1–8 mean nothing changed
and the old color is still serving. Step 10 means it auto-rolled back and left the new color
running so you can inspect it with `docker compose -p hydrogen-<color> logs`.

---

## Documentation

| Document | Contents |
|---|---|
| [`deploy/README.md`](deploy/README.md) | Blue/green deployment in depth, server bootstrap, proxy wiring |
| [`.github/workflows/README.md`](.github/workflows/README.md) | Workflow reference (Vietnamese) |
| [`.github/workflows/ARCHITECTURE.md`](.github/workflows/ARCHITECTURE.md) | CI pipeline architecture |
| [`WebApp/README.md`](WebApp/README.md) | Laravel setup and API reference |
| [`predict-service/README.md`](predict-service/README.md) | Flask service configuration and API docs |
| `http://localhost:5000/api-docs/` | Interactive Swagger UI for the ML service |
