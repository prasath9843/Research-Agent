import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from db import get_db_connection

class EvidenceStore:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id

    def _resolve_session_id(self, session_id: Optional[str] = None) -> str:
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("session_id is required")
        return sid

    def create_session(self, session_id_or_query: str, query_or_config: Any = None, config: Optional[dict] = None, user_id: Optional[str] = None, config_data: Optional[dict] = None):
        if config is not None or (isinstance(query_or_config, str) and not isinstance(query_or_config, dict)):
            sid = session_id_or_query
            query = str(query_or_config)
            cfg = config or config_data or {}
        else:
            sid = self.session_id or session_id_or_query
            query = session_id_or_query if not self.session_id else str(query_or_config)
            cfg = query_or_config if isinstance(query_or_config, dict) else (config_data or {})

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions (session_id, user_id, query, status, stage, config_json, created_at, updated_at)
            VALUES (?, ?, ?, 'running', 'initialized', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (sid, user_id, query, json.dumps(cfg))
        )
        conn.commit()
        conn.close()
        self.session_id = sid

    def get_session(self, session_id: Optional[str] = None) -> Optional[dict]:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (sid,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_session_status(self, session_id: Optional[str] = None) -> Optional[dict]:
        return self.get_session(session_id)

    def update_session(self, status: Optional[str] = None, stage: Optional[str] = None, rounds_completed: Optional[int] = None, session_id: Optional[str] = None):
        sid = self._resolve_session_id(session_id)
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
        params.append(sid)

        sql = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"
        cursor.execute(sql, params)
        conn.commit()
        conn.close()

    def log(self, stage: str, message: str, level: str = "INFO", session_id: Optional[str] = None):
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO session_logs (session_id, stage, message, level, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (sid, stage, message, level)
        )
        conn.commit()
        conn.close()

    def get_logs(self, session_id: Optional[str] = None) -> List[dict]:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM session_logs WHERE session_id = ? ORDER BY id ASC", (sid,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_session_logs(self, session_id: Optional[str] = None) -> List[dict]:
        return self.get_logs(session_id)

    def add_sub_questions(self, sub_questions: list, session_id: Optional[str] = None):
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        for sq in sub_questions:
            cursor.execute(
                """
                INSERT INTO sub_questions (session_id, tag, text, category)
                VALUES (?, ?, ?, ?)
                """,
                (sid, sq.id if hasattr(sq, 'id') else sq['id'],
                 sq.text if hasattr(sq, 'text') else sq['text'],
                 sq.category if hasattr(sq, 'category') else sq.get('category', 'General'))
            )
        conn.commit()
        conn.close()

    def get_sub_questions(self, session_id: Optional[str] = None) -> List[dict]:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sub_questions WHERE session_id = ?", (sid,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def add_source(self, url: str, title: str, domain: str, domain_score: float, relevance_score: float, relevance_reason: str, clean_text: str, session_id: Optional[str] = None) -> int:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM sources WHERE session_id = ? AND url = ?", (sid, url))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row['id']

        cursor.execute(
            """
            INSERT INTO sources (session_id, url, title, domain, domain_score, relevance_score, relevance_reason, clean_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sid, url, title, domain, domain_score, relevance_score, relevance_reason, clean_text)
        )
        source_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return source_id

    def get_sources(self, session_id: Optional[str] = None) -> List[dict]:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sources WHERE session_id = ?", (sid,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def add_claims(self, source_id: int, claims: list, session_id: Optional[str] = None):
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        for c in claims:
            c_text = c.claim if hasattr(c, 'claim') else (c.claim_text if hasattr(c, 'claim_text') else (c.get('claim') or c.get('claim_text', '')))
            q_text = c.quote_or_paraphrase if hasattr(c, 'quote_or_paraphrase') else c.get('quote_or_paraphrase', '')
            sq_tag = c.sub_question_tag if hasattr(c, 'sub_question_tag') else c.get('sub_question_tag', 'SQ1')
            conf = c.confidence if hasattr(c, 'confidence') else c.get('confidence', 1.0)
            cursor.execute(
                """
                INSERT INTO claims (session_id, source_id, claim_text, quote_or_paraphrase, sub_question_tag, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sid, source_id, c_text, q_text, sq_tag, conf)
            )
        conn.commit()
        conn.close()

    def get_claims(self, session_id: Optional[str] = None) -> List[dict]:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT c.*, s.url as source_url, s.title as source_title, s.domain as source_domain
            FROM claims c
            JOIN sources s ON c.source_id = s.id
            WHERE c.session_id = ?
            """,
            (sid,)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def add_contradictions(self, contradictions: list, session_id: Optional[str] = None):
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        for item in contradictions:
            topic = getattr(item, 'topic', None) or (item.get('topic') if isinstance(item, dict) else '')
            consensus = getattr(item, 'consensus_summary', None) or (item.get('consensus_summary') if isinstance(item, dict) else '')
            
            conflicting = getattr(item, 'conflicting_views', None)
            if conflicting is None and isinstance(item, dict):
                conflicting = item.get('conflicting_views')
            if not isinstance(conflicting, str):
                conflicting = json.dumps(conflicting or [])
                
            affected = getattr(item, 'affected_sources', None) or getattr(item, 'affected_source_ids', None)
            if affected is None and isinstance(item, dict):
                affected = item.get('affected_sources') or item.get('affected_source_ids', [])
            if not isinstance(affected, str):
                affected = json.dumps(affected or [])

            cursor.execute(
                """
                INSERT INTO contradictions (session_id, topic, consensus_summary, conflicting_views, affected_source_ids)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, topic, consensus, conflicting, affected)
            )
        conn.commit()
        conn.close()

    def get_contradictions(self, session_id: Optional[str] = None) -> List[dict]:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contradictions WHERE session_id = ?", (sid,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def save_report(self, markdown_content: str, verified_count: int, total_count: int, session_id: Optional[str] = None):
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reports (session_id, markdown_content, verified_citations_count, total_citations_count)
            VALUES (?, ?, ?, ?)
            """,
            (sid, markdown_content, verified_count, total_count)
        )
        conn.commit()
        conn.close()

    def get_latest_report(self, session_id: Optional[str] = None) -> Optional[dict]:
        sid = self._resolve_session_id(session_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports WHERE session_id = ? ORDER BY id DESC LIMIT 1", (sid,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_report(self, session_id: Optional[str] = None) -> Optional[dict]:
        return self.get_latest_report(session_id)

    def update_report_content(self, session_id: str, markdown_content: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE reports SET markdown_content = ? WHERE session_id = ?", (markdown_content, session_id))
        conn.commit()
        conn.close()
