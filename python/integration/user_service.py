import secrets
import bcrypt
from typing import Optional, Dict, Any
from python.integration.database import db
import logging

logger = logging.getLogger(__name__)

class UserService:
    """Service for user management and password security."""

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password using bcrypt."""
        # bcrypt requires bytes
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hash."""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def create_user(username: str, password: str, is_active: int = 1) -> bool:
        """Create a new user with hashed password."""
        hashed = UserService.get_password_hash(password)
        try:
            db.execute(
                "INSERT INTO users (username, hashed_password, is_active) VALUES (?, ?, ?)",
                (username, hashed, is_active)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return False

    @staticmethod
    def set_user_status(username: str, is_active: bool) -> bool:
        """Attiva o disattiva un utente."""
        try:
            db.execute(
                "UPDATE users SET is_active = ? WHERE username = ?",
                (1 if is_active else 0, username)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update status for {username}: {e}")
            return False

    @staticmethod
    def update_password(username: str, new_password: str) -> bool:
        """Aggiorna la password di un utente."""
        hashed = UserService.get_password_hash(new_password)
        try:
            db.execute(
                "UPDATE users SET hashed_password = ? WHERE username = ?",
                (hashed, username)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update password for {username}: {e}")
            return False

    @staticmethod
    def get_user(username: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by username."""
        return db.fetch_one("SELECT * FROM users WHERE username = ?", (username,))

    @staticmethod
    def generate_api_key(username: str, tier: str = "free") -> Optional[str]:
        """Generate and persist a new API Key for a user."""
        user = UserService.get_user(username)
        if not user:
            return None
            
        new_key = f"rw-{secrets.token_urlsafe(24)}"
        try:
            db.execute(
                "INSERT INTO api_keys (key, user_id, tier) VALUES (?, ?, ?)",
                (new_key, user['id'], tier)
            )
            return new_key
        except Exception as e:
            logger.error(f"Failed to generate API Key for {username}: {e}")
            return None

    @staticmethod
    def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API Key and return associated user and metadata."""
        query = """
            SELECT u.username, ak.tier, ak.credits, ak.is_active
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE ak.key = ? AND ak.is_active = 1 AND u.is_active = 1
        """
        return db.fetch_one(query, (api_key,))

    @staticmethod
    def list_users() -> list:
        """Restituisce la lista di tutti gli utenti."""
        return db.fetch_all("SELECT username, is_active FROM users")

    @staticmethod
    def delete_user(username: str) -> bool:
        """Rimuove un utente dal sistema."""
        try:
            db.execute("DELETE FROM users WHERE username = ?", (username,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {username}: {e}")
            return False
