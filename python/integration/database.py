import sqlite3
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("RAILWAY_AI_DB_PATH", "railway.db")

class DatabaseManager:
    """Manages SQLite database connections and schema."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    hashed_password TEXT NOT NULL,
                    privilege TEXT DEFAULT 'normal',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    terms_accepted_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # API Keys table (linked to users)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    tier TEXT DEFAULT 'free',
                    credits INTEGER DEFAULT -1,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Verification codes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS verification_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    code TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # SMTP Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smtp_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1), -- Only one configuration possible
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    username TEXT,
                    password TEXT,
                    sender_email TEXT NOT NULL,
                    use_tls BOOLEAN DEFAULT 1,
                    is_active BOOLEAN DEFAULT 0
                )
            ''')
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

            # Migration: add columns if they don't exist
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT UNIQUE")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN privilege TEXT DEFAULT 'normal'")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute("ALTER TABLE api_keys ADD COLUMN expires_at TIMESTAMP")
                conn.commit()
            except sqlite3.OperationalError:
                pass

    def execute(self, query: str, params: tuple = ()) -> Optional[int]:
        """Execute a write query and return the last row ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row as a dictionary."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows as a list of dictionaries."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

# Global instance
db = DatabaseManager()
