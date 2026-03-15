"""
Test script for Laravel API connection
"""
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Import just the DatabaseUtils module directly
import requests
from datetime import datetime
import json

class DatabaseUtils:
    """Utility class for database operations with Laravel backend"""
    
    def __init__(self):
        # Get Laravel API base URL from environment or default
        self.laravel_api_base = os.getenv('LARAVEL_API_URL', 'http://127.0.0.1:8000/api')
        self.timeout = 30  # Reasonable timeout for normal operations
        self.max_retries = 3
        
    def test_connection(self):
        """
        Test connection to Laravel API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print(f"🔗 Testing connection to {self.laravel_api_base}...")
            
            headers = {
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f'{self.laravel_api_base}/health',
                headers=headers,
                timeout=10  # Shorter timeout for health check
            )
            
            if response.status_code == 200:
                print(f"✅ Connection to Laravel API successful!")
                print(f"   Response: {response.json()}")
                return True
            else:
                print(f"❌ Laravel API returned status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Cannot connect to Laravel API: Connection refused")
            print(f"   Make sure Laravel is running on {self.laravel_api_base}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"❌ Cannot connect to Laravel API: Timeout after 10 seconds")
            print(f"   Laravel may be overloaded or not responding")
            return False
        except Exception as e:
            print(f"❌ Cannot connect to Laravel API: {str(e)}")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("Laravel API Connection Test")
    print("=" * 60)
    
    # Show environment variables
    print(f"\n📋 Environment Variables:")
    print(f"   LARAVEL_API_URL: {os.getenv('LARAVEL_API_URL', 'NOT SET')}")
    print(f"   JWT_SECRET: {os.getenv('JWT_SECRET', 'NOT SET')[:20]}...")
    print(f"   MODEL_DIR: {os.getenv('MODEL_DIR', 'NOT SET')}")
    print(f"   .env file: {env_path.absolute()}")
    print(f"   .env exists: {env_path.exists()}")
    
    print("\n" + "=" * 60)
    db = DatabaseUtils()
    result = db.test_connection()
    
    print("\n" + "=" * 60)
    print(f"Test Result: {'✅ PASSED' if result else '❌ FAILED'}")
    print("=" * 60)

