# LLM Enhancement Proposal: Invoice Itemization & Onboarding Assistant

## Executive Summary

This proposal outlines two strategic LLM enhancements to AccountantIQ that address current limitations and significantly improve user experience:

1. **Invoice Itemization Agent** - Parse and categorize line items within complex invoices
2. **Onboarding Assistant Agent** - Accelerate initial setup with intelligent match suggestions

**Business Value:**
- **Reduced manual effort**: Handle mixed-category transactions automatically
- **Faster onboarding**: Reduce setup time from hours to minutes
- **Higher accuracy**: LLM can understand context better than keyword matching
- **Cost-effective**: Strategic use of LLM only where it adds most value

---

## Current LLM Integration (Baseline)

### What's Already Implemented

**1. AI Suggester** (`ai_suggester.py`)
- **Purpose**: Suggest nominal codes for individual transactions
- **Two-layer approach**:
  - Layer 1: Rule-based (keyword matching) - Free, fast
  - Layer 2: LLM suggestions - Intelligent, costs API calls
- **Models**: GPT-4o-mini or Claude Haiku (cheap, fast)
- **Confidence**: Returns top 5 suggestions with reasoning

**2. Chat Interface** (`chat.py`)
- **Purpose**: Natural language interaction with accounting data
- **Capabilities**:
  - Update transaction codes
  - Query statistics
  - Create rules
  - Export data
- **Models**: GPT-4o or Claude Sonnet (more capable)

### Current Limitations

1. **Transaction-level only**: Cannot itemize within a single transaction
2. **Cold-start problem**: Low match rate (13%) until manual training
3. **No visual parsing**: Cannot read invoices/receipts
4. **Limited context**: Doesn't use historical patterns during onboarding

---

## Feature 1: Invoice Itemization Agent

### Problem Statement

**Current Behavior:**
```
Amazon transaction: -£127.43
Current system: Code entire amount to one category (e.g., 5000 - Purchases)
```

**Problem**: The £127.43 might be:
- £45.00 - Printer paper (7300 - Office Supplies)
- £32.50 - USB cables (7100 - IT Equipment)
- £28.93 - Desk organizer (0040 - Furniture)
- £21.00 - Business cards (7300 - Printing)

**Result**: Inaccurate categorization, mixed expense reporting.

### Solution: Invoice Itemization Agent

**Workflow:**
```
1. User uploads invoice (PDF, image, or text)
2. LLM extracts line items with vision/text parsing
3. Each item categorized to appropriate nominal code
4. Creates split-coded transaction entries
5. User reviews and approves splits
```

### Technical Design

#### New Agent Structure

```
accountantiq/agents/itemizer_agent/
├── __init__.py
├── itemizer_agent.py       # Main agent logic
├── invoice_parser.py       # Extract line items from invoice
└── item_classifier.py      # Categorize individual items
```

#### Core Components

**1. Invoice Parser**
```python
class InvoiceParser:
    """Extract line items from invoice using LLM vision."""

    def parse_invoice(self, invoice_source):
        """
        Args:
            invoice_source: PDF path, image path, or text

        Returns:
            {
                'vendor': 'Amazon',
                'invoice_number': 'XXX-XXXXXXX-XXXXXXX',
                'total': 127.43,
                'date': '2024-10-15',
                'line_items': [
                    {'description': 'A4 Printer Paper', 'amount': 45.00},
                    {'description': 'USB-C Cable', 'amount': 32.50},
                    ...
                ]
            }
        """
```

**LLM Models:**
- **GPT-4o**: Has vision capabilities, can read PDFs/images
- **Claude Sonnet**: Excellent at document understanding
- **Cost**: ~$0.01-0.05 per invoice (acceptable for business use)

**2. Item Classifier**
```python
class ItemClassifier:
    """Categorize individual line items to nominal codes."""

    def classify_items(self, line_items, business_context):
        """
        Args:
            line_items: List of items from invoice
            business_context: Business type, common categories

        Returns:
            [
                {
                    'description': 'A4 Printer Paper',
                    'amount': 45.00,
                    'suggested_code': '7300',
                    'reasoning': 'Office supplies/stationery',
                    'confidence': 0.95
                },
                ...
            ]
        """
```

**Context-aware prompting:**
```
Business type: Dental practice
Common expenses: Medical supplies, IT equipment, office supplies

Invoice items to categorize:
1. A4 Printer Paper - £45.00
2. USB-C Cable - £32.50
3. Desk organizer - £28.93

For each item, suggest the most appropriate UK nominal code
considering this is a dental practice.
```

#### Database Schema Addition

```sql
-- New table for split transactions
CREATE TABLE transaction_splits (
    id INTEGER PRIMARY KEY,
    parent_transaction_id INTEGER,  -- References original transaction
    line_number INTEGER,
    description TEXT,
    amount DECIMAL(10, 2),
    nominal_code TEXT,
    confidence DECIMAL(3, 2),
    reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_transaction_id) REFERENCES transactions(id)
);

-- Mark original transaction as split
ALTER TABLE transactions ADD COLUMN is_split BOOLEAN DEFAULT FALSE;
```

#### User Interface

**CLI Command:**
```bash
# Process invoice and split transaction
python -m accountantiq.cli itemize \
    -w my_workspace \
    --transaction-id 1234 \
    --invoice amazon_invoice.pdf

# Interactive review of splits
python -m accountantiq.cli review-splits -w my_workspace
```

**Dashboard Integration:**
```
Transaction: Amazon - £127.43
[Split this transaction] button

→ Upload invoice: amazon_invoice.pdf
→ AI analyzes and suggests splits:

   ✓ A4 Printer Paper     £45.00  → 7300 (Office Supplies)    [95% confidence]
   ✓ USB-C Cable          £32.50  → 7100 (IT Equipment)       [92% confidence]
   ? Desk organizer       £28.93  → 0040 (Furniture)          [75% confidence]
   ✓ Business cards       £21.00  → 7300 (Printing)           [98% confidence]

[Approve All] [Adjust] [Reject]
```

#### Cost Analysis

**Per Invoice:**
- Vision model call (parse): ~$0.01-0.02
- Classification calls (4-10 items): ~$0.01-0.03
- **Total**: ~$0.02-0.05 per invoice

**Monthly Usage:**
- 50 mixed invoices/month × $0.03 = **$1.50/month**
- 200 mixed invoices/month × $0.03 = **$6.00/month**

**ROI**: If each invoice takes 5 minutes to manually split (4-6 items):
- 50 invoices = 250 minutes saved = **4.2 hours saved**
- At £30/hour: **£126 saved for £1.50 cost**
- **ROI: 8,400%**

---

## Feature 2: Onboarding Assistant Agent

### Problem Statement

**Current Onboarding Experience:**
```
1. Import historical Sage data (1,479 transactions)
2. Import bank statement (1,407 transactions)
3. Initial match rate: 13.1% (205 coded, 1,202 exceptions)
4. User must manually review 1,202 transactions
5. After reviews, match rate improves to 95%+
```

**Problem**: The cold-start phase requires significant manual effort (4-6 hours of review).

### Solution: Onboarding Assistant Agent

**Goal**: Use LLM to analyze historical patterns and suggest likely matches during initial setup, reducing manual review from 1,200 → 200 transactions (~83% reduction).

**Approach:**
```
1. Analyze historical Sage patterns (vendors, amounts, frequencies)
2. Examine bank transactions that didn't auto-match
3. LLM suggests likely matches with reasoning
4. User approves/rejects suggestions in batch
5. System learns from approvals and creates rules
```

### Technical Design

#### New Agent Structure

```
accountantiq/agents/onboarding_agent/
├── __init__.py
├── onboarding_agent.py      # Main orchestrator
├── pattern_analyzer.py      # Analyze historical patterns
└── match_suggester.py       # Suggest bank→sage matches
```

#### Core Components

**1. Pattern Analyzer**
```python
class PatternAnalyzer:
    """Analyze historical Sage data for patterns."""

    def analyze_patterns(self, sage_transactions):
        """
        Analyze Sage history to understand:
        - Common vendors and their variations
        - Typical amounts and frequencies
        - Seasonal patterns
        - Category distributions

        Returns:
            {
                'vendor_patterns': {
                    'TESLA': {
                        'typical_amounts': [9.99, 15.00, 22.50],
                        'frequency': 'monthly',
                        'nominal_code': '1210',
                        'variations': ['tesla', 'tesla motors']
                    },
                    ...
                },
                'category_distribution': {...},
                'amount_ranges_by_category': {...}
            }
        """
```

**2. Match Suggester**
```python
class MatchSuggester:
    """Suggest matches between bank and Sage using LLM."""

    def suggest_matches(self, unmatched_bank_txns, sage_patterns):
        """
        For each unmatched bank transaction:
        1. Get context from historical patterns
        2. Ask LLM to suggest likely Sage match
        3. Return suggestions with confidence and reasoning

        Returns:
            [
                {
                    'bank_txn': {...},
                    'suggested_sage_vendor': 'TESLA',
                    'suggested_code': '1210',
                    'reasoning': 'Bank desc "Card 61, Tesla" matches Sage vendor "TESLA"',
                    'confidence': 0.92
                },
                ...
            ]
        """
```

#### LLM Prompting Strategy

**Batch Processing** (more efficient):
```
You are helping match bank transactions to historical accounting records.

Historical Sage patterns:
- TESLA: £9.99-£22.50, monthly, coded to 1210
- APPLE: £2.99-£9.99, monthly, coded to 1105
- JUST EAT: £15-£45, weekly, coded to 1210

Unmatched bank transactions:
1. 2024-03-28 | -£9.99 | "Card 61, Tesla"
2. 2024-03-29 | -£4.49 | "Apple.Com/Bill"
3. 2024-03-30 | -£28.50 | "Card 53, Just Eat"

For each bank transaction, suggest the most likely Sage vendor match.
Format:
MATCH: [bank_txn_id] → [sage_vendor] (code: [code])
REASONING: [why]
CONFIDENCE: [0.0-1.0]
```

**Response:**
```
MATCH: 1 → TESLA (code: 1210)
REASONING: Description "Card 61, Tesla" clearly matches vendor "TESLA"
CONFIDENCE: 0.95

MATCH: 2 → APPLE (code: 1105)
REASONING: "Apple.Com/Bill" matches vendor "APPLE", amount £4.49 in typical range
CONFIDENCE: 0.93

MATCH: 3 → JUST EAT (code: 1210)
REASONING: "Just Eat" directly matches vendor "JUST EAT"
CONFIDENCE: 0.98
```

#### Workflow

**Step 1: Initial Processing**
```bash
python -m accountantiq.cli onboard \
    -w my_workspace \
    --sage data/AUDITDL2.csv \
    --bank data/TransactionHistory.csv \
    --use-llm
```

**What Happens:**
1. Parse Sage history (1,479 txns) ✓
2. Learn patterns (238 rules) ✓
3. Parse bank statement (1,407 txns) ✓
4. Apply existing rules (205 matched, 1,202 unmatched)
5. **NEW**: Analyze patterns with LLM
6. **NEW**: Batch suggest matches for 1,202 unmatched
7. **NEW**: Present high-confidence suggestions for bulk approval

**Step 2: Bulk Review**
```
Onboarding Assistant Suggestions (842 high-confidence matches found)

Approve these matches?

✓ "Card 61, Tesla" → TESLA (1210)          [95% confidence]
✓ "Apple.Com/Bill" → APPLE (1105)          [93% confidence]
✓ "Card 53, Just Eat" → JUST EAT (1210)    [98% confidence]
✓ "Amznmktplace*" → AMAZON (5000)          [87% confidence]
✓ "Spotify" → SPOTIFY (7100)               [92% confidence]
... (showing 5 of 842)

[Approve All 842] [Review Individually] [Skip]
```

**Result:**
- Original: 1,202 unmatched → Manual review needed
- With LLM: 842 auto-suggested → User approves in 30 seconds
- Remaining: 360 for manual review (70% reduction!)

#### Cost Analysis

**Per Onboarding:**
- Pattern analysis: 1 LLM call with historical data (~$0.05)
- Match suggestions: Batch processing 1,200 transactions (~$0.20-0.40)
- **Total**: ~$0.25-0.45 per onboarding

**Time Savings:**
- Manual review: 1,200 txns × 15 sec = **5 hours**
- LLM-assisted: 360 txns × 15 sec = **1.5 hours**
- **Time saved: 3.5 hours per client**

**ROI**:
- Cost: $0.40
- Time saved: 3.5 hours × £30/hour = **£105**
- **ROI: 26,150%**

---

## Implementation Plan

### Phase 1: Invoice Itemization (Week 1-2)

**Week 1: Core Development**
- [ ] Create `itemizer_agent` directory and structure
- [ ] Implement `InvoiceParser` with GPT-4o vision
- [ ] Implement `ItemClassifier` with context-aware prompting
- [ ] Add `transaction_splits` table to database schema
- [ ] Write unit tests for parsing and classification

**Week 2: Integration & UI**
- [ ] Add CLI command: `accountantiq itemize`
- [ ] Integrate with dashboard (split transaction button)
- [ ] Add review interface for split transactions
- [ ] Test with real Amazon, Office Depot, and Staples invoices
- [ ] Document usage and cost estimates

**Deliverables:**
- Working itemization agent
- CLI and dashboard integration
- Documentation and examples
- Cost tracking and reporting

### Phase 2: Onboarding Assistant (Week 3-4)

**Week 3: Core Development**
- [ ] Create `onboarding_agent` directory and structure
- [ ] Implement `PatternAnalyzer` for historical analysis
- [ ] Implement `MatchSuggester` with batch LLM processing
- [ ] Add confidence thresholds and filtering
- [ ] Write unit tests for pattern analysis and matching

**Week 4: Integration & UI**
- [ ] Add CLI command: `accountantiq onboard --use-llm`
- [ ] Create bulk approval interface
- [ ] Add progress tracking and statistics
- [ ] Test with real onboarding datasets
- [ ] Measure time savings and accuracy

**Deliverables:**
- Working onboarding assistant
- Bulk approval interface
- Performance metrics and benchmarks
- Cost tracking and ROI analysis

### Phase 3: Optimization & Polish (Week 5)

- [ ] Optimize LLM prompts for accuracy and cost
- [ ] Add caching for repeated patterns
- [ ] Implement batch processing for efficiency
- [ ] Add user feedback loop for continuous improvement
- [ ] Write comprehensive documentation
- [ ] Create video tutorials

---

## Cost & ROI Projections

### Monthly Cost Estimates

**Scenario: Small Accounting Practice (10 clients)**

| Feature | Usage | Cost/Use | Monthly Cost |
|---------|-------|----------|--------------|
| **Invoice Itemization** | 50 invoices/month | $0.03 | $1.50 |
| **Onboarding** | 2 new clients/month | $0.40 | $0.80 |
| **Chat/Suggestions** | 200 queries/month | $0.01 | $2.00 |
| **Total** | - | - | **$4.30/month** |

**Scenario: Medium Practice (50 clients)**

| Feature | Usage | Cost/Use | Monthly Cost |
|---------|-------|----------|--------------|
| **Invoice Itemization** | 300 invoices/month | $0.03 | $9.00 |
| **Onboarding** | 8 new clients/month | $0.40 | $3.20 |
| **Chat/Suggestions** | 1,000 queries/month | $0.01 | $10.00 |
| **Total** | - | - | **$22.20/month** |

### ROI Analysis

**Small Practice (10 clients):**
- Monthly cost: $4.30
- Time saved: 20 hours/month (itemization + onboarding)
- Value saved: 20 hours × £30/hour = **£600**
- **ROI: 13,853%**

**Medium Practice (50 clients):**
- Monthly cost: $22.20
- Time saved: 120 hours/month
- Value saved: 120 hours × £30/hour = **£3,600**
- **ROI: 16,116%**

---

## Technical Considerations

### LLM Provider Selection

**Option 1: OpenAI (GPT-4o)**
- ✅ Vision capabilities (can read invoices)
- ✅ Fast and reliable
- ✅ Good context window (128k tokens)
- ⚠️ Slightly more expensive

**Option 2: Anthropic (Claude Sonnet)**
- ✅ Excellent document understanding
- ✅ Strong reasoning capabilities
- ✅ PDF support built-in
- ✅ Slightly cheaper

**Recommendation**: Support both, let users choose based on preference and budget.

### Cost Optimization Strategies

1. **Caching**: Cache LLM responses for identical queries (30-day TTL)
2. **Batch Processing**: Process multiple items in single LLM call
3. **Confidence Thresholds**: Only use LLM for ambiguous cases
4. **Tiered Approach**:
   - Rule-based (free) →
   - Fuzzy matching (free) →
   - LLM (paid, only when needed)

### Privacy & Security

**Considerations:**
- Invoice data contains sensitive business information
- LLM providers store queries temporarily (OpenAI: 30 days, Anthropic: 0 days)
- Recommendation:
  - Add option to anonymize vendor names before sending to LLM
  - Use Anthropic for sensitive data (no retention)
  - Add disclaimer about LLM usage in terms

**Anonymization Example:**
```python
def anonymize_for_llm(transaction):
    """Anonymize sensitive data before LLM processing."""
    return {
        'vendor': hash_vendor_name(transaction['vendor']),
        'amount': transaction['amount'],
        'date': transaction['date'],
        'description': remove_references(transaction['description'])
    }
```

---

## Success Metrics

### Invoice Itemization

**Target Metrics:**
- ✅ 90%+ accuracy on item categorization
- ✅ Process invoice in <10 seconds
- ✅ Cost < $0.05 per invoice
- ✅ User approval rate > 85%

**Measurement:**
- Track categorization accuracy vs. manual review
- Measure processing time per invoice
- Calculate cost per invoice
- Monitor user approval/rejection rates

### Onboarding Assistant

**Target Metrics:**
- ✅ 70%+ reduction in manual review time
- ✅ 85%+ match accuracy
- ✅ Onboarding time reduced from 5 hours → 1.5 hours
- ✅ Cost < $0.50 per client onboarding

**Measurement:**
- Compare onboarding time with/without LLM
- Track match accuracy (accepted suggestions)
- Monitor time savings
- Calculate cost per onboarding session

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **High LLM costs** | Medium | Medium | Implement strict rate limits, caching, and confidence thresholds |
| **Low accuracy** | Low | High | Extensive testing, user feedback loop, confidence scoring |
| **Privacy concerns** | Low | High | Anonymization option, use Anthropic (no retention), user consent |
| **API failures** | Medium | Low | Fallback to rule-based, retry logic, graceful degradation |
| **Slow processing** | Low | Low | Batch processing, async operations, progress indicators |

---

## Alternative Approaches Considered

### 1. Train Custom Model
**Pros**: Lower long-term cost, data privacy
**Cons**: Requires ML expertise, training data, infrastructure
**Decision**: Use LLM APIs for faster time-to-market, consider custom model later if volume justifies

### 2. OCR + Traditional ML
**Pros**: Cheaper per invoice, no API dependencies
**Cons**: Complex pipeline, lower accuracy, maintenance burden
**Decision**: LLM provides better accuracy with less complexity

### 3. Manual Rule Building
**Pros**: Free, deterministic
**Cons**: Doesn't scale, requires extensive configuration
**Decision**: Use as fallback, not primary approach

---

## Conclusion

### Summary

The proposed LLM enhancements address two critical gaps in AccountantIQ:

1. **Invoice Itemization**: Enables accurate split-coding of mixed transactions
2. **Onboarding Assistant**: Dramatically reduces initial setup time

**Combined Benefits:**
- **Time Savings**: 25-30 hours/month per practice
- **Cost**: $4-$22/month (negligible vs. time saved)
- **ROI**: 13,000-16,000%
- **User Experience**: Significantly improved onboarding and ongoing use

### Recommendation

**Proceed with implementation** in two phases:
1. **Phase 1** (Weeks 1-2): Invoice Itemization - addresses immediate user pain point
2. **Phase 2** (Weeks 3-4): Onboarding Assistant - solves cold-start problem

**Expected Impact:**
- Reduce onboarding time by 70% (5 hours → 1.5 hours)
- Enable accurate categorization of mixed invoices
- Increase user satisfaction and adoption
- Maintain cost-effectiveness (<$25/month for medium practices)

### Next Steps

1. Review and approve proposal
2. Set up LLM API accounts (OpenAI + Anthropic)
3. Begin Phase 1 implementation
4. Test with real user data
5. Iterate based on feedback

---

**Questions or feedback? Let's discuss the implementation approach!**
