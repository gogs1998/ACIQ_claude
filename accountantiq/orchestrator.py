"""
Multi-agent orchestrator for AccountantIQ.
Coordinates the workflow between all 5 agents.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.table import Table

from accountantiq.core.workspace import Workspace
from accountantiq.core.database import Database
from accountantiq.agents.parser_agent.parser_agent import ParserAgent
from accountantiq.agents.learner_agent.learner_agent import LearnerAgent
from accountantiq.agents.classifier_agent.classifier_agent import ClassifierAgent
from accountantiq.agents.reviewer_agent.reviewer_agent import ReviewerAgent
from accountantiq.agents.exporter_agent.exporter_agent import ExporterAgent

console = Console()


class AccountantOrchestrator:
    """Orchestrates multi-agent workflow for auto-coding transactions."""

    def __init__(self, workspace_name: str, workspace_base_path: Optional[str] = None):
        """
        Initialize orchestrator.

        Args:
            workspace_name: Name of workspace to use
            workspace_base_path: Base path for workspaces (optional)
        """
        self.workspace = Workspace(workspace_name, workspace_base_path)

        # Ensure workspace exists
        if not self.workspace.exists():
            raise ValueError(
                f"Workspace '{workspace_name}' does not exist. "
                f"Create it first with: accountantiq workspace create {workspace_name}"
            )

        self.workspace_path = str(self.workspace.workspace_path)

    def run_full_pipeline(
        self,
        sage_file: Optional[str] = None,
        bank_file: Optional[str] = None,
        output_file: str = "sage_import.csv",
        interactive_review: bool = True
    ) -> Dict[str, Any]:
        """
        Execute complete multi-agent pipeline.

        Pipeline flow:
        1. Parse Sage historical data (if provided)
        2. Learn patterns from historical data
        3. Parse bank statement
        4. Classify bank transactions
        5. Review exceptions (if interactive)
        6. Export to Sage format

        Args:
            sage_file: Path to Sage 50 export CSV (optional)
            bank_file: Path to bank statement CSV (required for coding)
            output_file: Name of output file
            interactive_review: Enable interactive exception review

        Returns:
            Dict with pipeline results and statistics
        """
        results = {}

        console.print("\n[bold blue]🤖 AccountantIQ Multi-Agent Pipeline[/bold blue]\n")

        # Phase 1: Parse Sage historical data
        if sage_file:
            console.print("[cyan]Phase 1:[/cyan] Parsing Sage historical data...")
            parser = ParserAgent(self.workspace_path)
            result = parser.run(sage_file, "sage")
            results['parse_sage'] = result.to_dict()

            if result.status == "error":
                console.print(f"[red]Error:[/red] {result.error_message}")
                return results

            console.print(
                f"  ✓ Parsed {result.stats['rows_inserted']} historical transactions\n"
            )

            # Phase 2: Learn patterns
            console.print("[cyan]Phase 2:[/cyan] Learning vendor patterns...")
            learner = LearnerAgent(self.workspace_path)
            result = learner.run()
            results['learn'] = result.to_dict()

            if result.status == "error":
                console.print(f"[red]Error:[/red] {result.error_message}")
                return results

            console.print(
                f"  ✓ Generated {result.stats['rules_generated']} rules "
                f"from {result.stats['unique_vendors']} unique vendors\n"
            )

        # Phase 3: Parse bank statement
        if bank_file:
            console.print("[cyan]Phase 3:[/cyan] Parsing bank statement...")
            parser = ParserAgent(self.workspace_path)
            result = parser.run(bank_file, "bank")
            results['parse_bank'] = result.to_dict()

            if result.status == "error":
                console.print(f"[red]Error:[/red] {result.error_message}")
                return results

            console.print(
                f"  ✓ Parsed {result.stats['rows_inserted']} bank transactions\n"
            )

            # Phase 4: Classify transactions
            console.print("[cyan]Phase 4:[/cyan] Auto-coding transactions...")
            classifier = ClassifierAgent(self.workspace_path)
            result = classifier.run()
            results['classify'] = result.to_dict()

            if result.status == "error":
                console.print(f"[red]Error:[/red] {result.error_message}")
                return results

            console.print(
                f"  ✓ Auto-coded {result.stats['auto_coded']}/{result.stats['processed']} "
                f"transactions (avg confidence: {result.stats['avg_confidence']:.1%})\n"
            )

            # Phase 5: Review exceptions
            if result.stats['exceptions'] > 0:
                console.print(
                    f"[cyan]Phase 5:[/cyan] Reviewing {result.stats['exceptions']} exceptions..."
                )
                reviewer = ReviewerAgent(self.workspace_path)
                result = reviewer.run(interactive=interactive_review)
                results['review'] = result.to_dict()

                if interactive_review:
                    console.print(
                        f"  ✓ Reviewed {result.stats['reviewed']} transactions, "
                        f"created {result.stats['new_rules_created']} new rules\n"
                    )
                else:
                    console.print(
                        f"  ℹ {result.stats['reviewed']} transactions need manual review\n"
                    )

            # Phase 6: Export
            console.print("[cyan]Phase 6:[/cyan] Generating Sage import file...")
            exporter = ExporterAgent(self.workspace_path)
            result = exporter.run(output_filename=output_file)
            results['export'] = result.to_dict()

            if result.status == "error":
                console.print(f"[red]Error:[/red] {result.error_message}")
                return results

            console.print(
                f"  ✓ Exported {result.stats['transactions_exported']} transactions\n"
            )
            console.print(
                f"[bold green]✓ Pipeline complete![/bold green] Output: {result.stats['output_file']}\n"
            )

        return results

    def get_workspace_stats(self) -> Dict[str, Any]:
        """Get workspace statistics."""
        with self.workspace.get_database() as db:
            return db.get_stats()

    def display_stats(self):
        """Display workspace statistics in a formatted table."""
        stats = self.get_workspace_stats()

        # Transactions table
        txn_table = Table(title="Transactions")
        txn_table.add_column("Metric", style="cyan")
        txn_table.add_column("Count", style="green")

        for key, value in stats['transactions'].items():
            if key != 'avg_confidence':
                txn_table.add_row(key.replace('_', ' ').title(), str(value))
            else:
                txn_table.add_row(
                    "Avg Confidence",
                    f"{value:.1%}" if isinstance(value, float) else str(value)
                )

        console.print(txn_table)

        # Rules table
        rules_table = Table(title="Rules")
        rules_table.add_column("Metric", style="cyan")
        rules_table.add_column("Count", style="green")

        for key, value in stats['rules'].items():
            if key != 'avg_confidence':
                rules_table.add_row(key.replace('_', ' ').title(), str(value))
            else:
                rules_table.add_row(
                    "Avg Confidence",
                    f"{value:.1%}" if isinstance(value, float) else str(value)
                )

        console.print(rules_table)
        console.print(f"\n[cyan]Overrides:[/cyan] {stats['overrides']}")

    # Individual agent operations
    def parse_sage(self, file_path: str):
        """Parse Sage historical data."""
        agent = ParserAgent(self.workspace_path)
        return agent.run(file_path, "sage")

    def parse_bank(self, file_path: str):
        """Parse bank statement."""
        agent = ParserAgent(self.workspace_path)
        return agent.run(file_path, "bank")

    def learn_patterns(self, min_confidence: float = 0.75):
        """Learn patterns from historical data."""
        agent = LearnerAgent(self.workspace_path)
        return agent.run(min_confidence=min_confidence)

    def classify_transactions(self, confidence_threshold: float = 0.70):
        """Classify transactions."""
        agent = ClassifierAgent(self.workspace_path)
        return agent.run(confidence_threshold=confidence_threshold)

    def review_exceptions(self, interactive: bool = True):
        """Review exception transactions."""
        agent = ReviewerAgent(self.workspace_path)
        return agent.run(interactive=interactive)

    def export_transactions(self, output_filename: str = "sage_import.csv"):
        """Export coded transactions."""
        agent = ExporterAgent(self.workspace_path)
        return agent.run(output_filename=output_filename)
