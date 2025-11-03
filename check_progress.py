from accountantiq.core.workspace import Workspace
from pathlib import Path
from collections import Counter

workspace = Workspace("production", str(Path("accountantiq/data/workspaces").absolute()))
db = workspace.get_database()

# Get all bank transactions
bank_txns = db.get_transactions(source="bank")
total = len(bank_txns)

# Split coded vs uncoded
coded = [t for t in bank_txns if t.get('nominal_code') and t.get('nominal_code').strip()]
uncoded = [t for t in bank_txns if not t.get('nominal_code') or not t.get('nominal_code').strip()]

# Get rules
all_rules = db.get_rules()
manual_rules = [r for r in all_rules if r.get('created_by') == 'reviewer']

print("=" * 80)
print("PROGRESS UPDATE")
print("=" * 80)

print(f"\n📊 COVERAGE:")
print(f"   Total transactions:     {total}")
print(f"   Coded:                  {len(coded)} ({len(coded)/total*100:.1f}%)")
print(f"   Uncoded:                {len(uncoded)} ({len(uncoded)/total*100:.1f}%)")

improvement = len(coded) - 1213
print(f"\n   Improvement:            +{improvement} transactions since auto-coding")

print(f"\n🎯 RULES:")
print(f"   Total rules:            {len(all_rules)}")
print(f"   Manual rules created:   {len(manual_rules)}")

# Show what was manually coded
if improvement > 0:
    print(f"\n✅ RECENTLY CODED TRANSACTIONS:")
    
    # Get manually coded transactions
    manual_coded = [t for t in coded if t.get('assigned_by') == 'manual_review']
    
    if manual_coded:
        # Group by nominal code
        by_code = Counter(t['nominal_code'] for t in manual_coded)
        
        print(f"   Total manually coded:   {len(manual_coded)}")
        print(f"\n   Breakdown by code:")
        for code, count in sorted(by_code.items(), key=lambda x: x[1], reverse=True):
            print(f"      {code}: {count} transactions")
        
        # Show vendor breakdown
        print(f"\n   Vendors coded:")
        vendor_counts = Counter(t['vendor'] for t in manual_coded)
        for vendor, count in sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
            vendor_short = vendor[:50]
            print(f"      {count:3d}  {vendor_short}")

# Show remaining exceptions by vendor
print(f"\n📋 REMAINING EXCEPTIONS ({len(uncoded)}):")
if uncoded:
    vendor_counts = Counter(t['vendor'] for t in uncoded)
    print(f"   Top 10 uncoded vendors:")
    for vendor, count in vendor_counts.most_common(10):
        vendor_short = vendor[:50]
        print(f"      {count:3d}  {vendor_short}")

# Calculate time estimate
remaining_vendors = len(set(t['vendor'] for t in uncoded))
estimated_minutes = (remaining_vendors * 20) / 60  # 20 sec per vendor

print(f"\n⏱️  ESTIMATE:")
print(f"   Remaining vendor groups: {remaining_vendors}")
print(f"   Est. time to finish:     {int(estimated_minutes)} minutes")

db.close()
