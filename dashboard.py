#!/usr/bin/env python3
"""
Interactive Dashboard for Manual Transaction Review
Beautiful terminal UI with AI suggestions and manual coding workflow
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
from pathlib import Path
import time

from accountantiq.core.workspace import Workspace
from accountantiq.agents.reviewer_agent.ai_suggester import AISuggester, STANDARD_NOMINAL_CODES


console = Console()


class ReviewDashboard:
    """Interactive dashboard for reviewing and coding transactions."""

    def __init__(self, workspace_name: str = "production", use_llm: bool = False):
        """Initialize dashboard."""
        self.workspace = Workspace(
            workspace_name,
            str(Path("accountantiq/data/workspaces").absolute())
        )
        self.db = self.workspace.get_database()
        self.suggester = AISuggester(use_llm=use_llm)
        self.session_stats = {
            'reviewed': 0,
            'coded': 0,
            'skipped': 0,
            'rules_created': 0,
            'start_time': time.time()
        }

    def run(self):
        """Run the interactive dashboard."""
        console.clear()
        self._show_welcome()

        # Get uncoded transactions
        bank_txns = self.db.get_transactions(source="bank")
        uncoded = [
            t for t in bank_txns
            if not t.get('nominal_code') or not t.get('nominal_code').strip()
        ]

        if not uncoded:
            console.print("\n✓ [green]All transactions are coded![/green]\n")
            return

        # Group by vendor and sort by count (most common first)
        from collections import defaultdict
        by_vendor = defaultdict(list)
        for txn in uncoded:
            by_vendor[txn['vendor']].append(txn)

        # Sort vendors by transaction count (descending)
        sorted_vendors = sorted(
            by_vendor.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        console.print(f"\n[yellow]Found {len(uncoded)} uncoded transactions from {len(sorted_vendors)} vendors[/yellow]")
        console.print(f"[cyan]💡 Tip: Most common vendors shown first - create rules to batch-code![/cyan]\n")

        # Review loop - one transaction per vendor group
        total_vendors = len(sorted_vendors)
        for i, (vendor, txns) in enumerate(sorted_vendors):
            # Show the first transaction from this vendor group
            txn = txns[0]
            should_continue = self._review_vendor_group(
                vendor, txns, i + 1, total_vendors
            )
            if not should_continue:
                break

            # Check if we auto-coded the rest via rule
            # Refresh uncoded list
            bank_txns = self.db.get_transactions(source="bank")
            uncoded_now = [
                t for t in bank_txns
                if not t.get('nominal_code') or not t.get('nominal_code').strip()
            ]

            if len(uncoded_now) == 0:
                console.print("\n[green]✓ All transactions coded![/green]")
                break

        # Show final stats
        self._show_final_stats()

        self.db.close()

    def _show_welcome(self):
        """Show welcome banner."""
        welcome_text = """
[bold cyan]AccountantIQ - Interactive Review Dashboard[/bold cyan]

Review uncoded transactions with AI-powered suggestions.
Code manually, create rules, and improve accuracy.
        """
        console.print(Panel(welcome_text, box=box.DOUBLE, border_style="cyan"))

    def _review_vendor_group(self, vendor: str, txns: list, current: int, total: int) -> bool:
        """
        Review a vendor group (shows first transaction, applies code to all).

        Returns:
            True to continue, False to quit
        """
        console.clear()

        # Header with vendor group info
        count = len(txns)
        progress = f"Vendor {current}/{total}"
        console.print(f"\n[bold cyan]{progress}[/bold cyan]")
        console.print(f"[bold yellow]📦 {vendor}[/bold yellow] [dim]({count} transactions)[/dim]")
        console.print("─" * 80)

        # Show representative transaction (first one)
        txn = txns[0]
        console.print("\n[bold]Representative Transaction:[/bold]")
        self._show_transaction_details(txn)

        # Show all amounts in this group
        if count > 1:
            console.print(f"\n[dim]All amounts for this vendor:[/dim]")
            amounts = [float(t['amount']) for t in txns]
            amount_summary = ", ".join([f"£{a:.2f}" for a in amounts[:10]])
            if count > 10:
                amount_summary += f"... (+{count-10} more)"
            console.print(f"[dim]{amount_summary}[/dim]")

        # Get AI suggestions
        suggestions = self.suggester.suggest(
            txn,
            nominal_codes=STANDARD_NOMINAL_CODES
        )

        # Show suggestions
        if suggestions:
            console.print("\n[bold yellow]💡 AI Suggestions:[/bold yellow]")
            self._show_suggestions(suggestions)

        # Show nominal code reference
        console.print("\n[bold cyan]📋 Common Nominal Codes:[/bold cyan]")
        self._show_nominal_codes_quick_ref()

        # Get user action
        console.print("\n[bold green]Actions:[/bold green]")
        console.print(f"  [1-9] - Select suggested code (applies to ALL {count} transactions)")
        console.print("  [c]   - Enter custom code")
        console.print("  [s]   - Skip this vendor")
        console.print("  [q]   - Quit and save progress")
        console.print("  [?]   - Show all nominal codes")

        choice = Prompt.ask(
            "\n[bold]Your choice[/bold]",
            default="s"
        )

        if choice.lower() == 'q':
            return False
        elif choice.lower() == 's':
            self.session_stats['skipped'] += count
            self.session_stats['reviewed'] += count
            return True
        elif choice.lower() == '?':
            self._show_all_nominal_codes()
            return self._review_vendor_group(vendor, txns, current, total)
        elif choice.lower() == 'c':
            return self._handle_custom_code_batch(vendor, txns, current, total)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                code, reason, conf = suggestions[idx]
                return self._handle_code_selection_batch(vendor, txns, code, reason)
            else:
                console.print("[red]Invalid choice[/red]")
                time.sleep(1)
                return self._review_vendor_group(vendor, txns, current, total)
        else:
            console.print("[red]Invalid choice[/red]")
            time.sleep(1)
            return self._review_vendor_group(vendor, txns, current, total)

    def _review_transaction(self, txn: dict, current: int, total: int) -> bool:
        """
        Review a single transaction.

        Returns:
            True to continue, False to quit
        """
        console.clear()

        # Header
        progress = f"Transaction {current}/{total}"
        console.print(f"\n[bold cyan]{progress}[/bold cyan]")
        console.print("─" * 80)

        # Transaction details
        self._show_transaction_details(txn)

        # Get AI suggestions
        suggestions = self.suggester.suggest(
            txn,
            nominal_codes=STANDARD_NOMINAL_CODES
        )

        # Show suggestions
        if suggestions:
            console.print("\n[bold yellow]💡 AI Suggestions:[/bold yellow]")
            self._show_suggestions(suggestions)

        # Show nominal code reference
        console.print("\n[bold cyan]📋 Common Nominal Codes:[/bold cyan]")
        self._show_nominal_codes_quick_ref()

        # Get user action
        console.print("\n[bold green]Actions:[/bold green]")
        console.print("  [1-9] - Select suggested code")
        console.print("  [c]   - Enter custom code")
        console.print("  [s]   - Skip this transaction")
        console.print("  [q]   - Quit and save progress")
        console.print("  [?]   - Show all nominal codes")

        choice = Prompt.ask(
            "\n[bold]Your choice[/bold]",
            default="s"
        )

        if choice.lower() == 'q':
            return False
        elif choice.lower() == 's':
            self.session_stats['skipped'] += 1
            self.session_stats['reviewed'] += 1
            return True
        elif choice.lower() == '?':
            self._show_all_nominal_codes()
            return self._review_transaction(txn, current, total)
        elif choice.lower() == 'c':
            return self._handle_custom_code(txn, current, total)
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                code, reason, conf = suggestions[idx]
                return self._handle_code_selection(txn, code, reason, current, total)
            else:
                console.print("[red]Invalid choice[/red]")
                time.sleep(1)
                return self._review_transaction(txn, current, total)
        else:
            console.print("[red]Invalid choice[/red]")
            time.sleep(1)
            return self._review_transaction(txn, current, total)

    def _show_transaction_details(self, txn: dict):
        """Show transaction details in a nice table."""
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
        table.add_column("Field", style="cyan", width=15)
        table.add_column("Value", style="white")

        amount = float(txn['amount'])
        amount_str = f"£{amount:.2f}" if amount > 0 else f"-£{abs(amount):.2f}"
        amount_style = "green" if amount > 0 else "red"

        table.add_row("Date", str(txn['date']))
        table.add_row("Vendor", txn['vendor'])
        table.add_row("Amount", Text(amount_str, style=amount_style))

        if txn.get('reference'):
            table.add_row("Reference", txn['reference'])

        if txn.get('details'):
            details = txn['details'][:80]
            table.add_row("Details", details)

        console.print(table)

    def _show_suggestions(self, suggestions):
        """Show AI suggestions in a table."""
        table = Table(box=box.ROUNDED, show_header=True, padding=(0, 1))
        table.add_column("#", style="cyan", width=3)
        table.add_column("Code", style="yellow", width=6)
        table.add_column("Description", style="white", width=40)
        table.add_column("Confidence", style="green", width=10)

        for i, (code, reason, conf) in enumerate(suggestions, 1):
            conf_pct = f"{conf*100:.0f}%"
            conf_style = "green" if conf > 0.8 else "yellow" if conf > 0.6 else "red"

            # Get code description
            desc = STANDARD_NOMINAL_CODES.get(code, reason)

            table.add_row(
                str(i),
                code,
                desc[:40],
                Text(conf_pct, style=conf_style)
            )

        console.print(table)

    def _show_nominal_codes_quick_ref(self):
        """Show quick reference of common codes."""
        codes = [
            ("1210", "Bank Account"),
            ("5000", "Purchases"),
            ("7100", "IT/Software"),
            ("7200", "Utilities"),
            ("7400", "Travel/Food"),
            ("7500", "Motor"),
            ("7600", "Prof Fees"),
        ]

        text = " | ".join([f"[cyan]{code}[/cyan]: {desc}" for code, desc in codes])
        console.print(text)

    def _show_all_nominal_codes(self):
        """Show all nominal codes."""
        console.clear()
        console.print("\n[bold cyan]All Nominal Codes[/bold cyan]\n")

        table = Table(box=box.ROUNDED)
        table.add_column("Code", style="cyan", width=8)
        table.add_column("Description", style="white")

        for code, desc in sorted(STANDARD_NOMINAL_CODES.items()):
            table.add_row(code, desc)

        console.print(table)
        Prompt.ask("\n[dim]Press Enter to continue[/dim]")

    def _handle_code_selection(
        self,
        txn: dict,
        code: str,
        reason: str,
        current: int,
        total: int
    ) -> bool:
        """Handle user selecting a code."""

        # Confirm
        desc = STANDARD_NOMINAL_CODES.get(code, "Unknown")
        console.print(f"\n[yellow]Selected: {code} - {desc}[/yellow]")

        # Ask if should create rule
        create_rule = Confirm.ask(
            "Create rule for this vendor?",
            default=True
        )

        # Update transaction
        self.db.update_transaction(txn['id'], {
            'nominal_code': code,
            'confidence': 1.0,
            'assigned_by': 'manual_review',
            'reviewed': True
        })

        self.session_stats['coded'] += 1
        self.session_stats['reviewed'] += 1

        # Create rule if requested
        if create_rule:
            rule_id = self.db.insert_rule({
                'vendor_pattern': txn['vendor'],
                'nominal_code': code,
                'rule_type': 'exact',
                'confidence': 1.0,
                'created_by': 'reviewer'
            })
            self.session_stats['rules_created'] += 1
            console.print(f"[green]✓ Rule created (ID: {rule_id})[/green]")

        console.print("[green]✓ Transaction coded[/green]")
        time.sleep(0.5)

        return True

    def _handle_code_selection_batch(
        self,
        vendor: str,
        txns: list,
        code: str,
        reason: str
    ) -> bool:
        """Handle user selecting a code for a batch of transactions."""

        count = len(txns)
        desc = STANDARD_NOMINAL_CODES.get(code, "Unknown")
        console.print(f"\n[yellow]Selected: {code} - {desc}[/yellow]")
        console.print(f"[yellow]This will code ALL {count} transactions for '{vendor}'[/yellow]")

        # Confirm
        if not Confirm.ask("Confirm batch coding?", default=True):
            return self._review_vendor_group(vendor, txns, 1, 1)

        # Create rule first
        rule_id = self.db.insert_rule({
            'vendor_pattern': vendor,
            'nominal_code': code,
            'rule_type': 'exact',
            'confidence': 1.0,
            'created_by': 'reviewer'
        })

        # Update all transactions
        for txn in txns:
            self.db.update_transaction(txn['id'], {
                'nominal_code': code,
                'confidence': 1.0,
                'assigned_by': 'manual_review',
                'reviewed': True
            })

        self.session_stats['coded'] += count
        self.session_stats['reviewed'] += count
        self.session_stats['rules_created'] += 1

        console.print(f"[green]✓ Coded {count} transactions[/green]")
        console.print(f"[green]✓ Rule created (ID: {rule_id})[/green]")
        time.sleep(1)

        return True

    def _handle_custom_code_batch(
        self,
        vendor: str,
        txns: list,
        current: int,
        total: int
    ) -> bool:
        """Handle user entering custom code for batch."""

        code = Prompt.ask("\n[bold]Enter nominal code[/bold]")

        # Validate code format
        if not code.isdigit() or len(code) != 4:
            console.print("[red]Invalid code format (must be 4 digits)[/red]")
            time.sleep(1)
            return self._review_vendor_group(vendor, txns, current, total)

        # Show description if known
        desc = STANDARD_NOMINAL_CODES.get(code, "Custom code")
        count = len(txns)
        console.print(f"[yellow]{code} - {desc}[/yellow]")
        console.print(f"[yellow]This will code ALL {count} transactions for '{vendor}'[/yellow]")

        # Confirm
        if not Confirm.ask("Confirm batch coding?", default=True):
            return self._review_vendor_group(vendor, txns, current, total)

        # Create rule first
        rule_id = self.db.insert_rule({
            'vendor_pattern': vendor,
            'nominal_code': code,
            'rule_type': 'exact',
            'confidence': 1.0,
            'created_by': 'reviewer'
        })

        # Update all transactions
        for txn in txns:
            self.db.update_transaction(txn['id'], {
                'nominal_code': code,
                'confidence': 1.0,
                'assigned_by': 'manual_review',
                'reviewed': True
            })

        self.session_stats['coded'] += count
        self.session_stats['reviewed'] += count
        self.session_stats['rules_created'] += 1

        console.print(f"[green]✓ Coded {count} transactions[/green]")
        console.print(f"[green]✓ Rule created (ID: {rule_id})[/green]")
        time.sleep(1)

        return True

    def _handle_custom_code(self, txn: dict, current: int, total: int) -> bool:
        """Handle user entering custom code."""

        code = Prompt.ask("\n[bold]Enter nominal code[/bold]")

        # Validate code format
        if not code.isdigit() or len(code) != 4:
            console.print("[red]Invalid code format (must be 4 digits)[/red]")
            time.sleep(1)
            return self._review_transaction(txn, current, total)

        # Show description if known
        desc = STANDARD_NOMINAL_CODES.get(code, "Custom code")
        console.print(f"[yellow]{code} - {desc}[/yellow]")

        # Confirm
        if not Confirm.ask("Confirm?", default=True):
            return self._review_transaction(txn, current, total)

        # Ask if should create rule
        create_rule = Confirm.ask(
            "Create rule for this vendor?",
            default=True
        )

        # Update transaction
        self.db.update_transaction(txn['id'], {
            'nominal_code': code,
            'confidence': 1.0,
            'assigned_by': 'manual_review',
            'reviewed': True
        })

        self.session_stats['coded'] += 1
        self.session_stats['reviewed'] += 1

        # Create rule if requested
        if create_rule:
            rule_id = self.db.insert_rule({
                'vendor_pattern': txn['vendor'],
                'nominal_code': code,
                'rule_type': 'exact',
                'confidence': 1.0,
                'created_by': 'reviewer'
            })
            self.session_stats['rules_created'] += 1
            console.print(f"[green]✓ Rule created (ID: {rule_id})[/green]")

        console.print("[green]✓ Transaction coded[/green]")
        time.sleep(0.5)

        return True

    def _show_final_stats(self):
        """Show final session statistics."""
        console.clear()

        duration = int(time.time() - self.session_stats['start_time'])
        minutes = duration // 60
        seconds = duration % 60

        stats_text = f"""
[bold cyan]Review Session Complete![/bold cyan]

[green]Reviewed:[/green]    {self.session_stats['reviewed']} transactions
[green]Coded:[/green]       {self.session_stats['coded']} transactions
[yellow]Skipped:[/yellow]     {self.session_stats['skipped']} transactions
[cyan]Rules Created:[/cyan] {self.session_stats['rules_created']} new rules

[dim]Duration: {minutes}m {seconds}s[/dim]

[bold green]✓ Progress saved to database[/bold green]
        """

        console.print(Panel(stats_text, box=box.DOUBLE, border_style="green"))

        # Show export reminder
        if self.session_stats['coded'] > 0:
            console.print("\n[yellow]💡 Don't forget to re-export for Sage 50:[/yellow]")
            console.print("   python -m accountantiq.cli export production")


def main():
    """Main entry point."""
    import sys

    # Check for LLM flag
    use_llm = "--llm" in sys.argv
    workspace = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else "production"

    if use_llm:
        console.print("[cyan]🤖 LLM suggestions enabled[/cyan]")
        console.print("[dim]Requires OPENAI_API_KEY or ANTHROPIC_API_KEY env var[/dim]\n")

    dashboard = ReviewDashboard(workspace_name=workspace, use_llm=use_llm)
    dashboard.run()


if __name__ == "__main__":
    main()
