#!/usr/bin/env python3
"""
AccountantIQ - Process New Bank Statement
==========================================

Complete workflow to auto-code a new unknown bank statement using learned rules.

Usage:
    python process_new_statement.py <bank_statement.csv>

Example:
    python process_new_statement.py data/NewBankStatement_May2024.csv

This will:
1. Create a new workspace (or use existing)
2. Load learned rules from historical Sage data
3. Parse the new bank statement
4. Auto-code transactions using learned rules
5. Export coded transactions to Sage 50 import format
"""

import sys
from pathlib import Path

from accountantiq.core.workspace import WorkspaceManager
from accountantiq.agents.parser_agent.parser_agent import ParserAgent
from accountantiq.agents.learner_agent.learner_agent import LearnerAgent
from accountantiq.agents.classifier_agent.classifier_agent import ClassifierAgent
from accountantiq.agents.exporter_agent.exporter_agent import ExporterAgent


def process_new_statement(bank_csv_path: str, sage_csv_path: str = None, workspace_name: str = "production"):
    """
    Process a new unknown bank statement.

    Args:
        bank_csv_path: Path to new bank statement CSV
        sage_csv_path: Path to historical Sage data (optional, for learning rules)
        workspace_name: Name of workspace to use
    """

    # Initialize workspace
    print(f"\n{'='*60}")
    print(f"AccountantIQ - Processing New Bank Statement")
    print(f"{'='*60}\n")

    wm = WorkspaceManager()

    # Create or load workspace
    if wm.workspace_exists(workspace_name):
        print(f"✓ Loading existing workspace: {workspace_name}")
        workspace = wm.get_workspace(workspace_name)
    else:
        print(f"✓ Creating new workspace: {workspace_name}")
        workspace = wm.create_workspace(workspace_name)

    workspace_path = str(workspace.workspace_path)

    # Step 1: Parse historical Sage data (if provided)
    if sage_csv_path:
        print(f"\n{'─'*60}")
        print("STEP 1: Parsing historical Sage data...")
        print(f"{'─'*60}")

        parser = ParserAgent(workspace_path)
        result = parser.run(sage_csv_path, file_type="sage")
        print(f"✓ Parsed {result.stats['rows_inserted']} historical Sage transactions")
    else:
        print(f"\n{'─'*60}")
        print("STEP 1: Using existing rules (no historical data provided)")
        print(f"{'─'*60}")

    # Step 2: Parse new bank statement
    print(f"\n{'─'*60}")
    print("STEP 2: Parsing new bank statement...")
    print(f"{'─'*60}")

    parser = ParserAgent(workspace_path)
    result = parser.run(bank_csv_path, file_type="bank")
    print(f"✓ Parsed {result.stats['rows_inserted']} new bank transactions")

    # Step 3: Learn rules (if we have historical data)
    if sage_csv_path:
        print(f"\n{'─'*60}")
        print("STEP 3: Learning rules from Sage + Bank data...")
        print(f"{'─'*60}")

        learner = LearnerAgent(workspace_path)
        result = learner.run(smart_matching=True)
        smart = result.stats.get('smart_rules', 0)
        fuzzy = result.stats.get('basic_rules', 0)
        total = result.stats['rules_generated']
        print(f"✓ Learned {total} rules ({smart} smart + {fuzzy} fuzzy)")
    else:
        print(f"\n{'─'*60}")
        print("STEP 3: Using existing learned rules")
        print(f"{'─'*60}")
        db = workspace.get_database()
        rules = db.get_rules()
        print(f"✓ Found {len(rules)} existing rules in workspace")
        db.close()

    # Step 4: Auto-code transactions
    print(f"\n{'─'*60}")
    print("STEP 4: Auto-coding transactions with learned rules...")
    print(f"{'─'*60}")

    classifier = ClassifierAgent(workspace_path)
    result = classifier.run()

    coded = result.stats['auto_coded']
    exceptions = result.stats.get('exceptions', 0)
    confidence = result.stats.get('avg_confidence', 0.0)

    # Get total count from database
    db = workspace.get_database()
    bank_txns = db.get_transactions(source="bank")
    total = len(bank_txns)
    db.close()

    if coded > 0:
        print(f"✓ Auto-coded {coded} transactions")
        print(f"✓ Total bank transactions: {total}")
        print(f"✓ Coverage: {coded/total*100:.1f}% ({exceptions} exceptions)")
        print(f"✓ Average confidence: {confidence:.2f}")
    else:
        print(f"✓ All transactions already coded")

    # Step 5: Export to Sage format
    print(f"\n{'─'*60}")
    print("STEP 5: Exporting to Sage 50 import format...")
    print(f"{'─'*60}")

    exporter = ExporterAgent(workspace_path)
    result = exporter.run(output_filename="sage_import.csv")

    output_file = result.stats['output_file']
    exported = result.stats['transactions_exported']

    print(f"✓ Exported {exported} coded transactions")
    print(f"✓ Output file: {output_file}")

    # Summary
    print(f"\n{'='*60}")
    print("COMPLETE! Next steps:")
    print(f"{'='*60}")
    print(f"1. Review the export file: {output_file}")
    print(f"2. Import into Sage 50:")
    print(f"   - File → Import")
    print(f"   - Select CSV format")
    print(f"   - Choose: {output_file}")
    print(f"   - Map columns: Date, Type, Nominal Code, Reference, Details, Debit, Credit")
    print(f"3. Verify transactions in Sage 50")
    print(f"\n{'='*60}\n")

    # Show uncoded transactions if any
    uncoded = total - coded
    if uncoded > 0:
        print(f"⚠ NOTE: {uncoded} transactions could not be auto-coded")
        print(f"        These require manual review and coding")
        print(f"        Run the Reviewer Agent to code these manually\n")

    return output_file


def main():
    """Command-line interface."""

    if len(sys.argv) < 2:
        print("Usage: python process_new_statement.py <bank_statement.csv> [sage_historical.csv] [workspace_name]")
        print("\nExamples:")
        print("  # Process new statement using existing rules:")
        print("  python process_new_statement.py data/NewStatement.csv")
        print()
        print("  # Process and learn from historical Sage data:")
        print("  python process_new_statement.py data/NewStatement.csv data/AUDITDL2.csv")
        print()
        print("  # Use custom workspace name:")
        print("  python process_new_statement.py data/NewStatement.csv data/AUDITDL2.csv my_company")
        sys.exit(1)

    bank_csv = sys.argv[1]
    sage_csv = sys.argv[2] if len(sys.argv) > 2 else None
    workspace = sys.argv[3] if len(sys.argv) > 3 else "production"

    if not Path(bank_csv).exists():
        print(f"ERROR: Bank statement file not found: {bank_csv}")
        sys.exit(1)

    if sage_csv and not Path(sage_csv).exists():
        print(f"ERROR: Sage file not found: {sage_csv}")
        sys.exit(1)

    process_new_statement(bank_csv, sage_csv, workspace)


if __name__ == "__main__":
    main()
