"""
Database utility functions for interacting with Laravel backend
"""
import requests
import os
from datetime import datetime
import json
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class DatabaseUtils:
    """Utility class for database operations with Laravel backend"""
    
    def __init__(self):
        # Get Laravel API base URL from environment or default
        self.laravel_api_base = os.getenv('LARAVEL_API_URL', 'http://127.0.0.1:8000/api')
        self.timeout = 30  # Reasonable timeout for normal operations
        self.max_retries = 3
        
        # DEBUG: Print Laravel API base URL
        print(f"🔧 DatabaseUtils initialized")
        print(f"   Laravel API Base: {self.laravel_api_base}")
        print(f"   Timeout: {self.timeout}s")
        print(f"   Max Retries: {self.max_retries}")
        
        # Create a session for connection pooling and better performance
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Connection': 'close'
        })
        
    def test_connection(self):
        """
        Test connection to Laravel API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print(f"🔗 Testing connection to {self.laravel_api_base}...")
            
            response = self.session.get(
                f'{self.laravel_api_base}/health',
                timeout=5  # Quick test with 5 seconds timeout
            )
            
            if response.status_code == 200:
                print(f"✅ Connection to Laravel API successful!")
                return True
            else:
                print(f"❌ Laravel API returned status {response.status_code}")
                return False
                
        except requests.exceptions.Timeout as e:
            print(f"⚠️ Laravel API health check timeout (5s)")
            print(f"   This is OK - Laravel might be busy processing requests")
            print(f"   Will attempt to save model anyway...")
            return True  # Return True to proceed with save attempt
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Cannot connect to Laravel API: Connection refused")
            print(f"   Make sure Laravel is running on {self.laravel_api_base}")
            print(f"   Error details: {str(e)}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"❌ Cannot connect to Laravel API: Timeout after 15 seconds")
            print(f"   Laravel may be overloaded or not responding")
            print(f"   Tried to connect to: {self.laravel_api_base}/health")
            print(f"   Error details: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Cannot connect to Laravel API: {str(e)}")
            print(f"   Exception type: {type(e).__name__}")
            return False
    
    def save_ml_model_to_db(self, model_info):
        """
        Save ML model information to Laravel database
        
        Args:
            model_info (dict): Dictionary containing model information
                Required keys:
                - MLMName: Model name
                - FilePath: Relative path to model file
                - LibType: Library type (sklearn, keras, etc.)
                - MSEValue: Mean Squared Error
                - MAEValue: Mean Absolute Error
                - TrainedBy: User ID who trained the model
                - DatasetId: Dataset ID used for training (optional)
        
        Returns:
            dict: Response from Laravel API or None if failed
        """
        import time
        
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"🔄 Retry attempt {attempt + 1}/{max_retries}...")
                    time.sleep(retry_delay)
                
                # Prepare the payload - FIXED: Use snake_case for MLflow fields
                payload = {
                    'MLMName': model_info.get('MLMName'),
                    'FilePath': model_info.get('FilePath'),
                    'LibType': model_info.get('LibType', 'sklearn'),
                    'IsActive': model_info.get('IsActive', True),
                    'MSEValue': model_info.get('MSEValue'),
                    'MAEValue': model_info.get('MAEValue'),
                    'R2Value': model_info.get('R2Value'),
                    'RMSEValue': model_info.get('RMSEValue'),
                    'mlflow_run_id': model_info.get('mlflow_run_id'),  # FIXED: snake_case
                    'mlflow_experiment_id': model_info.get('mlflow_experiment_id'),  # FIXED: snake_case
                    'gra_ranking': model_info.get('gra_ranking'),
                    'training_report': model_info.get('training_report'),
                    'TrainedBy': model_info.get('TrainedBy', 1),  # Default to admin user ID 1
                    'DatasetId': model_info.get('DatasetId'),
                    'CreatedDate': datetime.now().isoformat(),
                    'UpdatedDate': datetime.now().isoformat()
                }
                
                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}
                
                if attempt == 0:  # Only print detailed info on first attempt
                    print(f"🔄 Saving model info to database...")
                    print(f"   URL: {self.laravel_api_base}/ml-models")
                    print(f"   Payload keys: {list(payload.keys())}")
                    print(f"   Payload: {json.dumps(payload, indent=2)}")
                
                # Make API request to Laravel
                headers = {
                    'Content-Type': 'application/json',
                }
                
                # Add authentication if token is available
                auth_token = model_info.get('auth_token')
                if auth_token:
                    headers['Authorization'] = f'Bearer {auth_token}'
                    if attempt == 0:
                        print(f"   Auth token: {auth_token[:20]}..." if len(auth_token) > 20 else f"   Auth token: {auth_token}")
                
                response = self.session.post(
                    f'{self.laravel_api_base}/ml-models',
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 201 or response.status_code == 200:
                    result = response.json()
                    print(f"✅ Model saved to database successfully!")
                    print(f"   Model ID: {result.get('data', {}).get('id', 'N/A')}")
                    return result
                else:
                    print(f"❌ Failed to save model to database. Status: {response.status_code}")
                    print(f"   Response: {response.text}")
                    print(f"   Request URL: {self.laravel_api_base}/ml-models")
                    try:
                        error_data = response.json()
                        print(f"   Error details: {json.dumps(error_data, indent=2)}")
                    except:
                        pass
                    if attempt == max_retries - 1:  # Last attempt
                        return None
                    continue
                    
            except requests.exceptions.Timeout as e:
                error_msg = f"⏰ Timeout error (attempt {attempt + 1}/{max_retries}): Request exceeded {self.timeout}s"
                print(error_msg)
                print(f"   Endpoint: {self.laravel_api_base}/ml-models")
                print(f"   Suggestion: Check if Laravel is responsive or increase timeout in .env")
                if attempt == max_retries - 1:  # Last attempt
                    print(f"❌ Failed to save model after {max_retries} attempts due to timeout")
                    return None
            except requests.exceptions.RequestException as e:
                print(f"🌐 Network error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    print(f"❌ Failed to save model after {max_retries} attempts due to network error")
                    return None
            except Exception as e:
                print(f"❌ Unexpected error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    return None
        
        return None
    
    def update_model_status(self, model_id, is_active=True):
        """
        Update model active status in database
        
        Args:
            model_id (int): Model ID to update
            is_active (bool): Whether model should be active
            
        Returns:
            bool: Success status
        """
        try:
            payload = {
                'IsActive': is_active,
                'UpdatedDate': datetime.now().isoformat()
            }
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            response = self.session.put(
                f'{self.laravel_api_base}/ml-models/{model_id}',
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                print(f"✅ Model {model_id} status updated to active={is_active}")
                return True
            else:
                print(f"❌ Failed to update model status. Status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating model status: {str(e)}")
            return False

    def get_active_model(self):
        """
        Get currently active model from database
        
        Returns:
            dict: Active model information or None
        """
        try:
            headers = {
                'Content-Type': 'application/json',
            }
            
            response = self.session.get(
                f'{self.laravel_api_base}/ml-models/active',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('data')
            else:
                print(f"❌ Failed to get active model. Status: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting active model: {str(e)}")
            return None
