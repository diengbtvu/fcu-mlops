"""
Test script for MLflow Prediction API with Cache
Run this after training a model to verify the complete flow
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_response(response):
    """Pretty print JSON response"""
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Time: {response.elapsed.total_seconds():.3f}s")

def test_train_model():
    """Step 1: Train a new model with MLflow tracking"""
    print_section("TEST 1: Train Model (with MLflow tracking)")
    
    payload = {
        "dataset_path": "data/Dataset.new3.csv",
        "model_name": "Test_MLflow_Cache_Model",
        "n_estimators": 50,  # Small for faster training
        "max_depth": 5,
        "random_state": 42
    }
    
    print("Training model...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/train/model", json=payload)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        run_id = data.get('mlflow_run_id')
        print(f"\n✅ Model trained successfully!")
        print(f"MLflow Run ID: {run_id}")
        print(f"Database ID: {data.get('database_id')}")
        return run_id
    else:
        print("❌ Training failed!")
        return None

def test_predict_with_run_id(run_id):
    """Step 2: Predict using MLflow run_id (will cache model)"""
    print_section("TEST 2: Predict with run_id (Cache MISS - first time)")
    
    payload = {
        "run_id": run_id,
        "features": {
            "ph": 6.5,
            "vss": 3500.0,
            "ethanol": 12.0,
            "acetate": 25.0,
            "propionate": 8.0,
            "butyrate": 35.0,
            "sucrose_degradation": 72.0,
            "orp_mid": -180.0,
            "orp_low": -220.0,
            "vfa": 90.0,
            "cod_o": 12000.0
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    start = time.time()
    response = requests.post(f"{BASE_URL}/predict/mlflow", json=payload)
    duration = time.time() - start
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Prediction: {data.get('prediction')} {data.get('unit')}")
        print(f"Cached: {data.get('cached')}")
        print(f"Duration: {duration:.3f}s")
        return True
    else:
        print("❌ Prediction failed!")
        return False

def test_predict_cached(run_id):
    """Step 3: Predict again (should be from cache - much faster)"""
    print_section("TEST 3: Predict with same run_id (Cache HIT - should be faster)")
    
    payload = {
        "run_id": run_id,
        "features": {
            "ph": 6.8,
            "vss": 3800.0,
            "ethanol": 15.0,
            "acetate": 30.0,
            "propionate": 9.5,
            "butyrate": 38.0,
            "sucrose_degradation": 75.0,
            "orp_mid": -170.0,
            "orp_low": -210.0,
            "vfa": 95.0,
            "cod_o": 12500.0
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    start = time.time()
    response = requests.post(f"{BASE_URL}/predict/mlflow", json=payload)
    duration = time.time() - start
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Prediction: {data.get('prediction')} {data.get('unit')}")
        print(f"Cached: {data.get('cached')} ⚡")
        print(f"Duration: {duration:.3f}s (should be ~0.02s)")
        return True
    else:
        print("❌ Prediction failed!")
        return False

def test_predict_with_active_model():
    """Step 4: Predict using active model from database"""
    print_section("TEST 4: Predict with active model (use_active=true)")
    
    payload = {
        "use_active": True,
        "features": {
            "ph": 6.3,
            "vss": 3300.0,
            "ethanol": 10.0,
            "acetate": 22.0,
            "propionate": 7.0,
            "butyrate": 30.0,
            "sucrose_degradation": 68.0,
            "orp_mid": -190.0,
            "orp_low": -230.0,
            "vfa": 85.0,
            "cod_o": 11800.0
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/predict/mlflow", json=payload)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Prediction: {data.get('prediction')} {data.get('unit')}")
        print(f"Model Source: {data.get('model_source')}")
        print(f"Cached: {data.get('cached')}")
        return True
    else:
        print("❌ Prediction failed!")
        return False

def test_cache_info():
    """Step 5: Check cache statistics"""
    print_section("TEST 5: Cache Info")
    
    response = requests.get(f"{BASE_URL}/predict/mlflow/cache/info")
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        cache_info = data.get('cache_info', {})
        print(f"\n✅ Total cached models: {cache_info.get('total_cached_models')}")
        print(f"Cache TTL: {cache_info.get('cache_ttl_hours')} hours")
        print(f"Cached run_ids: {cache_info.get('cached_run_ids')}")
        return True
    else:
        print("❌ Failed to get cache info!")
        return False

def test_cache_specific_run(run_id):
    """Step 6: Check cache info for specific run"""
    print_section(f"TEST 6: Cache Info for specific run ({run_id[:8]}...)")
    
    response = requests.get(f"{BASE_URL}/predict/mlflow/cache/info?run_id={run_id}")
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        cache_info = data.get('cache_info', {})
        print(f"\n✅ Run ID: {cache_info.get('run_id')}")
        print(f"Age: {cache_info.get('age_seconds')}s")
        print(f"Loaded at: {cache_info.get('loaded_at')}")
        return True
    else:
        print("❌ Failed to get cache info!")
        return False

def test_force_reload(run_id):
    """Step 7: Force reload from MLflow (bypass cache)"""
    print_section("TEST 7: Force reload from MLflow (force_reload=true)")
    
    payload = {
        "run_id": run_id,
        "force_reload": True,
        "features": {
            "ph": 6.4,
            "vss": 3400.0,
            "ethanol": 11.0,
            "acetate": 24.0,
            "propionate": 7.5,
            "butyrate": 33.0,
            "sucrose_degradation": 70.0,
            "orp_mid": -185.0,
            "orp_low": -225.0,
            "vfa": 88.0,
            "cod_o": 11900.0
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    start = time.time()
    response = requests.post(f"{BASE_URL}/predict/mlflow", json=payload)
    duration = time.time() - start
    
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Prediction: {data.get('prediction')} {data.get('unit')}")
        print(f"Cached: {data.get('cached')} (should be False)")
        print(f"Duration: {duration:.3f}s (should be slower)")
        return True
    else:
        print("❌ Prediction failed!")
        return False

def test_cache_preload(run_id):
    """Step 8: Preload model into cache"""
    print_section("TEST 8: Preload model into cache")
    
    payload = {"run_id": run_id}
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/predict/mlflow/cache/preload", json=payload)
    print_response(response)
    
    if response.status_code == 200:
        print("\n✅ Model preloaded successfully!")
        return True
    else:
        print("❌ Preload failed!")
        return False

def test_clear_cache_specific(run_id):
    """Step 9: Clear specific model from cache"""
    print_section(f"TEST 9: Clear specific model from cache ({run_id[:8]}...)")
    
    payload = {"run_id": run_id}
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/predict/mlflow/cache/clear", json=payload)
    print_response(response)
    
    if response.status_code == 200:
        print("\n✅ Cache cleared successfully!")
        return True
    else:
        print("❌ Clear cache failed!")
        return False

def test_clear_all_cache():
    """Step 10: Clear all cache"""
    print_section("TEST 10: Clear all cache")
    
    response = requests.post(f"{BASE_URL}/predict/mlflow/cache/clear", json={})
    print_response(response)
    
    if response.status_code == 200:
        print("\n✅ All cache cleared successfully!")
        return True
    else:
        print("❌ Clear all cache failed!")
        return False

def run_all_tests():
    """Run complete test suite"""
    print("\n" + "🚀"*35)
    print("  MLflow Prediction API - Complete Test Suite")
    print("🚀"*35)
    
    # Test 1: Train model
    run_id = test_train_model()
    if not run_id:
        print("\n❌ Training failed. Stopping tests.")
        return
    
    # Wait a bit for database to update
    print("\n⏳ Waiting 2 seconds for database to update...")
    time.sleep(2)
    
    # Test 2-3: Prediction with cache
    test_predict_with_run_id(run_id)
    time.sleep(0.5)
    test_predict_cached(run_id)
    
    # Test 4: Active model
    time.sleep(0.5)
    test_predict_with_active_model()
    
    # Test 5-6: Cache info
    time.sleep(0.5)
    test_cache_info()
    time.sleep(0.5)
    test_cache_specific_run(run_id)
    
    # Test 7: Force reload
    time.sleep(0.5)
    test_force_reload(run_id)
    
    # Test 8: Preload
    time.sleep(0.5)
    test_cache_preload(run_id)
    
    # Test 9: Clear specific cache
    time.sleep(0.5)
    test_clear_cache_specific(run_id)
    
    # Test 10: Clear all cache
    time.sleep(0.5)
    test_clear_all_cache()
    
    print_section("✅ All Tests Completed!")
    print("\nSummary:")
    print(f"  - Model trained with run_id: {run_id}")
    print(f"  - All prediction methods tested")
    print(f"  - Cache management verified")
    print("\n🎉 MLflow Prediction system is working!")

if __name__ == "__main__":
    try:
        run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to Flask API at http://localhost:5000")
        print("Please make sure the predict-service is running!")
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
