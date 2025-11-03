#!/usr/bin/env python3
"""Simple test of chat interface without full LLM."""

from pathlib import Path
from accountantiq.core.workspace import Workspace

def process_command(command: str, db):
    """Process natural language command (simplified)."""

    command_lower = command.lower()

    # Change code command
    if "change" in command_lower or "update" in command_lower or "recode" in command_lower:
        # Extract vendor and code
        import re

        # Look for pattern like "vendor to 7403"
        match = re.search(r'([\w\s&*]+?)\s+(?:to|as|→)\s+(\d{4})', command)
        if match:
            vendor_pattern = match.group(1).strip()
            new_code = match.group(2)

            # Find transactions
            bank_txns = db.get_transactions(source="bank")
            matching = [t for t in bank_txns
                       if vendor_pattern.lower() in t['vendor'].lower()]

            if matching:
                # Update transactions
                for txn in matching:
                    db.update_transaction(txn['id'], {
                        'nominal_code': new_code,
                        'confidence': 1.0,
                        'assigned_by': 'chat',
                        'reviewed': True
                    })

                # Create rule
                db.conn.execute("DELETE FROM rules WHERE vendor_pattern = ?",
                               [matching[0]['vendor']])

                rule_id = db.insert_rule({
                    'vendor_pattern': matching[0]['vendor'],
                    'nominal_code': new_code,
                    'rule_type': 'exact',
                    'confidence': 1.0,
                    'created_by': 'reviewer'
                })

                return f"✓ Updated {len(matching)} transactions for '{matching[0]['vendor']}' → {new_code}\n✓ Rule created (ID: {rule_id})"
            else:
                return f"No transactions found matching: {vendor_pattern}"

    # Stats command
    elif "coverage" in command_lower or "stats" in command_lower or "status" in command_lower:
        bank_txns = db.get_transactions(source="bank")
        coded = [t for t in bank_txns if t.get('nominal_code')]
        uncoded = [t for t in bank_txns if not t.get('nominal_code')]
        coverage = len(coded) / len(bank_txns) * 100 if bank_txns else 0

        return f"""Coverage: {coverage:.1f}%
Coded: {len(coded)} transactions
Uncoded: {len(uncoded)} transactions
Total: {len(bank_txns)} transactions"""

    # Uncoded vendors
    elif "uncoded" in command_lower and "vendor" in command_lower:
        from collections import Counter
        bank_txns = db.get_transactions(source="bank")
        uncoded = [t for t in bank_txns if not t.get('nominal_code')]

        vendor_counts = Counter(t['vendor'] for t in uncoded)
        top_10 = vendor_counts.most_common(10)

        result = "Top 10 uncoded vendors:\n"
        for vendor, count in top_10:
            result += f"  {count:3d}  {vendor}\n"

        return result

    return "Command not recognized. Try:\n- 'change [vendor] to [code]'\n- 'show coverage'\n- 'show uncoded vendors'"


# Test commands
workspace = Workspace("production", str(Path("accountantiq/data/workspaces").absolute()))
db = workspace.get_database()

print("=" * 80)
print("TESTING CHAT INTERFACE (Simplified)")
print("=" * 80)

# Test 1: Show coverage
print("\nYou: What's my coverage?")
print("\nAssistant:")
print(process_command("What's my coverage?", db))

# Test 2: Show uncoded vendors
print("\n" + "=" * 80)
print("\nYou: Show me uncoded vendors")
print("\nAssistant:")
print(process_command("show uncoded vendors", db))

# Test 3: Example of changing code (won't actually execute for demo)
print("\n" + "=" * 80)
print("\nYou: Change Applecare Uk to 7100")
print("\nAssistant:")
result = process_command("Change Applecare Uk to 7100", db)
print(result)

# Show updated stats
print("\n" + "=" * 80)
print("\nYou: What's my coverage now?")
print("\nAssistant:")
print(process_command("coverage", db))

db.close()

print("\n" + "=" * 80)
print("DEMO COMPLETE!")
print("=" * 80)
print("\nTo use the full LLM-powered chat:")
print("  export OPENAI_API_KEY='sk-...'")
print("  python chat.py production")
print("\nOr set up MCP server for Claude Desktop integration!")
