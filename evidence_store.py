import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from db import get_db_connection

class EvidenceStore:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def create_session(self, query: str, config_data: dict, user_id: Optional[str] = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions (session_id, user_id, query, status, stage, config_json, created_at, updated_at)
            VALUES (?, ?, ?, 'running', 'initialized', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (self.session_id, user_id, query, json.dumps(config_data))
        )
        conn.commit()
        conn.close()

    def update_session(self, status: Optional[str] = None, stage: Optional[str] = None, rounds_completed: Optional[int] = None):
        conn = get_db_connection()
        cursor = conn.cursor()
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
        if stage:
            updates.append("stage = ?")
            params.append(stage)
        if rounds_completed is not None:
            updates.append("rounds_completed = ?")
            params.append(rounds_completed)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(self.session_id)

        sql = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        conn.close()

    def log(self, stage: str, message: str, level: str = "INFO"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO session_logs (session_id, stage, message, level, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (self.session_id, stage, message, level)
        )
        conn.commit()
        conn.close()

    def add_sub_questions(self, sub_questions: list):
        conn = get_db_connection()
        cursor = conn.cursor()
        for sq in sub_questions:
            cursor.execute(
                """
                INSERT INTO sub_questions (session_id, tag, text, category)
                VALUES (?, ?, ?, ?)
                """,
                (self.session_id, sq.id if hasattr(sq, 'id') else sq['id'],
                 sq.text if hasattr(sq, 'text') else sq['text'],
                 sq.category if hasattr(sq, 'category') else sq.get('category', 'General'))
            )
        conn.commit()
        conn.close()

    def add_source(self, url: str, title: str, domain: str, domain_score: float, relevance_score: float, relevance_reason: str, clean_text: str) -> int:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if URL already exists for this session
        cursor.execute("SELECT id FROM sources WHERE session_id = ? AND url = ?", (self.session_id, url))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row['id']

        cursor.execute(
            """
            INSERT INTO sources (session_id, url, title, domain, domain_score, relevance_score, relevance_reason, clean_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (self.session_id, url, title, domain, domain_score, relevance_score, relevance_reason, clean_text)
        )
        source_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return source_id

    def add_claims(self, source_id: int, claims: list):
        conn = get_db_connection()
        cursor = conn.cursor()
        for c in claims:
            cursor.execute(
                """
                INSERT INTO claims (session_id, source_id, claim_text, quote_or_paraphrase, sub_question_tag, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (self.session_id, source_id,
                 c.claim if hasattr(c, 'claim') else c['claim'],
                 c.quote_or_paraphrase if hasattr(c, 'quote_or_paraphrase') else c['quote_or_paraphrase'],
                 c.sub_question_tag if hasattr(c, 'sub_question_tag') else c['sub_question_tag'],
                 c.confidence if hasattr(c, 'confidence') else c.get('confidence', 1.0))
            )
        conn.commit()
        conn.close()

    def get_sources(self) -> List[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sources WHERE session_id = ?", (self.session_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_claims(self) -> List[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.*, s.url as source_url, s.title as source_title, s.domain as source_domain
            FROM claims c
            JOIN sources s ON c.source_id = s.id
            WHERE c.session_id = ?
            """,
            (self.session_id,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_sub_questions(self) -> List[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sub_questions WHERE session_id = ?", (self.session_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def add_contradictions(self, contradictions: list):
        conn = get_db_connection()
        cursor = conn.cursor()
        for item in contradictions:
            cursor.execute(
                """
                INSERT INTO contradictions (session_id, topic, consensus_summary, conflicting_views, affected_source_ids)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self.session_id,
                 item.topic if hasattr(item, 'topic') else item['topic'],
                 item.consensus_summary if hasattr(item, 'consensus_summary') else item['consensus_summary'],
                 json.dumps(item.conflicting_views if hasattr(item, 'conflicting_views') else item['conflicting_views']),
                 json.dumps(item.affected_source_ids if hasattr(item, 'affected_source_ids') else item['affected_source_ids']))
            )
        conn.commit()
        conn.close()

    def get_contradictions(self) -> List[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contradictions WHERE session_id = ?", (self.session_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_report(self, markdown_content: str, verified_count: int, total_count: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (session_id, markdown_content, verified_citations_count, total_citations_count)
            VALUES (?, ?, ?, ?)
            """,
            (self.session_id, markdown_content, verified_count, total_count)
        )
        conn.commit()
        conn.close()

    def get_latest_report(self) -> Optional[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE session_id = ? ORDER BY id DESC LIMIT 1", (self.session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_logs(self) -> List[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM session_logs WHERE session_id = ? ORDER BY id ASC", (self.session_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_session_status(self) -> Optional[dict]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (self.session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
