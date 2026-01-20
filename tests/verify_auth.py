import requests
import json
import time

BASE_URL = "http://localhost:8002"

def test_auth():
    print("--- Testing Authentication ---")
    
    # 1. Test access without token
    print("\n1. Testing access without token (should fail with 401)...")
    try:
        response = requests.get(f"{BASE_URL}/api/v2/health")
        print(f"Health check status: {response.status_code}")
        
        # Optimize endpoint should fail
        response = requests.post(f"{BASE_URL}/api/v2/optimize", json={"conflicts": [], "network": {"stations": []}})
        print(f"Optimize status (no token): {response.status_code}")
        if response.status_code == 401:
            print("✅ Success: Correctly denied access.")
        else:
            print("❌ Failure: Should have been 401.")
    except Exception as e:
        print(f"Error: {e}. Is the server running?")

    # 2. Get token
    print("\n2. Getting token with correct credentials (admin/admin)...")
    try:
        response = requests.post(
            f"{BASE_URL}/token", 
            data={"username": "admin", "password": "admin"}
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ Success: Got token.")
        else:
            print(f"❌ Failure: {response.status_code} - {response.text}")
            return
            
        # 3. Test access with token
        print("\n3. Testing access with valid token...")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test optimization request
        payload = {
            "conflicts": [
                {
                    "conflict_type": "platform_conflict",
                    "location": "MONZA",
                    "trains": [
                        {"train_id": "IC101", "priority": 10},
                        {"train_id": "R203", "priority": 5}
                    ],
                    "severity": "high"
                }
            ],
            "network": {
                "stations": ["MONZA"],
                "available_platforms": {"MONZA": [1, 2]},
                "max_speeds": {}
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/v2/optimize", json=payload, headers=headers)
        if response.status_code == 200:
            print("✅ Success: Optimization query successful.")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Failure: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # In a real scenario, we would start the server here
    print("Please ensure the FastAPI server is running on port 8002.")
    print("Run: python api/fdc_integration_api.py")
    test_auth()
