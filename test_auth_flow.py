import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_user_flow():
    # 1. Bootstrapping (Done automatically on server start)
    # 2. Login as admin to get the 60-day key
    print("Logging in as admin...")
    response = requests.post(f"{BASE_URL}/token", data={"username": "admin", "password": "admin"})
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return
    
    admin_data = response.json()
    admin_key = admin_data["access_token"]
    print(f"Admin Key: {admin_key[:10]}...")
    
    headers = {"X-API-Key": admin_key}
    
    # 3. Check Admin Key Info
    print("\nChecking key info...")
    response = requests.get(f"{BASE_URL}/api/v1/key-info", headers=headers)
    print(f"Key Info: {json.dumps(response.json(), indent=2)}")
    
    # 4. Create a new 'normal' user
    new_user = "test_user_" + str(int(time.time()))
    print(f"\nCreating new user '{new_user}'...")
    response = requests.post(
        f"{BASE_URL}/api/v1/admin/users", 
        headers=headers, 
        json={"username": new_user, "password": "password123", "privilege": "normal"}
    )
    print(f"Create User Response: {response.json()}")
    
    # 5. Login as the new user
    print(f"\nLogging in as '{new_user}'...")
    response = requests.post(f"{BASE_URL}/token", data={"username": new_user, "password": "password123"})
    user_data = response.json()
    user_key = user_data["access_token"]
    user_headers = {"X-API-Key": user_key}
    
    # 6. Try to perform admin action as normal user
    print("\nAttempting admin action as normal user (should fail)...")
    response = requests.get(f"{BASE_URL}/api/v1/admin/users", headers=user_headers)
    print(f"Admin List Status: {response.status_code} (Expected 403)")
    if response.status_code == 403:
        print("Success: Access denied as expected.")
    
    # 7. Check normal user key info
    print("\nChecking normal user key info...")
    response = requests.get(f"{BASE_URL}/api/v1/key-info", headers=user_headers)
    print(f"Key Info: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    # Note: Requires server to be running on localhost:8000
    print("Ensure the server is running with: python -m api.server")
    # test_user_flow()
