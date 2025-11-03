"""
Bank statement CSV parser.
Will be implemented after receiving real bank CSV format.
"""

import polars as pl
from pathlib import Path
from typing import List, Dict, Any

from accountantiq.core.database import Database
from accountantiq.core.models import Transaction


class BankParser:
    """Parses bank statement CSV files."""

    def __init__(self, db: Database):
        """
        Initialize parser.

        Args:
            db: Database connection
        """
        self.db = db

    def parse(self, file_path: str) -> List[Transaction]:
        """
        Parse bank statement CSV file.

        Args:
            file_path: Path to bank CSV file

        Returns:
            List of Transaction objects

        Note:
            This is a placeholder. Will be implemented after seeing real format.
        """
        raise NotImplementedError(
            "Bank parser not yet implemented. "
            "Waiting for real bank statement CSV format sample."
        )

    def _detect_columns(self, df: pl.DataFrame) -> Dict[str, str]:
        """
        Auto-detect column mappings.

        Args:
            df: Polars DataFrame

        Returns:
            Column mapping dict
        """
        # TODO: Implement after seeing real format
        pass

    def _normalize_transaction(self, row: dict) -> Transaction:
        """
        Convert bank row to Transaction model.

        Args:
            row: Row from CSV

        Returns:
            Transaction object
        """
        # TODO: Implement after seeing real format
        pass
