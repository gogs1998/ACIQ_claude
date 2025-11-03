from accountantiq.core.workspace import Workspace
from pathlib import Path

workspace = Workspace("production", str(Path("accountantiq/data/workspaces").absolute()))
db = workspace.get_database()

print("=" * 80)
print("UPDATING CODES: The Woodend & Angels Hotel → 7403")
print("=" * 80)

# Get transactions for these vendors
bank_txns = db.get_transactions(source="bank")

woodend = [t for t in bank_txns if "woodend" in t['vendor'].lower()]
angels = [t for t in bank_txns if "angels hotel" in t['vendor'].lower()]

print(f"\nFound:")
print(f"  The Woodend:              {len(woodend)} transactions")
print(f"  Angels Hotel Bar & Res:   {len(angels)} transactions")

# Show current codes
if woodend:
    current = woodend[0].get('nominal_code', 'None')
    print(f"\n  Current code (Woodend):   {current}")
if angels:
    current = angels[0].get('nominal_code', 'None')
    print(f"  Current code (Angels):    {current}")

print(f"\n  New code:                 7403 (Entertainment)")

# Update transactions
total_updated = 0

for txn in woodend + angels:
    db.update_transaction(txn['id'], {
        'nominal_code': '7403',
        'confidence': 1.0,
        'assigned_by': 'llm_chat',
        'reviewed': True
    })
    total_updated += 1

print(f"\n✓ Updated {total_updated} transactions")

# Update or create rules
print("\nUpdating rules...")

# Delete old rules for these vendors
db.conn.execute("DELETE FROM rules WHERE vendor_pattern IN (?, ?)", 
                ['The Woodend', 'Angels Hotel Bar & Res'])

# Create new rules
woodend_rule = db.insert_rule({
    'vendor_pattern': 'The Woodend',
    'nominal_code': '7403',
    'rule_type': 'exact',
    'confidence': 1.0,
    'created_by': 'reviewer'
})

angels_rule = db.insert_rule({
    'vendor_pattern': 'Angels Hotel Bar & Res',
    'nominal_code': '7403',
    'rule_type': 'exact',
    'confidence': 1.0,
    'created_by': 'reviewer'
})

print(f"✓ Created rule for The Woodend (ID: {woodend_rule})")
print(f"✓ Created rule for Angels Hotel (ID: {angels_rule})")

print("\n" + "=" * 80)
print("COMPLETE!")
print("=" * 80)
print("\n7403 = Entertainment (subset of 7400 Travel & Subsistence)")
print("\nThese vendors will now be coded as 7403 in future imports.")

db.close()
