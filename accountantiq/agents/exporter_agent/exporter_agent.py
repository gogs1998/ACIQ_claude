"""
Exporter Agent - Generates Sage 50 Audit Trail CSV files.
"""

from pathlib import Path
import time
import csv
from typing import List, Dict

from accountantiq.core.database import Database
from accountantiq.core.models import ExporterResult


class ExporterAgent:
    """Exports coded transactions to Sage 50 format."""

    def __init__(self, workspace_path: str):
        """
        Initialize exporter agent.

        Args:
            workspace_path: Path to workspace
        """
        self.workspace_path = Path(workspace_path)
        self.db_path = self.workspace_path / "accountant.db"
        self.exports_dir = self.workspace_path / "exports"
        self.exports_dir.mkdir(exist_ok=True)

    def run(
        self,
        output_filename: str = "sage_import.csv",
        format_type: str = "sage50"
    ) -> ExporterResult:
        """
        Export coded transactions to CSV.

        Args:
            output_filename: Name of output file
            format_type: Export format (only 'sage50' supported for now)

        Returns:
            ExporterResult with statistics
        """
        start_time = time.time()

        with Database(str(self.db_path)) as db:
            # Get coded transactions
            bank_txns = db.get_transactions(source="bank")
            coded = [
                t for t in bank_txns
                if t.get('nominal_code') and t.get('nominal_code').strip()
            ]

            if not coded:
                return ExporterResult(
                    agent="exporter",
                    status="error",
                    error_message="No coded transactions to export",
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            # Export based on format
            output_path = self.exports_dir / output_filename

            if format_type == "sage50":
                self._export_sage50(coded, output_path)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            # Log action
            db.log_agent_action(
                agent_name="exporter",
                action="export_transactions",
                input_summary=f"coded_txns={len(coded)}",
                output_summary=f"file={output_filename}",
                duration_ms=int((time.time() - start_time) * 1000)
            )

            return ExporterResult(
                agent="exporter",
                status="complete",
                stats={
                    "transactions_exported": len(coded),
                    "output_file": str(output_path)
                },
                duration_ms=int((time.time() - start_time) * 1000)
            )

    def _sanitize_csv_field(self, value: str) -> str:
        """
        Sanitize CSV field to prevent formula injection attacks.

        Prevents Excel/LibreOffice from executing formulas by prefixing
        dangerous characters with a single quote.

        Args:
            value: Field value to sanitize

        Returns:
            Sanitized value safe for CSV export
        """
        if not value or not isinstance(value, str):
            return value or ''

        # SECURITY FIX: Prevent CSV injection
        # If field starts with =, +, -, @, |, %, or tab, prefix with single quote
        dangerous_chars = ('=', '+', '-', '@', '|', '%', '\t')
        if value and value[0] in dangerous_chars:
            return "'" + value

        return value

    def _export_sage50(self, transactions: List[dict], output_path: Path):
        """
        Export to Sage 50 import format (simplified CSV).

        Creates a simple CSV that can be imported into Sage 50:
        Date, Type, Nominal Code, Reference, Details, Debit, Credit

        Args:
            transactions: List of coded transactions
            output_path: Output file path
        """
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'Date',
                'Type',
                'Nominal Code',
                'Reference',
                'Details',
                'Debit',
                'Credit'
            ])

            for txn in transactions:
                # Determine debit/credit based on amount
                amount = float(txn.get('amount', 0))

                # Convert date to DD/MM/YYYY format (Sage format)
                date_str = txn.get('date', '')
                if isinstance(date_str, str) and len(date_str) == 10:
                    # Already in YYYY-MM-DD format
                    from datetime import datetime
                    try:
                        date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
                        date_str = date_obj.strftime("%d/%m/%Y")
                    except (ValueError, TypeError):
                        pass

                # Determine type and debit/credit
                if amount > 0:
                    txn_type = "BR"  # Bank Receipt
                    debit = amount
                    credit = 0
                else:
                    txn_type = "BP"  # Bank Payment
                    debit = 0
                    credit = abs(amount)

                # SECURITY FIX: Sanitize user-controlled fields
                row = [
                    date_str,
                    txn_type,
                    self._sanitize_csv_field(txn.get('nominal_code', '')),
                    self._sanitize_csv_field(txn.get('reference', '')),
                    self._sanitize_csv_field(txn.get('vendor', '')),
                    f"{debit:.2f}",
                    f"{credit:.2f}"
                ]
                writer.writerow(row)
