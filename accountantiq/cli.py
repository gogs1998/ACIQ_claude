"""
CLI interface for AccountantIQ multi-agent system.
"""

import typer
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table

from accountantiq.core.workspace import WorkspaceManager, Workspace
from accountantiq.orchestrator import AccountantOrchestrator

app = typer.Typer(
    name="accountantiq",
    help="AccountantIQ - Autonomous bookkeeping with multi-agent AI",
    add_completion=False
)

workspace_app = typer.Typer(help="Workspace management commands")
app.add_typer(workspace_app, name="workspace")

rules_app = typer.Typer(help="Rules management commands")
app.add_typer(rules_app, name="rules")

console = Console()


# Main processing commands

@app.command()
def process(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    sage: Optional[str] = typer.Option(None, "--sage", "-s", help="Sage 50 export CSV file"),
    bank: Optional[str] = typer.Option(None, "--bank", "-b", help="Bank statement CSV file"),
    output: str = typer.Option("sage_import.csv", "--output", "-o", help="Output filename"),
    no_review: bool = typer.Option(False, "--no-review", help="Skip interactive review")
):
    """
    Run full processing pipeline: parse → learn → classify → review → export.
    """
    try:
        orchestrator = AccountantOrchestrator(workspace)
        results = orchestrator.run_full_pipeline(
            sage_file=sage,
            bank_file=bank,
            output_file=output,
            interactive_review=not no_review
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def parse(
    file_type: str = typer.Argument(..., help="File type: 'sage' or 'bank'"),
    file: str = typer.Option(..., "--file", "-f", help="CSV file path"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name")
):
    """
    Parse a CSV file (Sage or bank statement).
    """
    try:
        orchestrator = AccountantOrchestrator(workspace)

        if file_type == "sage":
            result = orchestrator.parse_sage(file)
        elif file_type == "bank":
            result = orchestrator.parse_bank(file)
        else:
            console.print(f"[red]Error:[/red] Unknown file type '{file_type}'. Use 'sage' or 'bank'.")
            raise typer.Exit(1)

        if result.status == "complete":
            console.print(
                f"[green]✓[/green] Parsed {result.stats['rows_inserted']} transactions"
            )
        else:
            console.print(f"[red]Error:[/red] {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def learn(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    min_confidence: float = typer.Option(0.75, "--min-confidence", "-c", help="Minimum rule confidence")
):
    """
    Learn vendor patterns from historical data.
    """
    try:
        orchestrator = AccountantOrchestrator(workspace)
        result = orchestrator.learn_patterns(min_confidence=min_confidence)

        if result.status == "complete":
            console.print(
                f"[green]✓[/green] Generated {result.stats['rules_generated']} rules "
                f"from {result.stats['unique_vendors']} vendors"
            )
        else:
            console.print(f"[red]Error:[/red] {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def classify(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    threshold: float = typer.Option(0.70, "--threshold", "-t", help="Confidence threshold")
):
    """
    Classify uncoded bank transactions.
    """
    try:
        orchestrator = AccountantOrchestrator(workspace)
        result = orchestrator.classify_transactions(confidence_threshold=threshold)

        if result.status == "complete":
            console.print(
                f"[green]✓[/green] Auto-coded {result.stats['auto_coded']}/{result.stats['processed']} "
                f"transactions ({result.stats['exceptions']} exceptions)"
            )
        else:
            console.print(f"[red]Error:[/red] {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def review(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Non-interactive mode")
):
    """
    Review low-confidence transactions.
    """
    try:
        orchestrator = AccountantOrchestrator(workspace)
        result = orchestrator.review_exceptions(interactive=not non_interactive)

        if result.status == "complete":
            console.print(
                f"[green]✓[/green] Reviewed {result.stats['reviewed']} transactions"
            )
        else:
            console.print(f"[red]Error:[/red] {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def export(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    output: str = typer.Option("sage_import.csv", "--output", "-o", help="Output filename")
):
    """
    Export coded transactions to Sage format.
    """
    try:
        orchestrator = AccountantOrchestrator(workspace)
        result = orchestrator.export_transactions(output_filename=output)

        if result.status == "complete":
            console.print(
                f"[green]✓[/green] Exported {result.stats['transactions_exported']} "
                f"transactions to {result.stats['output_file']}"
            )
        else:
            console.print(f"[red]Error:[/red] {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def stats(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name")
):
    """
    Display workspace statistics.
    """
    try:
        orchestrator = AccountantOrchestrator(workspace)
        orchestrator.display_stats()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# Workspace management commands

@workspace_app.command("create")
def workspace_create(
    name: str = typer.Argument(..., help="Workspace name"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite if exists")
):
    """
    Create a new workspace.
    """
    try:
        manager = WorkspaceManager()

        if manager.workspace_exists(name) and not overwrite:
            console.print(
                f"[red]Error:[/red] Workspace '{name}' already exists. "
                "Use --overwrite to recreate."
            )
            raise typer.Exit(1)

        workspace = manager.create_workspace(name, overwrite=overwrite)
        console.print(f"[green]✓[/green] Created workspace: {workspace.workspace_path}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workspace_app.command("list")
def workspace_list():
    """
    List all workspaces.
    """
    try:
        manager = WorkspaceManager()
        workspaces = manager.list_workspaces()

        if not workspaces:
            console.print("No workspaces found.")
            return

        table = Table(title="Workspaces")
        table.add_column("Name", style="cyan")

        for name in workspaces:
            table.add_row(name)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@workspace_app.command("delete")
def workspace_delete(
    name: str = typer.Argument(..., help="Workspace name"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm deletion")
):
    """
    Delete a workspace.
    """
    try:
        if not confirm:
            console.print(
                f"[yellow]Warning:[/yellow] This will permanently delete workspace '{name}'. "
                "Use --confirm to proceed."
            )
            raise typer.Exit(1)

        manager = WorkspaceManager()
        manager.delete_workspace(name, confirm=True)
        console.print(f"[green]✓[/green] Deleted workspace: {name}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# Rules management commands

@rules_app.command("list")
def rules_list(
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    min_confidence: Optional[float] = typer.Option(None, "--min-confidence", "-c", help="Filter by confidence")
):
    """
    List rules in workspace.
    """
    try:
        ws = Workspace(workspace)
        ws.load()

        with ws.get_database() as db:
            rules = db.get_rules(min_confidence=min_confidence)

        if not rules:
            console.print("No rules found.")
            return

        table = Table(title=f"Rules in {workspace}")
        table.add_column("ID", style="cyan")
        table.add_column("Vendor Pattern", style="yellow")
        table.add_column("Nominal Code", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Confidence", style="magenta")
        table.add_column("Matches", style="white")

        for rule in rules:
            table.add_row(
                str(rule['id']),
                rule['vendor_pattern'],
                rule['nominal_code'],
                rule['rule_type'],
                f"{float(rule['confidence']):.1%}",
                str(rule['match_count'])
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@rules_app.command("delete")
def rules_delete(
    rule_id: int = typer.Argument(..., help="Rule ID to delete"),
    workspace: str = typer.Option(..., "--workspace", "-w", help="Workspace name"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm deletion")
):
    """
    Delete a rule.
    """
    try:
        if not confirm:
            console.print(
                f"[yellow]Warning:[/yellow] This will delete rule {rule_id}. "
                "Use --confirm to proceed."
            )
            raise typer.Exit(1)

        ws = Workspace(workspace)
        ws.load()

        with ws.get_database() as db:
            db.delete_rule(rule_id)

        console.print(f"[green]✓[/green] Deleted rule {rule_id}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
