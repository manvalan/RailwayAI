import sys
import os
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.integration.user_service import UserService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize():
    print("=" * 60)
    print("Railway AI - Database Initialization")
    print("=" * 60)
    
    username = "admin"
    password = os.getenv("RAILWAY_ADMIN_PASSWORD", "admin123")
    
    print(f"Creating initial user: {username}")
    
    if UserService.get_user(username):
        print(f"User {username} already exists. Skipping.")
    else:
        success = UserService.create_user(username, password)
        if success:
            print(f"✓ User {username} created successfully.")
            print(f"  Password: {password}")
        else:
            print(f"✗ Failed to create user {username}.")
            sys.exit(1)

    print("\nInitialization complete.")
    print("=" * 60)

if __name__ == "__main__":
    initialize()
