"""
Bank statement CSV parser.
Custom parser for TransactionHistory.csv format.
"""

import polars as pl
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from decimal import Decimal
import re

from accountantiq.core.database import Database
from accountantiq.core.models import Transaction


class BankParser:
    """Parses bank statement CSV files (TransactionHistory.csv format)."""

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

        File format (no headers):
        Col 0: Date (YYYYMMDD)
        Col 4: DR/CR indicator
        Col 6: Transaction Type (Card, Transfer, ATM, etc.)
        Col 7: Amount (negative for DR, positive for CR)
        Col 8: Description/Vendor
        Col 9: Reference

        Args:
            file_path: Path to bank CSV file

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

        for row in df.iter_rows(named=False):
            try:
                # Extract fields
                date_str = str(row[0]).strip() if row[0] else ""
                dr_cr = str(row[4]).strip() if len(row) > 4 and row[4] else ""
                txn_type = str(row[6]).strip() if len(row) > 6 and row[6] else ""
                amount_raw = str(row[7]).strip() if len(row) > 7 and row[7] else "0"
                description = str(row[8]).strip() if len(row) > 8 and row[8] else ""
                reference = str(row[9]).strip() if len(row) > 9 and row[9] else ""

                # Parse date (YYYYMMDD format)
                try:
                    date_obj = datetime.strptime(date_str, "%Y%m%d").date()
                except:
                    continue

                # Parse amount (remove commas, convert to float)
                try:
                    amount = float(amount_raw.replace(",", ""))
                except:
                    continue

                # Skip zero amounts
                if amount == 0:
                    continue

                # Extract vendor from description
                vendor = self._extract_vendor(description, txn_type)

                # Build details string
                details = f"{txn_type}: {description}"
                if reference and reference != description:
                    details += f" (Ref: {reference})"

                # Create Transaction object
                transaction = Transaction(
                    date=date_obj,
                    vendor=vendor,
                    amount=Decimal(str(amount)),
                    nominal_code=None,  # To be coded
                    reference=reference,
                    details=details,
                    source="bank",
                    confidence=None,  # Will be set by classifier
                    assigned_by=None
                )

                transactions.append(transaction)

            except Exception as e:
                # Skip problematic rows
                continue

        return transactions

    def _extract_vendor(self, description: str, txn_type: str) -> str:
        """
        Extract vendor name from bank description.

        Args:
            description: Full transaction description
            txn_type: Transaction type (Card, Transfer, etc.)

        Returns:
            Extracted vendor name
        """
        # Remove leading/trailing whitespace
        vendor = description.strip()

        # For card transactions, extract merchant name
        if txn_type == "Card":
            # Pattern: "Card XX, Merchant Name"
            match = re.search(r'Card \d+,\s*(.+)', vendor)
            if match:
                vendor = match.group(1).strip()

        # For transfers, extract payee
        elif txn_type == "Transfer":
            # Pattern: "FPS, Gbp Faster Payment, Payee"
            # Or: "MOB, Payee, Details"
            if vendor.startswith("FPS,"):
                parts = vendor.split(",")
                if len(parts) >= 3:
                    vendor = parts[2].strip()
            elif vendor.startswith("MOB,"):
                parts = vendor.split(",")
                if len(parts) >= 2:
                    vendor = parts[1].strip()

        # For Direct Debits, extract company name
        elif txn_type == "Direct Debit":
            # Pattern: "Company Name, Reference"
            parts = vendor.split(",")
            if len(parts) >= 1:
                vendor = parts[0].strip()

        # For wallet transactions
        if vendor.startswith("WLT "):
            # Pattern: "WLT XX, Merchant"
            match = re.search(r'WLT \d+,\s*(.+)', vendor)
            if match:
                vendor = match.group(1).strip()

        # For contactless
        if vendor.startswith("CLS "):
            # Pattern: "CLS XX, Merchant"
            match = re.search(r'CLS \d+,\s*(.+)', vendor)
            if match:
                vendor = match.group(1).strip()

        # Normalize vendor name
        vendor = self._normalize_vendor(vendor)

        return vendor

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

        # Remove common patterns
        patterns = [
            r'^Card \d+,?\s*',
            r'^WLT \d+,?\s*',
            r'^CLS \d+,?\s*',
            r'^MOB,?\s*',
            r'^FPS,?\s*',
        ]

        for pattern in patterns:
            vendor = re.sub(pattern, '', vendor, flags=re.IGNORECASE)

        # Trim again
        vendor = vendor.strip()

        # If empty after normalization, return original
        if not vendor:
            return "Unknown"

        return vendor
