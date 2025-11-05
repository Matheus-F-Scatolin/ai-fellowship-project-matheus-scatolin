# Database - Interface para persistência de dados
import sqlite3
from typing import Optional, Dict, Any, List
import json
from contextlib import contextmanager

DATABASE_PATH = "./persistent_data/templates.db"


class TemplateDatabase:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        with self._get_connection() as conn:
            # Tabela templates
            conn.execute("""
                CREATE TABLE IF NOT EXISTS templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL UNIQUE,
                    sample_count INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.0,
                    structural_signature TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabela extraction_rules
            conn.execute("""
                CREATE TABLE IF NOT EXISTS extraction_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    rule_data TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    FOREIGN KEY (template_id) REFERENCES templates(id)
                )
            """)
            
            conn.commit()
    
    def find_template_by_label(self, label: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM templates WHERE label = ? LIMIT 1", (label,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def create_template(self, label: str, structural_signature: List[str]) -> int:
        signature_json = json.dumps(sorted(structural_signature))
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO templates (label, structural_signature, sample_count, confidence) VALUES (?, ?, 1, 0.5)",
                (label, signature_json)
            )
            conn.commit()
            return cursor.lastrowid
    
    def update_template_signature(self, template_id: int, new_signature: List[str]):
        signature_json = json.dumps(sorted(new_signature))
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE templates SET structural_signature = ?, sample_count = sample_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (signature_json, template_id)
            )
            conn.commit()
    
    def add_extraction_rule(self, template_id: int, field_name: str, rule_type: str, rule_data: Dict[str, Any], confidence: float):
        rule_data_json = json.dumps(rule_data)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Primeiro, deleta uma regra antiga para este campo (UPSERT)
            cursor.execute(
                "DELETE FROM extraction_rules WHERE template_id = ? AND field_name = ?",
                (template_id, field_name)
            )
            # Insere a nova regra
            cursor.execute(
                "INSERT INTO extraction_rules (template_id, field_name, rule_type, rule_data, confidence) VALUES (?, ?, ?, ?, ?)",
                (template_id, field_name, rule_type, rule_data_json, confidence)
            )
            conn.commit()
    
    def get_extraction_rules(self, template_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM extraction_rules WHERE template_id = ?", (template_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]