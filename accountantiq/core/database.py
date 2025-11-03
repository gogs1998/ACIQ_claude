"""
DuckDB database management for AccountantIQ multi-agent system.
Shared database for agent communication and data persistence.
"""

import duckdb
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class Database:
    """DuckDB database manager for multi-agent communication."""

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._initialize_schema()

    def _initialize_schema(self):
        """Create all tables if they don't exist."""

        # Transactions table - shared by all agents
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                vendor TEXT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                nominal_code TEXT,
                reference TEXT,
                details TEXT,
                source TEXT NOT NULL,
                confidence DECIMAL(3,2),
                explanation TEXT,
                reviewed BOOLEAN DEFAULT FALSE,
                assigned_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Rules table - learner and reviewer agents
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS rules (
                id INTEGER PRIMARY KEY,
                vendor_pattern TEXT NOT NULL,
                nominal_code TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                confidence DECIMAL(3,2) NOT NULL,
                match_count INTEGER DEFAULT 0,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        """)

        # Overrides table - reviewer agent
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS overrides (
                id INTEGER PRIMARY KEY,
                transaction_id INTEGER,
                original_code TEXT,
                corrected_code TEXT,
                created_rule_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Agent logs table - all agents
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY,
                agent_name TEXT NOT NULL,
                action TEXT NOT NULL,
                input_summary TEXT,
                output_summary TEXT,
                duration_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create sequence for auto-incrementing IDs
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_transactions START 1
        """)
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_rules START 1
        """)
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_overrides START 1
        """)
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS seq_agent_logs START 1
        """)

    # Transaction operations
    def insert_transaction(self, transaction: Dict[str, Any]) -> int:
        """Insert a transaction and return its ID."""
        result = self.conn.execute("""
            INSERT INTO transactions (
                id, date, vendor, amount, nominal_code, reference,
                details, source, confidence, explanation, assigned_by
            )
            VALUES (
                nextval('seq_transactions'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            RETURNING id
        """, [
            transaction['date'],
            transaction['vendor'],
            transaction['amount'],
            transaction.get('nominal_code'),
            transaction.get('reference'),
            transaction.get('details'),
            transaction['source'],
            transaction.get('confidence'),
            transaction.get('explanation'),
            transaction.get('assigned_by')
        ]).fetchone()
        return result[0]

    def insert_transactions_bulk(self, transactions: List[Dict[str, Any]]) -> int:
        """Insert multiple transactions efficiently."""
        count = 0
        for txn in transactions:
            self.insert_transaction(txn)
            count += 1
        return count

    def get_transactions(
        self,
        source: Optional[str] = None,
        reviewed: Optional[bool] = None,
        min_confidence: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get transactions with optional filters."""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if reviewed is not None:
            query += " AND reviewed = ?"
            params.append(reviewed)

        if min_confidence is not None:
            query += " AND confidence >= ?"
            params.append(min_confidence)

        query += " ORDER BY created_at DESC"

        if limit:
            query += f" LIMIT {limit}"

        result = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in result]

    def update_transaction(self, txn_id: int, updates: Dict[str, Any]):
        """Update a transaction."""
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE transactions SET {set_clause} WHERE id = ?"
        params = list(updates.values()) + [txn_id]
        self.conn.execute(query, params)

    # Rule operations
    def insert_rule(self, rule: Dict[str, Any]) -> int:
        """Insert a rule and return its ID."""
        result = self.conn.execute("""
            INSERT INTO rules (
                id, vendor_pattern, nominal_code, rule_type,
                confidence, created_by
            )
            VALUES (
                nextval('seq_rules'), ?, ?, ?, ?, ?
            )
            RETURNING id
        """, [
            rule['vendor_pattern'],
            rule['nominal_code'],
            rule['rule_type'],
            rule['confidence'],
            rule.get('created_by')
        ]).fetchone()
        return result[0]

    def get_rules(self, min_confidence: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get all rules, optionally filtered by confidence."""
        query = "SELECT * FROM rules WHERE 1=1"
        params = []

        if min_confidence:
            query += " AND confidence >= ?"
            params.append(min_confidence)

        query += " ORDER BY confidence DESC, match_count DESC"

        result = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in result]

    def update_rule_stats(self, rule_id: int):
        """Update rule usage statistics."""
        self.conn.execute("""
            UPDATE rules
            SET match_count = match_count + 1,
                last_used = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [rule_id])

    def delete_rule(self, rule_id: int):
        """Delete a rule."""
        self.conn.execute("DELETE FROM rules WHERE id = ?", [rule_id])

    # Override operations
    def insert_override(self, override: Dict[str, Any]) -> int:
        """Insert an override record."""
        result = self.conn.execute("""
            INSERT INTO overrides (
                id, transaction_id, original_code,
                corrected_code, created_rule_id
            )
            VALUES (
                nextval('seq_overrides'), ?, ?, ?, ?
            )
            RETURNING id
        """, [
            override['transaction_id'],
            override['original_code'],
            override['corrected_code'],
            override.get('created_rule_id')
        ]).fetchone()
        return result[0]

    # Agent logging
    def log_agent_action(
        self,
        agent_name: str,
        action: str,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """Log an agent action."""
        self.conn.execute("""
            INSERT INTO agent_logs (
                id, agent_name, action, input_summary,
                output_summary, duration_ms
            )
            VALUES (
                nextval('seq_agent_logs'), ?, ?, ?, ?, ?
            )
        """, [agent_name, action, input_summary, output_summary, duration_ms])

    def get_agent_logs(self, agent_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get agent logs."""
        query = "SELECT * FROM agent_logs WHERE 1=1"
        params = []

        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        result = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        return [dict(zip(columns, row)) for row in result]

    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get workspace statistics."""
        stats = {}

        # Transaction counts
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN source = 'history' THEN 1 END) as history,
                COUNT(CASE WHEN source = 'bank' THEN 1 END) as bank,
                COUNT(CASE WHEN reviewed = TRUE THEN 1 END) as reviewed,
                COUNT(CASE WHEN nominal_code IS NOT NULL THEN 1 END) as coded,
                AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence
            FROM transactions
        """).fetchone()

        stats['transactions'] = {
            'total': result[0],
            'history': result[1],
            'bank': result[2],
            'reviewed': result[3],
            'coded': result[4],
            'avg_confidence': round(result[5], 2) if result[5] else 0.0
        }

        # Rule counts
        result = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN created_by = 'learner' THEN 1 END) as learned,
                COUNT(CASE WHEN created_by = 'reviewer' THEN 1 END) as manual,
                AVG(confidence) as avg_confidence
            FROM rules
        """).fetchone()

        stats['rules'] = {
            'total': result[0],
            'learned': result[1],
            'manual': result[2],
            'avg_confidence': round(result[3], 2) if result[3] else 0.0
        }

        # Override count
        override_count = self.conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0]
        stats['overrides'] = override_count

        return stats

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
