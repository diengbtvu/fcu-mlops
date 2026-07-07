# Blue/green deployment

Single server, Docker Compose, edge proxy switch. Two identical stacks ("colors")
run side by side; the edge Caddy proxy always points at exactly one of them. A deploy
brings up the idle color, verifies it, flips the proxy, then drains and stops the old
color. The DB and the proxy are **not** part of either color - they are separate,
permanent stacks that outlive every deploy.

This server also hosts other, unrelated projects (`aura-content`, `byeielts-app`, a
tiktok scheduler, ...) all behind **one shared edge Caddy** - `aura-caddy`, part of the
`aura-content` project at `/root/aura-content`, *outside this repo* - which already owns
ports 80/443 for every domain on the box. There is no dedicated Caddy container for this
project: `zettix.net` is just one more server block appended to that shared
`/root/aura-content/Caddyfile`, and `aura-caddy` is joined to our `hydrogen_net` network
(in `/root/aura-content/docker-compose.yml`) so it can resolve `frontend-<color>`.
`switch_proxy.sh` runs `caddy validate`/`caddy reload` inside `aura-caddy` - same
mechanism as a dedicated proxy would use, just a different container name
(`PROXY_CONTAINER_NAME`, default `aura-caddy`).

```
                         ┌─────────────────────────┐
   internet ── :443 ──▶  │  aura-caddy (shared,    │  imports active-upstream.caddy
                         │  lives in aura-content) │  (+ byeielts.com, concat.lol, ...)
                         └────────────┬────────────┘
                                      │  hydrogen_net (external, shared)
                  ┌───────────────────┼───────────────────┐
                  │                                       │
        ┌─────────▼─────────┐                   ┌─────────▼─────────┐
        │ hydrogen-blue      │                   │ hydrogen-green     │
        │  nginx (frontend)──┼─ frontend-blue    │  nginx (frontend)──┼─ frontend-green
        │  laravel-webapp ───┼─ joins hydrogen_net│  laravel-webapp ──┼─ joins hydrogen_net
        │  predict-service   │  (to reach mysql) │  predict-service   │
        └────────────────────┘                   └────────────────────┘
                  │                                       │
                  └───────────────────┬───────────────────┘
                                      │ hydrogen_net
                         ┌────────────▼────────────┐
                         │   mysql (db stack)       │  shared by both colors
                         └──────────────────────────┘
```

Inside one color, `nginx`/`laravel-webapp`/`predict-service` talk to each other over
that color's own **default** Compose network (plain service names, e.g.
`http://predict-service:5000`) - blue and green never see each other's containers.
Only `nginx` (aliased `frontend-<color>`) and `laravel-webapp` (to reach `mysql`) also
join the shared **external** network `hydrogen_net`.

Because both colors share one MySQL, **every migration must be additive and
idempotent** (`ADD COLUMN`, new tables, backfills with defaults - never `DROP`/rename/
type changes) since old and new code run against the same schema simultaneously during
the switch window.

## Files

| File | Purpose |
|---|---|
| `docker-compose.app.yml` | One color's stack (nginx/laravel-webapp/predict-service). Instantiated twice, once per `COMPOSE_PROJECT_NAME` (`hydrogen-blue` / `hydrogen-green`). |
| `docker-compose.db.yml` | Shared MySQL. Started once, never touched by deploys. |
| `active-upstream.caddy` | One line, e.g. `to frontend-blue:80`. Bind-mounted into `aura-caddy` (see `/root/aura-content/docker-compose.yml`), rewritten in place by `switch_proxy.sh`. The `zettix.net` block that imports it lives in `/root/aura-content/Caddyfile`, not in this repo. |
| `.active-color` | Tracks which color is currently live. |
| `deploy.sh` | Orchestrator, run on the server: `deploy.sh prod <tag>`. |
| `migrate.sh` | Runs `php artisan migrate --force` using the idle color's new image, before it's started. |
| `switch_proxy.sh` | Flips the proxy, validates first, rolls back the file on failure. |
| `smoke_test.sh` | Tests the idle color directly via `docker exec` (never through the proxy). |
| `preflight_resources.sh` | Aborts the deploy early if RAM/disk headroom is too low. |
| `rollback.sh` | Re-point the proxy at a color that's already built (used by `rollback.yml` and manually). |
| `.env.blue` / `.env.green` / `.env.db` | Real secrets, gitignored. Copy from the matching `.example`. |

## First-time bootstrap (once per server)

Already done on `14.225.217.250` (see "Shared proxy wiring" below for what that
involved). Steps for setting this up fresh on another server:

```bash
# 1. Shared external network + named volumes (see docker-compose.*.yml for the exact names)
docker network create hydrogen_net
docker volume create hydrogen_mysql_data
docker volume create hydrogen_laravel_storage
docker volume create hydrogen_mlflow_runs
docker volume create hydrogen_mlflow_models
docker volume create hydrogen_training_progress

# 2. Registry login (GHCR). Use a PAT with read:packages if the packages are private.
echo "$GHCR_PAT" | docker login ghcr.io -u <your-github-username> --password-stdin

# 3. Env files
cd deploy
cp .env.db.example .env.db          && vi .env.db          # set MYSQL_ROOT_PASSWORD etc.
cp .env.blue.example .env.blue      && vi .env.blue        # DB_PASSWORD must equal .env.db's MYSQL_PASSWORD
cp .env.green.example .env.green    && vi .env.green       # identical secrets to .env.blue, only COLOR differs
cp .active-color.example .active-color
cp active-upstream.caddy.example active-upstream.caddy

# 4. Start the DB stack
docker compose -p hydrogen-db --env-file .env.db -f docker-compose.db.yml up -d

# 5. Wire zettix.net into whatever edge proxy already owns 80/443 on this server
#    (see "Shared proxy wiring" below) - there is no dedicated proxy stack to start here.

# 6. First deploy (brings up blue, the default active color per .active-color)
TAG=<12-char-sha-from-a-CI-run> ./deploy.sh prod "$TAG"
```

### Shared proxy wiring (what was actually done on this server)

There's no `docker-compose.proxy.yml` in this repo - `14.225.217.250` already runs a
shared Caddy (`aura-caddy`, project `aura-content` at `/root/aura-content`) for other
domains. Wiring `zettix.net` into it took two edits *outside this repo*:

1. `/root/aura-content/docker-compose.yml` - added `hydrogen_net` as an external network
   on the `caddy` service, and bind-mounted this repo's
   `/root/fcu-mlops/deploy/active-upstream.caddy` into the container at
   `/etc/caddy/active-upstream.caddy` (content-in-place, same rule as any other
   single-file bind mount here - never replace the file, only overwrite its content).
2. `/root/aura-content/Caddyfile` - added `email admin@zettix.net` to the existing
   global options block, and appended a `zettix.net { ... }` server block (same shape as
   the one in this repo's git history) that imports `active-upstream.caddy`.

Then `docker compose -p aura-content up -d --no-deps caddy` to recreate the container
with the new network/mount, `caddy validate` to confirm, and a `caddy reload`. Verified:
Let's Encrypt issued a cert for `zettix.net` immediately (DNS + ports 80/443 were already
reachable), and the other domains on that Caddy (`byeielts.com` was already returning 502
before this change, unrelated; `concat.lol` and the `aura` domain were unaffected) kept
working.

If this project ever moves to its own server (nothing else bound to 80/443), go back to
a dedicated Caddy stack instead: a `caddy:2-alpine` service publishing `80:80`/`443:443`,
mounting its own `Caddyfile` (the `zettix.net` block above, standalone) and
`active-upstream.caddy`, on the `hydrogen_net` network - and point
`PROXY_CONTAINER_NAME` in `switch_proxy.sh` at that container instead.

### Required GitHub Secrets (for `deploy-prod.yml` / `rollback.yml`)

`SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SSH_PORT` (optional, default 22),
`DEPLOY_PATH` (absolute path to this repo checkout on the server).

## Normal deploy flow

1. Push to `main` → `ci.yml` runs tests, then builds & pushes 3 images
   (`fcu-mlops-webapp`, `fcu-mlops-frontend`, `fcu-mlops-predict`) to GHCR tagged with
   the 12-char commit SHA.
2. Run `Deploy to Production` (`workflow_dispatch`) → type `DEPLOY` in `confirm`,
   optionally set `tag` (empty = latest `main` SHA) → SSHes in and runs
   `deploy/deploy.sh prod <tag>`.
3. `deploy.sh`: lock → preflight → backup DB → migrate (idle image) → pull+start idle
   color → wait healthy → smoke test idle directly → switch proxy → verify over the
   real `https://zettix.net/health` path → **auto-rollback** if that fails → 5 minute
   drain window → stop the old color, prune images, prune old backups.

Any failure before the switch step leaves the previously-active color completely
untouched. If the post-switch public verification fails, the proxy is flipped back
automatically and the *new* color is left running (not torn down) so you can inspect
`docker compose -p hydrogen-<idle-color> logs`.

## Manual rollback on the server (no CI needed)

```bash
cd deploy
./rollback.sh blue    # or green
```

This restarts (`docker start`, via `compose up -d`) whichever containers already exist
for that color - it recovers the image tag from the still-existing container, waits for
health, smoke-tests it, then switches the proxy. It does **not** need you to remember
which tag was previously running.

If the target color was fully torn down (`docker compose ... down`, not just `stop`),
there's nothing to restart - re-run `./deploy.sh prod <tag>` with the last-known-good
tag instead (check `backups/` timestamps or your CI run history to find it).

## Checking which color is active

```bash
cat deploy/.active-color                 # what deploy.sh/switch_proxy.sh last wrote
cat deploy/active-upstream.caddy         # what the proxy is actually routing to right now
docker compose -p hydrogen-blue  ps      # is blue up?
docker compose -p hydrogen-green ps      # is green up?
curl -sk --resolve zettix.net:443:127.0.0.1 https://zettix.net/health
```
`.active-color` and `active-upstream.caddy` should always agree; they're written
together as the last two steps of `switch_proxy.sh`.

## Known limitations / things to revisit

- The edge proxy is a shared resource owned by a different project
  (`/root/aura-content`). `switch_proxy.sh`/`deploy.sh` never touch its compose file or
  restart the container - only `active-upstream.caddy`'s content and a graceful
  `caddy reload` - but anyone editing `/root/aura-content/Caddyfile` for their own domains
  could break `zettix.net` (and vice versa) without either project's CI noticing. There's
  no automated check that the `zettix.net` block still exists there.
- Laravel's `/api/health` route is a liveness check only (doesn't touch the DB), so a
  broken DB connection won't fail the healthcheck or smoke test - it would surface as
  500s on real requests. Consider adding a DB ping to that route.
- `public/storage` (Laravel's storage symlink) is recreated on every `nginx` container
  start from the shared `laravel_storage` volume, since the frontend image never runs
  `artisan storage:link` itself.
- `APP_SLUG`/`REGISTRY`/`IMAGE_PREFIX`/`NET_EXTERNAL`/`VOLUME_PREFIX` all default to
  `hydrogen` / `ghcr.io/diengbtvu` / `fcu-mlops` / `hydrogen_net` / `hydrogen` - override
  via the env files or exported shell vars if you rename things later.
