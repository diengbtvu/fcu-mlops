# Hydrogen Production Rate Prediction - Laravel MVC System

[![CI - Testing & Quality Checks](https://github.com/nguyenhuuluan1702/Hydrogen-MLOps/actions/workflows/ci.yml/badge.svg)](https://github.com/nguyenhuuluan1702/Hydrogen-MLOps/actions/workflows/ci.yml)
[![PHP Version](https://img.shields.io/badge/PHP-8.2+-blue.svg)](https://www.php.net/)
[![Python Version](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Laravel](https://img.shields.io/badge/Laravel-12.x-red.svg)](https://laravel.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)](https://www.docker.com/)

A comprehensive web-based machine learning system for predicting Hydrogen Production Rate (HPR) using machine learning models. The system includes a Laravel web application with admin panel, user management, and integration with a Python Flask-based prediction service.

## 🏗️ System Architecture

This project consists of two main components working together:

### 🌐 **WebApp** (Laravel MVC)
- **Frontend & Backend**: Full-stack Laravel application
- **User Interface**: Responsive web interface with Bootstrap & AdminLTE
- **Authentication**: Role-based user management (Admin/User)
- **Admin Panel**: Model management, user administration, system monitoring
- **File Management**: ML model upload and storage
- **Database**: User data, model metadata, prediction history

### 🤖 **Predict-Service** (Python Flask)
- **ML Engine**: Python Flask API for HPR regression predictions
- **Model Loading**: Dynamic ML model loading and inference
- **API Endpoints**: RESTful services for prediction requests
- **Documentation**: Swagger/OpenAPI documentation

## 🔬 Prediction Contract

The platform predicts **Hydrogen Production Rate (HPR)** from **11 biochemical input features**:

1. `ph`
2. `vss`
3. `ethanol`
4. `acetate`
5. `propionate`
6. `butyrate`
7. `sucrose_degradation`
8. `orp_mid`
9. `orp_low`
10. `vfa`
11. `cod_o`

Output:
- `HPR` in `L/h/L`

## 🚀 Quick Start


### Prerequisites

> **Note:** This project requires Docker version 28.1+ and Docker Compose 2.0+ for stable operation. If you need support for older Docker/Docker Compose versions, please contact the project owner for guidance or a compatible setup.

#### Option 1: Docker (Recommended)
- **Docker 28.1+** & **Docker Compose 2.0+**
- No additional dependencies needed

#### Option 2: Manual Installation
- **PHP 8.4+** with extensions
- **Python 3.11+** 
- **Node.js & npm**
- **Database** (MySQL/PostgreSQL/SQLite)

## 🐳 Docker Deployment (Recommended)

### Quick Docker Setup

> **Note for Fresh Clone**: When you first clone the repository, the deployment script will automatically create `.env.docker` from `.env.docker.example`. You can customize database credentials and other settings in `.env.docker` before running the deployment.

**Windows (PowerShell):**
```powershell
# Deploy with fresh database
.\deploy.ps1 -Fresh

# Or normal deployment (keeps existing data)
.\deploy.ps1
```

**Linux/Mac:**
```bash
# Make script executable
chmod +x deploy.sh

# Deploy with fresh database
./deploy.sh --fresh

# Or normal deployment (keeps existing data)
./deploy.sh
```

### What the Deployment Script Does
1. ✅ Creates `.env.docker` from example file (if not exists)
2. ✅ Copies environment config to WebApp
3. ✅ Builds Docker images
4. ✅ Starts all services (Laravel, Python API, MySQL, Nginx)
5. ✅ Runs database migrations and seeders
6. ✅ Creates default admin/user accounts

### Access Application
- 🌐 **Web Application**: http://localhost:52025
- 👤 **Admin Login**: `admin` / `Admin@123`
- 👤 **User Login**: `testuser` / `Test@123`

### Docker Architecture
The system uses Docker Compose to orchestrate multiple services:

- **🌐 Laravel WebApp** (Port 9000): Main web application (PHP-FPM)
- **🤖 Predict Service** (Port 5000): ML prediction service (Python Flask)
- **🗄️ MySQL Database** (Port 3306): Data storage (MySQL 8.0)
- **🌐 Nginx** (Port 52025→80): Reverse proxy and load balancer

![Docker deployment](images/Docker-deployment.png)


### Manual Installation Commands

**1. Install PHP (choose your platform):**
```bash
# Windows
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://php.new/install/windows/8.4'))

# Linux
/bin/bash -c "$(curl -fsSL https://php.new/install/linux/8.4)"

# macOS
/bin/bash -c "$(curl -fsSL https://php.new/install/mac/8.4)"
```

**2. Setup Laravel WebApp:**
```bash
cd WebApp

composer install
npm install

#Windows
Copy-Item .env.example .env
#Linux/Mac
cp .env.example .env


php artisan key:generate
php artisan migrate  # Select 'yes' if database doesn't exist
php artisan db:seed
npm run build
php artisan serve    # Runs on http://localhost:8000
```

**3. Setup Python Predict Service:**
```bash
cd predict-service

#Windows
Copy-Item .env.example .env
#Linux/Mac
cp .env.example .env


python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python run.py        # Runs on http://localhost:5000
```

## 🌟 Key Features

### User Management
- ✅ **Role-based Authentication** (Admin/User roles with granular permissions)
- ✅ **User Login** with secure sessions
- ✅ **Admin Panel** for user management (CRUD operations)
- ✅ **Profile Management** and admin password reset
- ✅ **Multi-language Support** (English, Vietnamese, Chinese)

### Machine Learning Integration
- ✅ **Model Upload & Management** through web interface
- ✅ **MLflow Integration** for experiment tracking
- ✅ **Dynamic Model Loading** with metadata storage
- ✅ **Real-time Predictions** via Flask API
- ✅ **Prediction History** with detailed analytics
- ✅ **Model Comparison Tool** for performance evaluation
- ✅ **Model Validation & Testing** before deployment

### Dataset & Training Features
- ✅ **Dataset Management** (Upload, view, delete datasets)
- ✅ **Model Training Pipeline** with configurable parameters
- ✅ **Data Augmentation** capabilities
- ✅ **Training Progress Tracking** with real-time updates

### System Administration
- ✅ **Admin Dashboard** with system overview and statistics
- ✅ **User Management** (Create, edit, delete, anonymize)
- ✅ **Permission Management** (Role-based & user-specific)
- ✅ **ML Model Management** with force delete options
- ✅ **Email Settings** with test functionality
- ✅ **System Health Monitoring** for API services

### Technical Features
- ✅ **Responsive Design** (Bootstrap 5 + AdminLTE 3)
- ✅ **RESTful API Integration** with JWT authentication
- ✅ **File Upload Security** with size and type validation
- ✅ **Database Optimization** with proper indexing
- ✅ **Database Caching** for improved performance
- ✅ **Comprehensive Error Handling** and logging
- ✅ **API Health Checks** for service availability

## 📁 Project Structure

```
Hydrogen-MLOps/
├── docker-compose.yml               # Docker orchestration configuration
├── docker/
│   └── nginx/
│       └── default.conf             # Nginx reverse proxy config
│
├── WebApp/                          # Laravel MVC Application
│   ├── dockerfile                   # Laravel container configuration
│   ├── app/
│   │   ├── Http/Controllers/        # Request controllers
│   │   ├── Models/                  # Eloquent models
│   │   └── Services/                # Business logic
│   ├── resources/views/             # Blade templates
│   ├── public/                      # Web assets & uploads
│   ├── database/                    # Migrations & seeders
│   └── README.md                    # Laravel setup guide
│
├── predict-service/                 # Python Flask API
│   ├── dockerfile                   # Python API container configuration
│   ├── app/
│   │   ├── routes/                  # API endpoints
│   │   ├── models/                  # ML model utilities
│   │   ├── middlewares/             # Authentication
│   │   └── scalers/                 # Data preprocessing
│   ├── ml_model/                    # Trained models & scalers
│   └── README.md                    # Flask API setup guide
│
└── README.md                        # This file
```

## 🎯 User Workflows

### Regular Users
1. **Register/Login** → Access personal dashboard
2. **Make Predictions** → Input parameters, get ML results
3. **View History** → Track previous predictions
4. **Manage Profile** → Update account settings

### Administrators
1. **Admin Dashboard** → System overview and statistics
2. **Make predictions and view history** → Get ML results and view previous predictions
3. **User Management** → Create, edit, delete, reset passwords
4. **Model Management** → Upload, activate, delete ML models
5. **System Monitoring** → Health checks and logs

## 🔧 Development & Maintenance

### Laravel WebApp Development
```bash
cd WebApp

# Development commands
npm run build              # Build frontend assets
php artisan cache:clear    # Clear application cache
php artisan view:clear     # Clear compiled views
php artisan migrate        # Run new migrations
php artisan test           # Run test suite
./vendor/bin/phpunit --display-deprecations --display-warnings --fail-on-deprecation --fail-on-warning
```

### Python Service Development
```bash
cd predict-service

# Development commands
python run.py             # Start development server
pip install -r requirements.txt  # Install dependencies
# Access Swagger docs: http://localhost:5000/api-docs/

# Legacy domain guard (run from repository root)
cd ..
./scripts/check-legacy-terms.sh
```

## 🔍 API Integration

The Laravel webapp communicates with the Python service via HTTP APIs:

- **Prediction Endpoint**: `POST /predict/model`
- **Health Check**: `GET /predict/health`
- **Authentication**: JWT token-based
- **Documentation**: Available at `/api-docs/`

## 📊 Default System Data

### Default Users
- **Admin**: Full system access, user/model management
- **User**: Basic prediction access, personal dashboard

### Baseline ML Models
- **Hydrogen RF Baseline**: Seeded as the protected system baseline model
- **Hydrogen XGBoost Baseline**: Alternative boosted-tree baseline
- **Hydrogen ANN Baseline**: Neural-network baseline for comparison
- **Scalers**: Included preprocessing pipelines

## 🛡️ Security Features

- **CSRF Protection**: Laravel built-in security
- **XSS Prevention**: Input sanitization and output escaping
- **SQL Injection Protection**: Eloquent ORM safeguards
- **File Upload Security**: Type validation and secure storage
- **JWT Authentication**: Secure service-to-service communication
- **Password Hashing**: Bcrypt encryption
- **Session Management**: Secure session handling

## 🚨 Troubleshooting

### Common Issues

**Docker Issues:**
```bash
# Services not starting
docker compose down && docker compose up -d --build

# Database connection issues
docker compose exec laravel-webapp php artisan migrate:status
docker compose exec mysql mysql -u root -p

# Container logs
docker compose logs laravel-webapp
docker compose logs predict-service
docker compose logs mysql

# Clean rebuild (removes all data)
docker compose down -v
docker compose up -d --build

# Permission issues in containers
docker compose exec laravel-webapp chown -R www-data:www-data storage/ bootstrap/cache/
```

**WebApp Issues:**
```bash
# Permission errors
chmod -R 755 storage/ bootstrap/cache/

# Cache issues
php artisan cache:clear
php artisan config:clear

# Database issues
php artisan migrate:refresh --seed
```

**Predict Service Issues:**
```bash
# Python environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Dependencies
pip install -r requirements.txt --force-reinstall

# Model loading
ls -la ml_model/  # Check model files exist
```

## 📱 Responsive Design

The system works seamlessly across:
- **Desktop**: Full admin panel functionality
- **Tablet**: Optimized touch interface
- **Mobile**: Responsive prediction interface

## 📚 Documentation

- **WebApp/README.md**: Detailed Laravel setup and API reference
- **predict-service/README.md**: Python service configuration and API docs
- **Swagger UI**: Interactive API documentation at `/api-docs/`

