# Interactive Review Dashboard

Beautiful terminal UI for manually reviewing and coding uncoded transactions with AI-powered suggestions.

## Features

✅ **Vendor Grouping** - Groups transactions by vendor, sorted by frequency (most common first)
✅ **Batch Coding** - Code all transactions from a vendor at once with one rule
✅ **AI Suggestions** - Rule-based + optional LLM suggestions for each transaction
✅ **Smart Ordering** - Most frequent vendors shown first for maximum efficiency
✅ **Learning** - Creates rules automatically as you code
✅ **Progress Tracking** - Shows stats at the end of your session

## Quick Start

```bash
# Basic usage (rule-based AI suggestions only)
python dashboard.py production

# With LLM suggestions (requires OpenAI or Anthropic API key)
python dashboard.py production --llm
```

## How It Works

### 1. Vendor Grouping (Efficiency!)

Instead of reviewing 355 individual transactions, you review **215 vendor groups**.

**Example:**
- **Apple.Com/Bill** (14 transactions)
  - Code once → Creates rule → All 14 auto-coded ✅
  - Saved 13 manual reviews!

**Top vendors by frequency:**
```
14 transactions - Apple.Com/Bill
13 transactions - Angels Hotel Bar & Res
11 transactions - Ringgo Parking
11 transactions - The Woodend
 9 transactions - Www Gdc Uk Org
 8 transactions - Microsoft*Microsoft 36
 8 transactions - Ubr* Pending.Uber.Com
```

### 2. AI Suggestions (Two Layers)

#### Layer 1: Rule-Based (Free, Fast)
Keyword matching for common patterns:
- "Apple", "Microsoft" → `7100` (IT/Software)
- "Hotel", "Restaurant" → `7400` (Travel & Subsistence)
- "Parking", "Uber" → `7500` (Motor)
- "Insurance" → `7104`
- "Medical", "Dental" → `7200`

#### Layer 2: LLM (Smart, Costs API calls)
Uses GPT-4o-mini or Claude Haiku for intelligent suggestions:
- Understands context and business type
- Provides reasoning for each suggestion
- Considers transaction amount and patterns
- Only runs when `--llm` flag is used

### 3. Interactive Workflow

For each vendor group:

```
┌─────────────────────────────────────────────┐
│ Vendor 1/215                                │
│ 📦 Apple.Com/Bill (14 transactions)        │
├─────────────────────────────────────────────┤
│                                             │
│ Representative Transaction:                 │
│   Date: 2024-07-01                         │
│   Vendor: Apple.Com/Bill                   │
│   Amount: -£2.99                           │
│                                             │
│ All amounts: £-2.99, £-4.49, £-9.49...     │
│                                             │
├─────────────────────────────────────────────┤
│ 💡 AI Suggestions:                         │
│   1. 7100 - IT & Software (80%)            │
│   2. 7500 - Motor Expenses (75%)           │
├─────────────────────────────────────────────┤
│ Actions:                                    │
│   [1-9] - Select suggested code            │
│   [c]   - Enter custom code                │
│   [s]   - Skip this vendor                 │
│   [q]   - Quit and save                    │
│   [?]   - Show all codes                   │
└─────────────────────────────────────────────┘

Your choice: 1

✓ Coded 14 transactions
✓ Rule created (ID: 789)
```

### 4. What Happens When You Code

When you select a code (e.g., `7100` for Apple.Com/Bill):

1. **Creates Rule** → Exact match for "Apple.Com/Bill" → `7100`
2. **Codes ALL 14 transactions** → Updates database
3. **Rule applies to future** → Any future Apple.Com/Bill auto-coded

**Result:** 14 transactions coded with 1 action! 🎉

## Usage Examples

### Example 1: Code Top 10 Vendors (Batch Coding)

```bash
python dashboard.py production
```

**Workflow:**
1. Apple.Com/Bill (14 txns) → Press `1` → 7100 (IT/Software)
2. Angels Hotel (13 txns) → Press `2` → 7400 (Hospitality)
3. Ringgo Parking (11 txns) → Press `1` → 7500 (Motor)
4. Microsoft (8 txns) → Press `1` → 7100 (IT/Software)
5. Uber (8 txns) → Press `1` → 7500 (Travel)

**Result:** 54 transactions coded in 2 minutes!

### Example 2: Use LLM for Complex Cases

```bash
# Set API key
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."

python dashboard.py production --llm
```

LLM provides intelligent reasoning:
- "This appears to be a professional membership fee (GDC registration) → 7600"
- "High-value capital equipment purchase → 0030"
- "Recurring insurance payment → 7104"

### Example 3: Custom Codes

For transactions not in suggestions:

```
Your choice: c
Enter nominal code: 7903
7903 - Subscriptions and Memberships
This will code ALL 9 transactions for 'Www Gdc Uk Org'
Confirm batch coding? (Y/n): y

✓ Coded 9 transactions
✓ Rule created (ID: 790)
```

## Session Statistics

At the end, you'll see:

```
╔════════════════════════════════════════════╗
║ Review Session Complete!                   ║
╠════════════════════════════════════════════╣
║ Reviewed:      87 transactions             ║
║ Coded:         82 transactions             ║
║ Skipped:       5 transactions              ║
║ Rules Created: 15 new rules                ║
║                                            ║
║ Duration: 8m 32s                           ║
║                                            ║
║ ✓ Progress saved to database               ║
╚════════════════════════════════════════════╝

💡 Don't forget to re-export for Sage 50:
   python -m accountantiq.cli export production
```

## After Review: Export Updated File

Once you've coded transactions, re-export:

```bash
python -m accountantiq.cli export production
```

This creates a new `sage_import.csv` with:
- Original 1,213 auto-coded transactions
- New manually-coded transactions
- Total coverage increased from 77.4% → 85%+

## Efficiency Calculations

**Without Grouping:**
- 355 transactions × 30 seconds each = 2.96 hours 😫

**With Vendor Grouping:**
- 215 vendor groups × 20 seconds each = 1.19 hours
- But top 20 vendors = 150+ transactions (42%)
- Code top 20 in 7 minutes → 42% coverage ✅

**Realistic Session:**
- 15 minutes → Code ~50 vendor groups
- ~120-150 transactions coded
- ~20 rules created
- Coverage: 77.4% → 87%+ 🎉

## Nominal Code Reference

Common UK nominal codes shown in dashboard:

| Code | Category | Examples |
|------|----------|----------|
| 1200-1299 | Bank Accounts | Current, Deposit |
| 0030-0099 | Capital Assets | Equipment, Vehicles |
| 5000-5999 | Purchases | Cost of Sales |
| 7100 | IT & Software | Subscriptions, Cloud |
| 7104 | Insurance | Professional, Vehicle |
| 7200 | Utilities | Electric, Gas, Phone |
| 7300 | Office Supplies | Stationery, Ink |
| 7400 | Travel & Subsistence | Hotels, Meals, Rail |
| 7500 | Motor Expenses | Fuel, Parking, Repairs |
| 7600 | Professional Fees | Accountant, Legal, Registrations |
| 7901 | Bank Charges | Fees, Overdraft |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1-9` | Select AI suggestion (batch codes all) |
| `c` | Enter custom nominal code |
| `s` | Skip this vendor |
| `q` | Quit and save progress |
| `?` | Show all nominal codes |

## Tips

1. **Start with top vendors** - They give the most impact
2. **Create rules liberally** - They improve future auto-coding
3. **Use LLM for unknowns** - When rule-based suggestions aren't clear
4. **Skip personal expenses** - Don't waste time on non-business
5. **Review in sessions** - 15-20 minutes at a time

## LLM Setup (Optional)

### OpenAI (GPT-4o-mini)

```bash
# Get API key from https://platform.openai.com/api-keys
export OPENAI_API_KEY="sk-..."

# Install library
pip install openai

# Run with LLM
python dashboard.py production --llm
```

**Cost:** ~$0.15 per 1000 transactions (very cheap)

### Anthropic (Claude Haiku)

```bash
# Get API key from https://console.anthropic.com/
export ANTHROPIC_API_KEY="sk-ant-..."

# Install library
pip install anthropic

# Run with LLM
python dashboard.py production --llm
```

**Cost:** ~$0.25 per 1000 transactions (very cheap)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Dashboard UI                      │
│               (Rich Terminal UI)                    │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│                 AI Suggester                        │
├─────────────────────────────────────────────────────┤
│  Layer 1: Rule-Based (keyword matching)             │
│           - Fast, free, 70-85% confidence           │
│                                                     │
│  Layer 2: LLM (GPT/Claude)                          │
│           - Smart, contextual, 85-95% confidence    │
│           - Optional, costs API calls               │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              DuckDB Database                        │
│  - Transactions (update nominal_code)               │
│  - Rules (create new exact match rules)             │
│  - Agent logs (track review actions)                │
└─────────────────────────────────────────────────────┘
```

## Next Steps

After manual review:

1. **Re-export** → `python -m accountantiq.cli export production`
2. **Import to Sage 50** → Use the updated CSV
3. **Monitor rules** → Check database stats
4. **Next statement** → Auto-coding improves with more rules!

---

**The system learns from you!** Every code you assign creates a rule that improves future automation. 🚀
