---
title: Hydrogen Production Rate - Complete User Guide
---

# Hydrogen Production Rate - Complete User Guide

## 1. Introduction

The Hydrogen MLOps platform predicts Hydrogen Production Rate (HPR) from biochemical process inputs.

It includes:
- Laravel WebApp for user/admin workflows
- Python predict-service for model inference
- Docker-based local deployment
- Model management, history tracking, and role-based access control

## 2. Prediction Domain

### Input features (11)
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

### Output
- `HPR` (Hydrogen Production Rate), unit: `L/h/L`

## 3. User Roles

### Admin
- Manage users and models
- Trigger predictions
- View system-wide settings and history

### User
- Run predictions
- View own prediction history
- Manage profile and password

## 4. Quick Start (Docker)

```bash
./deploy.sh --fresh
```

Main URLs:
- WebApp: `http://localhost:52025`
- Predict API health: `http://localhost:5000/predict/health`

## 5. Web Prediction Flow

1. User/admin opens prediction page.
2. Select an active model.
3. Submit 11 features.
4. WebApp validates input ranges.
5. WebApp calls predict-service.
6. Prediction result is stored in `predictions` table with HPR.
7. History page renders result analytics.

## 6. API Summary

### `POST /predict/model`
- Requires JWT token
- Accepts 11 features + model context
- Returns predicted `HPR`

### `GET /predict/health`
- Service health endpoint

## 7. Data and Models

- Model metadata is stored in `ml_models`
- Key metrics: `MSEValue`, `MAEValue`, optional `R2Value`, `RMSEValue`
- Prediction records stored in `predictions`

## 8. Testing

### WebApp
```bash
cd WebApp
./vendor/bin/phpunit
```

### Notes
- Tests use SQLite in-memory during CI/local test execution.
- Keep language files and templates aligned with Hydrogen HPR terminology.

## 9. Operational Checklist

- Ensure at least one active model exists.
- Verify predict-service health before prediction tests.
- Keep `.env.docker` and `docker-compose.yml` values synchronized.
- Re-run tests after changing validation rules, migrations, or model I/O.

## 10. Troubleshooting

- `503 Prediction service unavailable`:
  - Check predict-service container logs.
  - Validate `PREDICT_SERVICE_URL`.
- `404 Model file not found`:
  - Ensure uploaded model path exists in `WebApp/public/models`.
  - Prefer MLflow-backed models if configured.
- Validation errors:
  - Confirm all 11 input fields are present and numeric in valid ranges.

---

For deeper implementation details, refer to:
- `README.md`
- `WebApp/README.md`
- `predict-service/README.md`
