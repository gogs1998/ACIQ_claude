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

    def _export_sage50(self, transactions: List[dict], output_path: Path):
        """
        Export to Sage 50 Audit Trail format.

        Args:
            transactions: List of coded transactions
            output_path: Output file path

        Note:
            This is a placeholder. Column mapping will be implemented
            after receiving real Sage 50 format sample.
        """
        # Placeholder format - will be customized based on real Sage format
        headers = [
            'Date',
            'Reference',
            'Nominal Code',
            'Details',
            'Amount',
            'Debit',
            'Credit'
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for txn in transactions:
                # Determine debit/credit based on amount
                amount = float(txn.get('amount', 0))
                debit = amount if amount > 0 else 0
                credit = abs(amount) if amount < 0 else 0

                row = {
                    'Date': txn.get('date', ''),
                    'Reference': txn.get('reference', ''),
                    'Nominal Code': txn.get('nominal_code', ''),
                    'Details': txn.get('vendor', ''),
                    'Amount': abs(amount),
                    'Debit': debit,
                    'Credit': credit
                }
                writer.writerow(row)
