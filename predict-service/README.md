# Predict Service

Python Flask-based machine learning service for predicting Hydrogen Production Rate (HPR). This service provides REST API endpoints for making predictions with pre-trained models.

## 🚀 Features

- **Flask-based REST API** with Blueprint architecture
- **Pre-trained models** for Hydrogen Production Rate prediction
- **JWT authentication middleware** for secure API access
- **CORS enabled** for cross-origin requests
- **Model and scaler lazy loading** for performance optimization
- **Health check endpoint** for service monitoring
- **Swagger API Documentation** with interactive testing

## 🔬 Prediction Input Contract

The service predicts Hydrogen Production Rate (`HPR`) from these 11 features:

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
- `prediction` mapped to HPR (`L/h/L`)

## 📚 API Documentation

### Access Swagger UI:
- **Direct Access**: http://localhost:5000/api-docs/
- **Features**: Interactive API testing, JWT authentication support, request/response schemas

### API Endpoints:
- **POST /predict/model** - ML prediction (requires JWT authentication)
  - Request: `{ ph, vss, ethanol, acetate, propionate, butyrate, sucrose_degradation, orp_mid, orp_low, vfa, cod_o, model_path }`
  - Response: `{ prediction, unit, user }`
- **GET /predict/health** - Health check
  - Response: `{ status, message }`

## 📋 Prerequisites

- Python 3.11+
- Pre-trained ML models (included in `ml_model/` directory)
- JWT secret key (shared with auth-service)
- pip or conda

## 🛠️ Local Development

### 1. Create Virtual Environment
```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac  
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory or use the project's main `.env` file:
```env
JWT_SECRET=your_jwt_secret_here
MODEL_DIR=app/ml_model
```

### 4. Run the Service
```bash
# Development server
python run.py
```

The service will be available at `http://localhost:5000`

## 🐳 Docker Development

### Build and Run
```bash
# Build the image
docker build -t predict-service .

# Run the container
docker run -p 5000:5000 --env-file .env predict-service
```

### With Docker Compose (Recommended)
```bash
# From the root directory
docker-compose up predict-service
```

## 📚 API Endpoints

### Prediction

#### POST /predict/model
Make predictions using dynamic ML models (requires authentication)

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request:**
```json
{
  "ph": 6.5,
  "vss": 3500,
  "ethanol": 12,
  "acetate": 25,
  "propionate": 8,
  "butyrate": 35,
  "sucrose_degradation": 72,
  "orp_mid": -180,
  "orp_low": -220,
  "vfa": 90,
  "cod_o": 12000,
  "model_path": "/path/to/model.keras"
}
```

**Response:**
```json
{
  "prediction": 0.8756,
  "unit": "L/h/L",
  "user": "testuser"
}
```

**Error Responses:**
```json
// Missing authorization
{
  "error": "Token missing"
}

// Invalid token
{
  "error": "Token expired"
}

// Missing fields
{
  "error": "Missing field: ph"
}
```

#### GET /predict/health
Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "message": "Predict service is running"
}
```

## 🧪 Testing

### Manual Testing
```bash
# Health check
curl http://localhost:5000/predict/health

# Get JWT token from auth service first
TOKEN=$(curl -X POST http://localhost:4000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "Test@123"}' | jq -r '.token')

# Make prediction
curl -X POST http://localhost:5000/predict/model \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "ph": 6.5,
    "vss": 3500,
    "ethanol": 12,
    "acetate": 25,
    "propionate": 8,
    "butyrate": 35,
    "sucrose_degradation": 72,
    "orp_mid": -180,
    "orp_low": -220,
    "vfa": 90,
    "cod_o": 12000,
    "model_path": "/path/to/model.keras"
  }'
```

## 📊 Offline Benchmarking

The service now includes an additive benchmarking module under `benchmarking/` for claim-level evaluation of artifact-grounded explanations. It does not modify Flask prediction endpoints or runtime inference contracts, but training reports can publish benchmark status back into `summary.json` for the Laravel report page.

When a training report is generated through `/train/model`, the report workflow now writes `benchmark_status` and `benchmark_summary` into the bundle `summary.json`. That lets the report page surface queued/running/completed benchmark state and download links for leaderboard outputs without changing prediction contracts.

After AI explanations complete, the runtime benchmark now runs real `A/B/C` generations with the benchmark client across the full Phase 2 chart bundle under the richest runtime condition, `image_table_summary`. It then publishes `selected_benchmark_explanations` and `benchmark_eval/selected_explanations.json` back into the report bundle so the Laravel report page shows only the benchmark-selected explanation payload after benchmark success.

Run it from `predict-service` with either the bundled synthetic fixture or an existing report bundle:

```bash
python3 scripts/run_benchmark.py --fixture-only --output-dir ./tmp/benchmark-fixture
python3 scripts/run_benchmark.py --bundle-path app/reports/AI_Long_PostPatch_20260322_1 --output-dir ./tmp/benchmark-real
python3 scripts/run_benchmark.py --bundle-path app/reports/AI_Long_PostPatch_20260322_1 --output-dir ./tmp/benchmark-real-openai --client openai
```

When a bundle contains `llm_explanations.json`, the CLI now ingests it automatically as the official `BASELINE_LLM` arm. That baseline is evaluated as evidence only; it is never used as ground truth. Each asset must now carry a structured `benchmark_payload` with `explanation_short`, `explanation_full`, and `claims[]`; legacy freeform-only baseline files are rejected instead of being heuristically parsed.

Current benchmark coverage includes:

- Core Phase 1 units: `model_comparison/main`, `incremental_feature_analysis/main`, `feature_ranking/gra`
- Phase 2 chart assets discovered from `asset_evidence.json`, including SHAP, feature importance, correlation, distribution, scatter, residual, and time-series chart families

See [docs/benchmarking.md](docs/benchmarking.md) for scope, outputs, and extension notes.

## 🏗️ Project Structure

```
predict-service/
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── __pycache__/        # Python cache files
│   ├── config/
│   │   ├── env.py          # Environment configuration
│   │   ├── swagger.py      # Swagger configuration
│   │   └── __pycache__/    # Python cache files
│   ├── middlewares/
│   │   ├── auth.py         # JWT authentication middleware
│   │   └── __pycache__/    # Python cache files
│   ├── models/
│   │   ├── dynamic_loader.py # Dynamic model loader utility
│   │   └── __pycache__/    # Python cache files
│   ├── routes/
│   │   ├── predict.py      # Prediction routes
│   │   └── __pycache__/    # Python cache files
│   └── scalers/
│       ├── shared_scaler.py # Shared scaler utility
│       └── __pycache__/    # Python cache files
├── ml_model/
│   └── scaler.pkl          # Trained data scaler
├── dockerfile              # Docker configuration
├── README.md              # This file
├── requirements.txt       # Python dependencies
└── run.py                 # Application entry point
```

## 🔧 Configuration

### Environment Variables
- `JWT_SECRET`: Secret key for JWT token verification (should match auth service)
- `MODEL_DIR`: Directory containing ML models (default: ml_model)

### Key Dependencies
- **Flask**: Web framework
- **TensorFlow/Keras**: Machine learning framework
- **scikit-learn**: Data preprocessing and scaling
- **PyJWT**: JWT token handling
- **Flask-CORS**: Cross-origin resource sharing
- **Flasgger**: Swagger/OpenAPI documentation

## 🔍 Monitoring

### Health Check
The service provides a health check endpoint at `/predict/health` that returns the service status.

### Logging
The service logs important events including:
- Model loading
- Prediction requests
- Authentication attempts
- Errors and exceptions

## 🚨 Troubleshooting

### Common Issues

1. **Model Loading Errors**
   ```bash
   # Check if model files exist
   ls -la app/ml_model/
   
   # Verify model file integrity
   python -c "import tensorflow as tf; tf.keras.models.load_model('app/ml_model/hydrogen_ann_baseline.keras')"
   ```

2. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats predict-service
   ```

3. **Authentication Errors**
   ```bash
   # Verify JWT_SECRET matches auth service
   echo $JWT_SECRET
   ```

4. **Dependency Issues**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt --force-reinstall
   ```
