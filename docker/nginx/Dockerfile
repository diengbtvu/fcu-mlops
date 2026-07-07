# Frontend/edge-facing image: nginx + the static public/ assets, built from the
# same git commit as the laravel-webapp image so both are always in sync.
# Build context MUST be the repo root, e.g.:
#   docker build -f docker/nginx/Dockerfile -t <registry>/<app>-frontend:<tag> .
FROM nginx:alpine

RUN apk add --no-cache curl

COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY WebApp/public /var/www/html/public

# The shared laravel_storage volume (mounted at /var/www/html/storage) holds
# user-uploaded files under storage/app/public. Laravel normally exposes those
# via `php artisan storage:link`, but this image never runs artisan, so
# recreate the symlink on every start instead.
RUN echo '#!/bin/sh' > /docker-entrypoint.d/50-link-storage.sh \
    && echo 'ln -sfn ../storage/app/public /var/www/html/public/storage 2>/dev/null || true' >> /docker-entrypoint.d/50-link-storage.sh \
    && chmod +x /docker-entrypoint.d/50-link-storage.sh

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=6 \
    CMD curl -fsS http://127.0.0.1/api/health || exit 1
