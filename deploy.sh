#!/bin/bash
# Hydrogen Production Rate Prediction - Docker Deployment Script
# Bash Script for Linux/Mac

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Hydrogen Production Rate Prediction - Docker Deploy${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Parse arguments
BUILD=false
FRESH=false
STOP=false
LOGS=false
RESTART=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --fresh)
            FRESH=true
            shift
            ;;
        --stop)
            STOP=true
            shift
            ;;
        --logs)
            LOGS=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker.${NC}"
    exit 1
fi

# Detect Docker Compose command (prefer modern plugin syntax)
if docker compose version > /dev/null 2>&1; then
    DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose > /dev/null 2>&1; then
    DOCKER_COMPOSE=(docker-compose)
else
    echo -e "${RED}Error: Docker Compose not found. Install Docker Compose plugin ('docker compose').${NC}"
    exit 1
fi

compose() {
    "${DOCKER_COMPOSE[@]}" "$@"
}

get_env_value() {
    local file="$1"
    local key="$2"
    grep -E "^${key}=" "$file" | tail -n1 | cut -d'=' -f2-
}

upsert_env_value() {
    local file="$1"
    local key="$2"
    local value="$3"
    if grep -qE "^${key}=" "$file"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

is_valid_laravel_app_key() {
    local key="$1"
    if [[ "$key" != base64:* ]]; then
        return 1
    fi

    local raw decoded_len
    raw="${key#base64:}"
    decoded_len="$(printf '%s' "$raw" | base64 -d 2>/dev/null | wc -c | tr -d '[:space:]')"
    [ "$decoded_len" = "32" ]
}

generate_laravel_app_key() {
    echo "base64:$(openssl rand -base64 32 | tr -d '\n')"
}

# Stop containers
if [ "$STOP" = true ]; then
    echo -e "${YELLOW}Stopping all containers...${NC}"
    compose down
    echo -e "${GREEN}Containers stopped successfully!${NC}"
    exit 0
fi

# View logs
if [ "$LOGS" = true ]; then
    echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    compose logs -f
    exit 0
fi

# Restart containers
if [ "$RESTART" = true ]; then
    echo -e "${YELLOW}Restarting containers...${NC}"
    compose restart
    echo -e "${GREEN}Containers restarted successfully!${NC}"
    exit 0
fi

# Create .env.docker from example if not exists
if [ ! -f ".env.docker" ]; then
    echo -e "${YELLOW}Creating .env.docker from .env.docker.example...${NC}"
    if [ -f ".env.docker.example" ]; then
        cp .env.docker.example .env.docker
        echo -e "${GREEN}.env.docker created successfully!${NC}"
    else
        echo -e "${RED}Error: .env.docker.example not found!${NC}"
        exit 1
    fi
fi

# Copy environment file to WebApp if not exists
if [ ! -f "WebApp/.env" ]; then
    echo -e "${YELLOW}Copying .env.docker to WebApp/.env...${NC}"
    cp .env.docker WebApp/.env
fi

# Ensure APP_KEY is valid for Laravel encryption/session cookies
APP_KEY_VALUE="$(get_env_value "WebApp/.env" "APP_KEY")"
if ! is_valid_laravel_app_key "$APP_KEY_VALUE"; then
    echo -e "${YELLOW}Generating valid APP_KEY for Laravel...${NC}"
    APP_KEY_VALUE="$(generate_laravel_app_key)"
    upsert_env_value "WebApp/.env" "APP_KEY" "$APP_KEY_VALUE"
fi
# Keep .env.docker key in sync with runtime env
upsert_env_value ".env.docker" "APP_KEY" "$APP_KEY_VALUE"

# For local HTTP access, secure cookies must be disabled to avoid 419 CSRF/session issues
APP_URL_VALUE="$(get_env_value "WebApp/.env" "APP_URL")"
SESSION_SECURE_COOKIE_VALUE="$(get_env_value "WebApp/.env" "SESSION_SECURE_COOKIE")"
if [[ "$APP_URL_VALUE" == http://* ]] && [[ "${SESSION_SECURE_COOKIE_VALUE,,}" == "true" ]]; then
    echo -e "${YELLOW}APP_URL uses HTTP; setting SESSION_SECURE_COOKIE=false for local Docker access...${NC}"
    upsert_env_value "WebApp/.env" "SESSION_SECURE_COOKIE" "false"
fi
# Keep .env.docker session cookie setting in sync with runtime env
SESSION_SECURE_COOKIE_VALUE="$(get_env_value "WebApp/.env" "SESSION_SECURE_COOKIE")"
if [ -n "$SESSION_SECURE_COOKIE_VALUE" ]; then
    upsert_env_value ".env.docker" "SESSION_SECURE_COOKIE" "$SESSION_SECURE_COOKIE_VALUE"
fi

# Ensure Laravel and predict-service share the same JWT secret
JWT_SECRET_VALUE="$(get_env_value "WebApp/.env" "JWT_SECRET")"
if [ -z "$JWT_SECRET_VALUE" ]; then
    echo -e "${YELLOW}JWT_SECRET is missing. Setting fallback value 'jwt_secret'.${NC}"
    JWT_SECRET_VALUE="jwt_secret"
    upsert_env_value "WebApp/.env" "JWT_SECRET" "$JWT_SECRET_VALUE"
fi
upsert_env_value ".env.docker" "JWT_SECRET" "$JWT_SECRET_VALUE"
# Export for docker-compose variable interpolation in predict-service
export JWT_SECRET="$JWT_SECRET_VALUE"

# Build containers
if [ "$BUILD" = true ] || [ "$FRESH" = true ]; then
    echo -e "${YELLOW}Building Docker images...${NC}"
    compose build --no-cache
fi

# Fresh start - remove volumes
if [ "$FRESH" = true ]; then
    echo -e "${YELLOW}Removing old volumes and containers...${NC}"
    compose down -v
fi

# Start containers
echo -e "${YELLOW}Starting Docker containers...${NC}"
compose up -d

# Ensure mounted directories are writable by predict-service runtime user
echo -e "${YELLOW}Ensuring predict-service volume permissions...${NC}"
if ! compose exec -T -u root predict-service sh -c \
    "mkdir -p /app/app/mlruns /app/app/models /app/training_progress && \
    chown -R apiuser:apigroup /app/app/mlruns /app/app/models /app/training_progress && \
    chmod -R u+rwX,g+rwX /app/app/mlruns /app/app/models /app/training_progress"; then
    echo -e "${YELLOW}Warning: Could not adjust predict-service volume permissions.${NC}"
    echo -e "${YELLOW}MLflow tracking may fallback to /tmp inside the container.${NC}"
fi

# Wait for MySQL to be ready
echo -e "${YELLOW}Waiting for MySQL to be ready...${NC}"
max_retries=30
retries=0
while [ $retries -lt $max_retries ]; do
    if compose exec -T mysql mysqladmin ping -h localhost -u root -pMySecureRootPass2025! 2>&1 | grep -q "mysqld is alive"; then
        break
    fi
    retries=$((retries + 1))
    echo -n "."
    sleep 2
done
echo ""

if [ $retries -eq $max_retries ]; then
    echo -e "${RED}MySQL failed to start in time!${NC}"
    exit 1
fi

echo -e "${GREEN}MySQL is ready!${NC}"

# Ensure Laravel Composer dependencies exist in mounted project volume
echo -e "${YELLOW}Checking Laravel dependencies...${NC}"
if ! compose exec -T laravel-webapp test -f /var/www/html/vendor/autoload.php; then
    echo -e "${YELLOW}Installing Composer dependencies...${NC}"
    compose exec -T laravel-webapp composer install --no-dev --optimize-autoloader --no-interaction
    echo -e "${GREEN}Composer dependencies installed.${NC}"
fi

# Clear cached config/routes/views so updated .env is applied
echo -e "${YELLOW}Clearing Laravel caches...${NC}"
compose exec -T laravel-webapp php artisan config:clear
compose exec -T laravel-webapp php artisan cache:clear
compose exec -T laravel-webapp php artisan route:clear
compose exec -T laravel-webapp php artisan view:clear

# Run migrations and seeders
if [ "$FRESH" = true ]; then
    echo -e "${YELLOW}Running database migrations...${NC}"
    compose exec laravel-webapp php artisan migrate:fresh --force
    
    echo -e "${YELLOW}Seeding database...${NC}"
    compose exec laravel-webapp php artisan db:seed --force
    
    echo -e "${YELLOW}Creating storage link...${NC}"
    compose exec laravel-webapp php artisan storage:link
    
    echo -e "${YELLOW}Clearing caches...${NC}"
    compose exec laravel-webapp php artisan config:clear
    compose exec laravel-webapp php artisan cache:clear
    compose exec laravel-webapp php artisan view:clear
else
    echo -e "${YELLOW}Running database migrations...${NC}"
    compose exec laravel-webapp php artisan migrate --force
fi

# Ensure at least initial users exist for login
echo -e "${YELLOW}Checking initial user data...${NC}"
USER_COUNT="$(compose exec -T mysql mysql -N -B -ularavel_user -pLaravelSecurePass2025! -D laravel_db -e 'SELECT COUNT(*) FROM users;' 2>/dev/null || echo 0)"
if [ "$USER_COUNT" = "0" ]; then
    echo -e "${YELLOW}No users found. Running database seeders...${NC}"
    compose exec -T laravel-webapp php artisan db:seed --force
    echo -e "${GREEN}Database seeded successfully.${NC}"
fi

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${CYAN}Access the application at: http://localhost:52025${NC}"
echo ""
echo -e "${YELLOW}Default admin credentials:${NC}"
echo "  Username: admin"
echo "  Password: Admin@123"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  View logs:         ./deploy.sh --logs"
echo "  Stop containers:   ./deploy.sh --stop"
echo "  Restart:           ./deploy.sh --restart"
echo "  Fresh install:     ./deploy.sh --fresh"
echo "  Rebuild images:    ./deploy.sh --build"
echo ""
