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
    def create_user(username: str, password: str, privilege: str = "normal", is_active: int = 1, email: str = None) -> bool:
        """Create a new user with hashed password and privilege level."""
        hashed = UserService.get_password_hash(password)
        try:
            db.execute(
                "INSERT INTO users (username, hashed_password, privilege, is_active, email) VALUES (?, ?, ?, ?, ?)",
                (username, hashed, privilege, is_active, email)
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
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by email."""
        return db.fetch_one("SELECT * FROM users WHERE email = ?", (email,))

    @staticmethod
    def store_verification_code(email: str, username: str, password_hash: str, code: str) -> bool:
        """Store a verification code in the database."""
        from datetime import datetime, timedelta
        expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        try:
            # Rimuovi eventuali codici precedenti per la stessa email
            db.execute("DELETE FROM verification_codes WHERE email = ?", (email,))
            db.execute(
                "INSERT INTO verification_codes (email, username, password_hash, code, expires_at) VALUES (?, ?, ?, ?, ?)",
                (email, username, password_hash, code, expires_at)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store verification code for {email}: {e}")
            return False

    @staticmethod
    def verify_code_and_register(email: str, code: str) -> Optional[str]:
        """Verify code and create user if valid. Returns username on success."""
        from datetime import datetime
        record = db.fetch_one("SELECT * FROM verification_codes WHERE email = ? AND code = ?", (email, code))
        if not record:
            return None
        
        # Controlla scadenza
        try:
            expiry = datetime.fromisoformat(record['expires_at'])
            if datetime.utcnow() > expiry:
                db.execute("DELETE FROM verification_codes WHERE email = ?", (email,))
                return None
        except Exception:
            return None

        # Crea l'utente
        try:
            db.execute(
                "INSERT INTO users (username, hashed_password, email, privilege, is_active) VALUES (?, ?, ?, ?, ?)",
                (record['username'], record['password_hash'], record['email'], 'normal', 1)
            )
            # Pulisci i codici
            db.execute("DELETE FROM verification_codes WHERE email = ?", (email,))
            return record['username']
        except Exception as e:
            logger.error(f"Failed to finalize registration for {record['username']}: {e}")
            return None

    @staticmethod
    def generate_api_key(username: str, tier: str = "free", days: int = 60) -> Optional[str]:
        """Generate and persist a new API Key for a user with expiry."""
        from datetime import datetime, timedelta
        user = UserService.get_user(username)
        if not user:
            return None
            
        new_key = f"rw-{secrets.token_urlsafe(24)}"
        expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
        
        try:
            db.execute(
                "INSERT INTO api_keys (key, user_id, tier, expires_at) VALUES (?, ?, ?, ?)",
                (new_key, user['id'], tier, expires_at)
            )
            return new_key
        except Exception as e:
            logger.error(f"Failed to generate API Key for {username}: {e}")
            return None

    @staticmethod
    def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API Key and return associated user and metadata."""
        from datetime import datetime
        query = """
            SELECT u.username, u.privilege, ak.tier, ak.credits, ak.is_active, ak.expires_at
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE ak.key = ? AND ak.is_active = 1 AND u.is_active = 1
        """
        key_data = db.fetch_one(query, (api_key,))
        
        if key_data and key_data['expires_at']:
            try:
                expiry = datetime.fromisoformat(key_data['expires_at'])
                if datetime.utcnow() > expiry:
                    logger.warning(f"API Key {api_key[:8]}... has expired.")
                    return None
            except Exception as e:
                logger.error(f"Error checking key expiry: {e}")
                
        return key_data

    @staticmethod
    def get_key_info(api_key: str) -> Optional[Dict[str, Any]]:
        """Returns details about the API Key, including remaining life."""
        from datetime import datetime
        query = """
            SELECT ak.key, ak.expires_at, ak.created_at, u.username, u.privilege
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE ak.key = ?
        """
        data = db.fetch_one(query, (api_key,))
        if not data:
            return None
            
        remaining_days = -1
        if data['expires_at']:
            try:
                expiry = datetime.fromisoformat(data['expires_at'])
                delta = expiry - datetime.utcnow()
                remaining_days = round(delta.total_seconds() / (24 * 3600), 2)
            except Exception:
                pass
                
        return {
            "key_prefix": data['key'][:8] + "...",
            "username": data['username'],
            "privilege": data['privilege'],
            "expires_at": data['expires_at'],
            "remaining_days": max(0, remaining_days)
        }

    @staticmethod
    def list_users() -> list:
        """Restituisce la lista di tutti gli utenti."""
        return db.fetch_all("SELECT username, privilege, is_active FROM users")

    @staticmethod
    def delete_user(username: str) -> bool:
        """Rimuove un utente dal sistema."""
        try:
            db.execute("DELETE FROM users WHERE username = ?", (username,))
            return True
        except Exception as e:
            logger.error(f"Failed to delete user {username}: {e}")
            return False

    @staticmethod
    def get_smtp_settings() -> Optional[Dict[str, Any]]:
        """Retrieve the current SMTP configuration."""
        return db.fetch_one("SELECT * FROM smtp_settings WHERE id = 1")

    @staticmethod
    def update_smtp_settings(settings: Dict[str, Any]) -> bool:
        """Update or create the SMTP configuration."""
        try:
            current = UserService.get_smtp_settings()
            if current:
                db.execute(
                    """UPDATE smtp_settings SET 
                       host=?, port=?, username=?, password=?, sender_email=?, use_tls=?, is_active=? 
                       WHERE id = 1""",
                    (settings['host'], settings['port'], settings['username'], 
                     settings['password'], settings['sender_email'], 
                     1 if settings.get('use_tls') else 0, 1 if settings.get('is_active') else 0)
                )
            else:
                db.execute(
                    """INSERT INTO smtp_settings 
                       (id, host, port, username, password, sender_email, use_tls, is_active) 
                       VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
                    (settings['host'], settings['port'], settings['username'], 
                     settings['password'], settings['sender_email'], 
                     1 if settings.get('use_tls') else 0, 1 if settings.get('is_active') else 0)
                )
            return True
        except Exception as e:
            logger.error(f"Failed to update SMTP settings: {e}")
            return False

    @staticmethod
    async def send_email(subject: str, recipient: str, body: str):
        """Send an email using configured SMTP settings."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        config = UserService.get_smtp_settings()
        if not config or not config.get('is_active'):
            # Fallback a simulazione
            with open("registrations.log", "a") as f:
                f.write(f"[{datetime.now().isoformat() if 'datetime' in locals() else 'NOW'}] [SIMULATED EMAIL] To: {recipient}, Subject: {subject}, Body: {body}\n")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = config['sender_email']
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(config['host'], config['port'])
            if config.get('use_tls'):
                server.starttls()
            
            if config.get('username') and config.get('password'):
                server.login(config['username'], config['password'])
            
            server.send_message(msg)
            server.quit()
        except Exception as e:
            logger.error(f"SMTP Error: {e}")
            raise e
