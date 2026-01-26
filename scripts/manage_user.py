import sys
import os
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.integration.user_service import UserService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/manage_user.py <username> <activate|deactivate>")
        return

    username = sys.argv[1]
    action = sys.argv[2].lower()

    user = UserService.get_user(username)
    if not user:
        print(f"Error: User '{username}' not found.")
        return

    if action == "activate":
        success = UserService.set_user_status(username, True)
        status_str = "ACTIVATED"
    elif action == "deactivate":
        success = UserService.set_user_status(username, False)
        status_str = "DEACTIVATED"
    else:
        print(f"Error: Unknown action '{action}'. Use 'activate' or 'deactivate'.")
        return

    if success:
        print(f"✓ User '{username}' has been successfully {status_str}.")
    else:
        print(f"✗ Failed to update status for user '{username}'.")

if __name__ == "__main__":
    main()
