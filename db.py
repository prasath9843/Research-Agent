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
        auth_provider TEXT DEFAULT 'email',
        google_id TEXT,
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        code TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safe migration: add user_id column to sessions if not present
    try:
        cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT;")
    except sqlite3.OperationalError:
        pass # Already exists

    conn.commit()
    conn.close()

def save_verification_code(email: str, code: str, expires_at: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO email_verifications (email, code, expires_at, created_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (email.lower().strip(), code.strip(), expires_at))
    conn.commit()
    conn.close()

def get_verification_code(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM email_verifications WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_verification_code(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM email_verifications WHERE email = ?", (email.lower().strip(),))
    conn.commit()
    conn.close()

def create_user(user_id: str, email: str, name: str, password_hash: str = None, auth_provider: str = 'email', google_id: str = None, avatar_url: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (id, email, name, password_hash, auth_provider, google_id, avatar_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, email.lower().strip(), name.strip(), password_hash, auth_provider, google_id, avatar_url))
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

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
