"""
Sage 50 CSV parser.
Will be implemented after receiving real Sage CSV format.
"""

import polars as pl
from pathlib import Path
from typing import List, Dict, Any

from accountantiq.core.database import Database
from accountantiq.core.models import Transaction


class SageParser:
    """Parses Sage 50 export CSV files."""

    def __init__(self, db: Database):
        """
        Initialize parser.

        Args:
            db: Database connection
        """
        self.db = db

    def parse(self, file_path: str) -> List[Transaction]:
        """
        Parse Sage 50 CSV file.

        Args:
            file_path: Path to Sage CSV file

        Returns:
            List of Transaction objects

        Note:
            This is a placeholder. Will be implemented after seeing real format.
        """
        raise NotImplementedError(
            "Sage parser not yet implemented. "
            "Waiting for real Sage 50 CSV format sample."
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
        Convert Sage row to Transaction model.

        Args:
            row: Row from CSV

        Returns:
            Transaction object
        """
        # TODO: Implement after seeing real format
        pass
