import sys
import os
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.integration.user_service import UserService
from python.integration.database import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset():
    username = "admin"
    password = "admin123"
    
    print(f"Resetting user: {username}")
    
    user = UserService.get_user(username)
    if user:
        # Update existing user
        from python.integration.user_service import UserService
        hashed = UserService.get_password_hash(password)
        db.execute(
            "UPDATE users SET hashed_password = ?, is_active = 1 WHERE username = ?",
            (hashed, username)
        )
        print(f"✓ User {username} updated and activated.")
    else:
        # Create new user
        success = UserService.create_user(username, password, is_active=1)
        if success:
            print(f"✓ User {username} created and activated.")
        else:
            print(f"✗ Failed to create user {username}.")
            sys.exit(1)

    print(f"Credentials set to: {username} / {password}")

if __name__ == "__main__":
    reset()
