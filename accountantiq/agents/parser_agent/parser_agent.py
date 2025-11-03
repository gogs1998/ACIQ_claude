"""
Parser Agent - Entry point for CSV parsing operations.
"""

from pathlib import Path
from typing import Literal
import time

from accountantiq.core.database import Database
from accountantiq.core.models import ParserResult
from accountantiq.agents.parser_agent.sage_parser import SageParser
from accountantiq.agents.parser_agent.bank_parser import BankParser


class ParserAgent:
    """Main parser agent that delegates to specific parsers."""

    def __init__(self, workspace_path: str):
        """
        Initialize parser agent.

        Args:
            workspace_path: Path to workspace
        """
        self.workspace_path = Path(workspace_path)
        self.db_path = self.workspace_path / "accountant.db"

    def run(
        self,
        file_path: str,
        file_type: Literal["sage", "bank"]
    ) -> ParserResult:
        """
        Run parser on a CSV file.

        Args:
            file_path: Path to CSV file
            file_type: Type of file ('sage' or 'bank')

        Returns:
            ParserResult with statistics
        """
        start_time = time.time()

        with Database(str(self.db_path)) as db:
            if file_type == "sage":
                parser = SageParser(db)
            elif file_type == "bank":
                parser = BankParser(db)
            else:
                raise ValueError(f"Unknown file type: {file_type}")

            try:
                transactions = parser.parse(file_path)
                rows_inserted = db.insert_transactions_bulk(
                    [t.to_dict() for t in transactions]
                )

                # Log action
                db.log_agent_action(
                    agent_name="parser",
                    action=f"parse_{file_type}",
                    input_summary=f"file={Path(file_path).name}",
                    output_summary=f"inserted={rows_inserted}",
                    duration_ms=int((time.time() - start_time) * 1000)
                )

                return ParserResult(
                    agent="parser",
                    status="complete",
                    stats={
                        "rows_parsed": len(transactions),
                        "rows_inserted": rows_inserted,
                        "errors": 0
                    },
                    duration_ms=int((time.time() - start_time) * 1000),
                    next_step="learner" if file_type == "sage" else "classifier"
                )

            except Exception as e:
                # Log error
                db.log_agent_action(
                    agent_name="parser",
                    action=f"parse_{file_type}",
                    input_summary=f"file={Path(file_path).name}",
                    output_summary=f"error={str(e)}",
                    duration_ms=int((time.time() - start_time) * 1000)
                )

                return ParserResult(
                    agent="parser",
                    status="error",
                    error_message=str(e),
                    duration_ms=int((time.time() - start_time) * 1000)
                )
