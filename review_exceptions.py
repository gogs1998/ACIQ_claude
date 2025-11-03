#!/usr/bin/env python3
"""
Interactive review tool for uncoded transactions.
Shows exceptions and allows manual coding.
"""

from accountantiq.core.workspace import Workspace
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def review_exceptions(workspace_name: str = "production"):
    """Review and manually code uncoded transactions."""

    workspace = Workspace(workspace_name, str(Path("accountantiq/data/workspaces").absolute()))
    db = workspace.get_database()

    # Get uncoded transactions
    bank_txns = db.get_transactions(source="bank")
    uncoded = [t for t in bank_txns if not t.get('nominal_code') or not t.get('nominal_code').strip()]

    if not uncoded:
        print("✓ All transactions are already coded!")
        db.close()
        return

    # Group by vendor for batch coding
    by_vendor = defaultdict(list)
    for txn in uncoded:
        by_vendor[txn['vendor']].append(txn)

    print("=" * 80)
    print(f"REVIEW EXCEPTIONS - {len(uncoded)} uncoded transactions from {len(by_vendor)} vendors")
    print("=" * 80)

    # Show summary
    print("\n📊 SUMMARY BY VENDOR:")
    print("-" * 80)
    print(f"{'Count':<8} {'Vendor':<40} {'Example Amount':<15}")
    print("-" * 80)

    vendor_list = sorted(by_vendor.items(), key=lambda x: len(x[1]), reverse=True)
    for vendor, txns in vendor_list[:30]:  # Show top 30
        example_amount = f"£{float(txns[0]['amount']):.2f}"
        print(f"{len(txns):<8} {vendor:<40} {example_amount:<15}")

    if len(vendor_list) > 30:
        remaining = len(vendor_list) - 30
        print(f"\n... and {remaining} more vendors")

    # Show detailed examples
    print("\n" + "=" * 80)
    print("DETAILED EXAMPLES (showing first 20 transactions)")
    print("=" * 80)

    for i, txn in enumerate(uncoded[:20]):
        amount = float(txn['amount'])
        amount_str = f"£{amount:.2f}" if amount > 0 else f"-£{abs(amount):.2f}"

        print(f"\n{i+1}. {txn['date']} | {amount_str:>12} | {txn['vendor']}")
        if txn.get('details'):
            print(f"   Details: {txn['details'][:70]}")
        if txn.get('reference'):
            print(f"   Ref: {txn['reference'][:70]}")

    if len(uncoded) > 20:
        print(f"\n... and {len(uncoded) - 20} more transactions")

    # Export uncoded to CSV for manual review
    export_path = workspace.workspace_path / "exports" / "uncoded_transactions.csv"

    print("\n" + "=" * 80)
    print("EXPORTING UNCODED TRANSACTIONS")
    print("=" * 80)

    import csv
    with open(export_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Transaction ID',
            'Date',
            'Vendor',
            'Amount',
            'Reference',
            'Details',
            'Suggested Nominal Code'
        ])

        for txn in uncoded:
            # Try to suggest a nominal code based on keywords
            suggested = suggest_nominal_code(txn['vendor'], txn.get('details', ''))

            writer.writerow([
                txn['id'],
                txn['date'],
                txn['vendor'],
                f"{float(txn['amount']):.2f}",
                txn.get('reference', ''),
                txn.get('details', ''),
                suggested
            ])

    print(f"✓ Exported to: {export_path}")
    print(f"\nYou can:")
    print(f"1. Review the CSV file")
    print(f"2. Add nominal codes in Excel/Sheets")
    print(f"3. Use the Reviewer Agent for interactive coding")

    # Show statistics
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)

    total_bank = len(bank_txns)
    coded = total_bank - len(uncoded)
    coverage = (coded / total_bank * 100) if total_bank > 0 else 0

    print(f"Total transactions: {total_bank}")
    print(f"Auto-coded:        {coded} ({coverage:.1f}%)")
    print(f"Need review:       {len(uncoded)} ({100-coverage:.1f}%)")

    # Analyze exception types
    print("\n📋 EXCEPTION CATEGORIES:")
    print("-" * 80)

    categories = categorize_exceptions(uncoded)
    for category, txns in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
        pct = len(txns) / len(uncoded) * 100
        print(f"{category:<30} {len(txns):>4} ({pct:>5.1f}%)")

    db.close()

    return export_path


def suggest_nominal_code(vendor: str, details: str = '') -> str:
    """Suggest a nominal code based on vendor/details keywords."""
    vendor_lower = vendor.lower()
    details_lower = details.lower() if details else ''
    combined = vendor_lower + ' ' + details_lower

    # Common patterns
    if any(x in combined for x in ['apple', 'microsoft', 'google', 'software', 'subscription']):
        return '7100'  # Software/IT
    elif any(x in combined for x in ['hotel', 'restaurant', 'cafe', 'food', 'eat']):
        return '7400'  # Travel & Subsistence
    elif any(x in combined for x in ['parking', 'fuel', 'petrol', 'diesel', 'uber', 'taxi']):
        return '7500'  # Motor expenses
    elif any(x in combined for x in ['insurance']):
        return '7104'  # Insurance
    elif any(x in combined for x in ['medical', 'dental', 'pharma', 'health']):
        return '7200'  # Medical/Health
    elif any(x in combined for x in ['professional', 'membership', 'subscription', 'gdc']):
        return '7600'  # Professional fees
    elif any(x in combined for x in ['stationery', 'office', 'supplies']):
        return '7300'  # Office supplies
    elif any(x in combined for x in ['amazon', 'ebay', 'purchase']):
        return '5000'  # Purchases
    elif any(x in combined for x in ['tesco', 'sainsbury', 'asda', 'supermarket']):
        return '7400'  # Subsistence
    else:
        return '????'  # Unknown - needs review


def categorize_exceptions(transactions: list) -> dict:
    """Categorize uncoded transactions by type."""
    categories = defaultdict(list)

    for txn in transactions:
        vendor = txn['vendor'].lower()
        details = txn.get('details', '').lower()
        combined = vendor + ' ' + details

        if any(x in combined for x in ['apple', 'microsoft', 'google', 'software']):
            categories['IT & Software'].append(txn)
        elif any(x in combined for x in ['hotel', 'restaurant', 'cafe', 'bar']):
            categories['Hospitality'].append(txn)
        elif any(x in combined for x in ['parking', 'uber', 'taxi', 'fuel']):
            categories['Travel & Motor'].append(txn)
        elif any(x in combined for x in ['medical', 'dental', 'pharma', 'health']):
            categories['Medical/Health'].append(txn)
        elif any(x in combined for x in ['insurance']):
            categories['Insurance'].append(txn)
        elif any(x in combined for x in ['amazon', 'ebay', 'purchase']):
            categories['Purchases/Supplies'].append(txn)
        elif any(x in combined for x in ['tesco', 'sainsbury', 'supermarket']):
            categories['Groceries/Food'].append(txn)
        elif any(x in combined for x in ['professional', 'membership', 'gdc', 'subscription']):
            categories['Professional Fees'].append(txn)
        else:
            categories['Other/Unknown'].append(txn)

    return categories


if __name__ == "__main__":
    import sys
    workspace = sys.argv[1] if len(sys.argv) > 1 else "production"
    review_exceptions(workspace)
