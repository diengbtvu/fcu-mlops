# GitHub Actions CI Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Repository                            │
│                  (nguyenhuuluan1702/PCS_MLops)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Event Triggers:
                         │ • Pull Request → main/dev
                         │ • Push → main/dev
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           GitHub Actions Runner (Ubuntu Latest)                  │
└─────────────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┬────────────────┐
         │               │               │                │
         ▼               ▼               ▼                ▼
┌────────────────┐ ┌────────────────┐ ┌────────────┐ ┌──────────────┐
│  Job 1         │ │  Job 2         │ │  Job 3     │ │  Job 4       │
│  🐘 Laravel    │ │  🐍 Python/ML  │ │  🐳 Docker │ │  🔒 Security │
│  Tests         │ │  Tests         │ │  Build     │ │  Scanning    │
└────────────────┘ └────────────────┘ └────────────┘ └──────────────┘
         │               │               │                │
         │               │               │                │
         ▼               ▼               ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Job 5: 📋 Build Summary                       │
│              (Runs after all jobs complete)                      │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Status Report                               │
│  ✅ Success → Allow merge                                        │
│  ❌ Failure → Block merge                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Job 1: 🐘 Laravel Tests (2-3 minutes)

```
Setup PHP 8.2
     │
     ├─→ Install extensions (mbstring, xml, pdo_sqlite...)
     │
     ▼
Cache Composer Dependencies
     │
     ├─→ Check cache key: composer.lock hash
     │
     ▼
Install Dependencies
     │
     ├─→ composer install --optimize-autoloader
     │
     ▼
Setup Environment
     │
     ├─→ Copy .env.example → .env
     ├─→ php artisan key:generate
     │
     ▼
Setup Database
     │
     ├─→ Create SQLite database
     ├─→ Run migrations
     │
     ▼
Run PHPUnit Tests
     │
     ├─→ php artisan test --coverage --min=70
     │
     ▼
Check Code Style
     │
     ├─→ Laravel Pint --test
     │
     ▼
Upload Coverage Report
     │
     └─→ Artifact: laravel-coverage
```

## Job 2: 🐍 Python/ML Tests (1-2 minutes)

```
Setup Python 3.11
     │
     ├─→ Cache pip packages
     │
     ▼
Install Dependencies
     │
     ├─→ pip install -r requirements.txt
     ├─→ pip install pytest flake8 black isort safety
     │
     ▼
Lint with Flake8
     │
     ├─→ Check syntax errors (E9, F63, F7, F82)
     ├─→ Check code quality (complexity, line length)
     │
     ▼
Check Formatting
     │
     ├─→ Black --check --diff
     ├─→ isort --check-only
     │
     ▼
Validate ML Libraries
     │
     ├─→ Test TensorFlow import
     ├─→ Test Flask import
     ├─→ Test Pandas/NumPy import
     │
     ▼
Security Check
     │
     ├─→ safety check --json
     │
     ▼
Run Pytest
     │
     ├─→ pytest tests/ -v --cov=app
     │
     ▼
Upload Coverage Report
     │
     └─→ Artifact: python-coverage
```

## Job 3: 🐳 Docker Build Test (3-4 minutes)

```
Setup Docker Buildx
     │
     ▼
Build Laravel Image
     │
     ├─→ Context: ./WebApp
     ├─→ File: ./WebApp/dockerfile
     ├─→ Tag: laravel-webapp:test
     ├─→ Use GitHub Actions cache
     │
     ▼
Build Predict Service Image
     │
     ├─→ Context: ./predict-service
     ├─→ File: ./predict-service/dockerfile
     ├─→ Tag: predict-service:test
     ├─→ Use GitHub Actions cache
     │
     ▼
Validate Docker Compose
     │
     └─→ docker-compose config
```

## Job 4: 🔒 Security Scanning (1-2 minutes)

```
PHP Security Audit
     │
     ├─→ Setup PHP 8.2
     ├─→ composer install
     ├─→ composer audit --format=plain
     │   └─→ Check for CVE in PHP packages
     │
     ▼
Python Security Check
     │
     ├─→ Setup Python 3.11
     ├─→ pip install safety
     ├─→ safety check --json
     │   └─→ Check for CVE in Python packages
     │
     ▼
Report Vulnerabilities
     │
     └─→ Continue on error (warnings only)
```

## Job 5: 📋 Build Summary

```
Wait for all jobs to complete
     │
     ├─→ Laravel Tests: ✅/❌
     ├─→ Python Tests: ✅/❌
     ├─→ Docker Build: ✅/❌
     ├─→ Security Scan: ✅/❌
     │
     ▼
Generate Summary Table
     │
     ├─→ Create Markdown table
     ├─→ Add to GitHub Step Summary
     │
     ▼
Determine Final Status
     │
     ├─→ If any job failed → Exit 1 (Block merge)
     └─→ If all passed → Exit 0 (Allow merge)
```

## Event Flow Example

### Scenario: Developer creates Pull Request

```
1. Developer: git push origin feature/new-feature
                    │
                    ▼
2. Developer: Create PR on GitHub
                    │
                    ▼
3. GitHub: Trigger CI workflow
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
Laravel Tests   Python Tests   Docker Build   Security Scan
    │               │               │               │
    ├─ Setup        ├─ Setup        ├─ Setup        ├─ Setup
    ├─ Test         ├─ Lint         ├─ Build        ├─ Audit
    ├─ Style        ├─ Test         ├─ Validate     ├─ Check
    │               │               │               │
    ▼               ▼               ▼               ▼
   ✅              ✅              ✅              ⚠️
                    │
                    ▼
4. Build Summary: Generate report
                    │
                    ▼
5. GitHub PR: Show status
                    │
                    ├─→ ✅ All checks passed
                    │   └─→ Enable "Merge" button
                    │
                    └─→ ❌ Some checks failed
                        └─→ Block merge, show errors
```

## Cache Strategy

```
┌─────────────────────────────────────┐
│     First Run (No Cache)             │
├─────────────────────────────────────┤
│ • Download all Composer packages    │
│ • Download all pip packages         │
│ • Docker build from scratch         │
│ Time: ~10-12 minutes                │
└─────────────────────────────────────┘
                │
                ├─→ Save to GitHub Actions cache
                │
                ▼
┌─────────────────────────────────────┐
│  Subsequent Runs (With Cache)        │
├─────────────────────────────────────┤
│ • Restore Composer from cache       │
│ • Restore pip from cache            │
│ • Docker build from cache layers    │
│ Time: ~5-7 minutes (50% faster!)    │
└─────────────────────────────────────┘
                │
                ├─→ Cache invalidated if:
                │   • composer.lock changed
                │   • requirements.txt changed
                │   • Dockerfile changed
                │
                └─→ Rebuild cache
```

## Resource Usage

```
GitHub Actions Free Tier: 2000 minutes/month

Per Workflow Run:
├─ Laravel Tests:     2-3 min
├─ Python Tests:      1-2 min
├─ Docker Build:      3-4 min
├─ Security Scan:     1-2 min
└─ Build Summary:     <1 min
────────────────────────────
Total:                8-12 min per run

Monthly Capacity:
• With average 8 min/run: ~250 runs/month
• With average 10 min/run: ~200 runs/month

Typical Usage:
• 10 PRs/week × 3 commits each = 30 runs/week
• 4 direct pushes/week = 4 runs/week
• Total: ~136 runs/month
• Remaining: ~64 runs spare capacity
```

## Parallel vs Sequential Execution

```
Without Parallelization (Sequential):
Laravel → Python → Docker → Security
2 min     1 min    3 min    1 min
─────────────────────────────────────
Total: 7 minutes

With Parallelization (Current):
┌─ Laravel (2 min) ─┐
├─ Python (1 min)  ─┤
├─ Docker (3 min)  ─┤→ Build Summary
└─ Security (1 min)─┘
─────────────────────────
Total: 3 minutes (max of all jobs)

Time Saved: 4 minutes (57% faster!)
```

## Status Badges

```
In README.md:

[![CI](https://github.com/.../workflows/ci.yml/badge.svg)]()
      │                           │                     │
      │                           │                     └─→ Link to Actions
      │                           └─────────────────────→ Workflow file
      └─────────────────────────────────────────────────→ Badge image

Badge Colors:
• 🟢 passing  - All jobs succeeded
• 🔴 failing  - One or more jobs failed
• 🟡 running  - Workflow in progress
• ⚪ no status - Workflow not run yet
```
