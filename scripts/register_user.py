import requests
import sys

def register(username, password):
    url = "http://localhost:8002"
    
    print(f"1. Login as admin...")
    try:
        resp = requests.post(f"{url}/token", data={"username": "admin", "password": "admin123"})
        if resp.status_code != 200:
            print(f"Error login: {resp.status_code} - {resp.text}")
            return
        
        token = resp.json()["access_token"]
        print(f"   ✓ Authenticated.")

        print(f"\n2. Registering {username}...")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "username": username,
            "password": password
        }
        
        resp = requests.post(f"{url}/api/v1/register", json=data, headers=headers)
        if resp.status_code in [200, 201]:
            print(f"   ✓ Success! {resp.json().get('message')}")
        else:
            print(f"   ✗ Failed: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/register_user.py <username> <password>")
    else:
        register(sys.argv[1], sys.argv[2])
