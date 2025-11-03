"""
Sage 50 Audit Trail CSV parser.
Custom parser for AUDITDL2.csv format.
"""

import polars as pl
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal

from accountantiq.core.database import Database
from accountantiq.core.models import Transaction


class SageParser:
    """Parses Sage 50 Audit Trail CSV files (AUDITDL2.csv format)."""

    def __init__(self, db: Database):
        """
        Initialize parser.

        Args:
            db: Database connection
        """
        self.db = db

    def parse(self, file_path: str) -> List[Transaction]:
        """
        Parse Sage 50 Audit Trail CSV file.

        File format (no headers):
        Col 0: Transaction ID
        Col 1: Type (JC/JD/BR/BP)
        Col 2: Nominal Code
        Col 3: Date (DD/MM/YYYY)
        Col 4: Reference
        Col 5: Debit Amount
        Col 6: Credit Amount
        Col 14: Details/Vendor

        Args:
            file_path: Path to Sage CSV file

        Returns:
            List of Transaction objects
        """
        # Read CSV with Polars (no headers)
        df = pl.read_csv(
            file_path,
            has_header=False,
            separator=',',
            quote_char='"'
        )

        transactions = []
        seen_combos = set()  # Track unique transaction+nominal combinations

        for row in df.iter_rows(named=False):
            try:
                # Extract fields
                txn_id = str(row[0]) if row[0] else ""
                txn_type = str(row[1]).strip() if row[1] else ""
                nominal_code = str(row[2]).strip() if row[2] else None
                date_str = str(row[3]).strip() if row[3] else ""
                reference = str(row[4]).strip() if row[4] else ""
                debit = float(row[5]) if row[5] else 0.0
                credit = float(row[6]) if row[6] else 0.0

                # Vendor is at column 14
                vendor = str(row[14]).strip() if len(row) > 14 and row[14] else "Unknown"

                # Skip if no nominal code
                if not nominal_code or nominal_code == "0":
                    continue

                # Parse date (DD/MM/YYYY format)
                try:
                    date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                except:
                    continue

                # Calculate amount (debit positive, credit negative for consistency)
                amount = debit - credit
                if amount == 0:
                    continue

                # Create unique key to avoid duplicates
                # (Same transaction can appear multiple times in audit trail)
                unique_key = f"{txn_id}_{nominal_code}_{amount}_{vendor}"
                if unique_key in seen_combos:
                    continue
                seen_combos.add(unique_key)

                # Build details string
                details = f"{txn_type}: {vendor}"
                if reference:
                    details += f" (Ref: {reference})"

                # Create Transaction object
                transaction = Transaction(
                    date=date_obj,
                    vendor=vendor,
                    amount=Decimal(str(amount)),
                    nominal_code=nominal_code,
                    reference=reference,
                    details=details,
                    source="history",
                    confidence=Decimal("1.0"),  # Historical data is 100% confident
                    assigned_by="sage_import"
                )

                transactions.append(transaction)

            except Exception as e:
                # Skip problematic rows
                continue

        return transactions

    def _normalize_vendor(self, vendor: str) -> str:
        """
        Normalize vendor name for consistent matching.

        Args:
            vendor: Raw vendor name

        Returns:
            Normalized vendor name
        """
        # Remove extra whitespace
        vendor = " ".join(vendor.split())

        # Remove common prefixes
        prefixes = ["Card ", "WLT ", "CLS ", "MOB ", "FPS "]
        for prefix in prefixes:
            if vendor.startswith(prefix):
                vendor = vendor[len(prefix):]

        return vendor.strip()
