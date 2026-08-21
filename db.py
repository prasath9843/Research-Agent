import sqlite3
import json
from pathlib import Path
from config import settings

def get_db_connection():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT,
        email_verified INTEGER DEFAULT 0,
        auth_provider TEXT DEFAULT 'email',
        google_id TEXT,
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT,
        query TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        stage TEXT NOT NULL DEFAULT 'initialized',
        rounds_completed INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        config_json TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS sub_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        tag TEXT NOT NULL,
        text TEXT NOT NULL,
        category TEXT,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS search_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        sub_question_id TEXT NOT NULL,
        query_text TEXT NOT NULL,
        round_num INTEGER DEFAULT 1,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        url TEXT NOT NULL,
        title TEXT,
        domain TEXT,
        domain_score REAL DEFAULT 0.5,
        relevance_score REAL DEFAULT 0.0,
        relevance_reason TEXT,
        clean_text TEXT,
        status TEXT DEFAULT 'fetched',
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        source_id INTEGER NOT NULL,
        claim_text TEXT NOT NULL,
        quote_or_paraphrase TEXT,
        sub_question_tag TEXT,
        confidence REAL DEFAULT 1.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id),
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );

    CREATE TABLE IF NOT EXISTS contradictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        topic TEXT NOT NULL,
        consensus_summary TEXT,
        conflicting_views TEXT,
        affected_source_ids TEXT,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        markdown_content TEXT NOT NULL,
        verified_citations_count INTEGER DEFAULT 0,
        total_citations_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'final',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS session_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        message TEXT NOT NULL,
        level TEXT DEFAULT 'INFO',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );

    CREATE TABLE IF NOT EXISTS email_verifications (
        email TEXT PRIMARY KEY,
        otp_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        expires_at INTEGER NOT NULL,
        resend_available_at INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS password_resets (
        email TEXT PRIMARY KEY,
        token_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        expires_at INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safe migrations for existing databases using PRAGMA inspection
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [r["name"] for r in cursor.fetchall()]
    if "email_verified" not in user_cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0;")
        except Exception:
            pass
    if "updated_at" not in user_cols:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN updated_at TEXT;")
        except Exception:
            pass

    cursor.execute("PRAGMA table_info(sessions)")
    session_cols = [r["name"] for r in cursor.fetchall()]
    if "user_id" not in session_cols:
        try:
            cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT;")
        except Exception:
            pass

    conn.commit()
    conn.close()

# --- User Account Functions ---

def create_user(user_id: str, email: str, name: str, password_hash: str = None, auth_provider: str = 'email', google_id: str = None, avatar_url: str = None, email_verified: int = 0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (id, email, name, password_hash, auth_provider, google_id, avatar_url, email_verified, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (user_id, email.lower().strip(), name.strip(), password_hash, auth_provider, google_id, avatar_url, email_verified))
    conn.commit()
    conn.close()

def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_google_id(google_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def verify_user_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET email_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

def update_user_password(email: str, password_hash: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE email = ?", (password_hash, email.lower().strip()))
    conn.commit()
    conn.close()

def link_google_account(email: str, google_id: str, avatar_url: str = None, name: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if avatar_url:
        cursor.execute("UPDATE users SET google_id = ?, avatar_url = ?, email_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE email = ?", (google_id, avatar_url, email.lower().strip()))
    else:
        cursor.execute("UPDATE users SET google_id = ?, email_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE email = ?", (google_id, email.lower().strip()))
    conn.commit()
    conn.close()

# --- Email Verification Storage ---

def save_email_verification(email: str, otp_hash: str, salt: str, expires_at: int, resend_available_at: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO email_verifications (email, otp_hash, salt, attempts, expires_at, resend_available_at, created_at)
        VALUES (?, ?, ?, 0, ?, ?, CURRENT_TIMESTAMP)
    """, (email.lower().strip(), otp_hash, salt, expires_at, resend_available_at))
    conn.commit()
    conn.close()

def get_email_verification(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_verifications WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def increment_otp_attempts(email: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE email_verifications SET attempts = attempts + 1 WHERE email = ?", (email.lower().strip(),))
    cursor.execute("SELECT attempts FROM email_verifications WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return row["attempts"] if row else 0

def delete_email_verification(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_verifications WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

# --- Password Reset Storage ---

def save_password_reset(email: str, token_hash: str, salt: str, expires_at: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO password_resets (email, token_hash, salt, attempts, expires_at, created_at)
        VALUES (?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
    """, (email.lower().strip(), token_hash, salt, expires_at))
    conn.commit()
    conn.close()

def get_password_reset(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM password_resets WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def increment_reset_attempts(email: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE password_resets SET attempts = attempts + 1 WHERE email = ?", (email.lower().strip(),))
    cursor.execute("SELECT attempts FROM password_resets WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return row["attempts"] if row else 0

def delete_password_reset(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM password_resets WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
