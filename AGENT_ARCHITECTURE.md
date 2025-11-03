# AccountantIQ Agent Architecture

## Overview

AccountantIQ uses a **modular multi-agent architecture** where each agent is responsible for a specific task. Agents are independent, loosely coupled, and can be used in isolation or as part of the orchestrated pipeline.

---

## Current Agents (Production)

### 1. Parser Agent
**Location**: `accountantiq/agents/parser_agent/`
**Purpose**: Normalize CSV files from different sources
**Input**: Sage 50 CSV or Bank Statement CSV
**Output**: Normalized transactions in database
**Status**: ✅ Production-ready

**Subcomponents:**
- `sage_parser.py` - Parses Sage 50 Audit Trail format
- `bank_parser.py` - Parses bank statement format

### 2. Learner Agent
**Location**: `accountantiq/agents/learner_agent/`
**Purpose**: Build vendor→nominal code rules from historical data
**Input**: Historical Sage transactions
**Output**: Rules in database (smart + fuzzy matching)
**Status**: ✅ Production-ready (95.4% match rate achieved)

**Key Features:**
- Smart matching by (date, absolute amount)
- Fuzzy matching by vendor name
- Creates 700+ rules automatically

### 3. Classifier Agent
**Location**: `accountantiq/agents/classifier_agent/`
**Purpose**: Auto-code new bank transactions using learned rules
**Input**: Bank transactions + Rules
**Output**: Coded transactions with confidence scores
**Status**: ✅ Production-ready

**Features:**
- Applies smart rules (date+amount)
- Falls back to fuzzy matching
- Flags low-confidence for review

### 4. Reviewer Agent
**Location**: `accountantiq/agents/reviewer_agent/`
**Purpose**: Handle exceptions and learn from corrections
**Input**: Low-confidence transactions
**Output**: User-corrected codes + new rules
**Status**: ⚠️ Partially implemented (interactive mode is stub)

**Subcomponents:**
- `ai_suggester.py` - LLM-powered suggestions (rule-based + LLM)
- `reviewer_agent.py` - Review workflow

### 5. Exporter Agent
**Location**: `accountantiq/agents/exporter_agent/`
**Purpose**: Generate Sage 50 import CSV
**Input**: Coded transactions
**Output**: Sage-compatible CSV file
**Status**: ✅ Production-ready

**Features:**
- Date format conversion (DD/MM/YYYY)
- CSV injection prevention
- Proper debit/credit handling

---

## Proposed New Agents

### 6. Itemizer Agent (NEW)
**Location**: `accountantiq/agents/itemizer_agent/` (to be created)
**Purpose**: Parse and categorize line items within invoices
**Input**: Invoice (PDF/image/text) + Transaction ID
**Output**: Split transaction entries with individual line items
**Status**: 📋 Planned

**Use Case:**
```
Before: Amazon transaction: -£127.43 → Code: 5000 (Purchases)
After:  - Line 1: Printer paper £45.00 → 7300 (Office Supplies)
        - Line 2: USB cables £32.50 → 7100 (IT Equipment)
        - Line 3: Desk organizer £28.93 → 0040 (Furniture)
        - Line 4: Business cards £21.00 → 7300 (Printing)
```

**Subcomponents:**
- `invoice_parser.py` - Extract line items using GPT-4o vision
- `item_classifier.py` - Categorize each item to nominal code
- `split_manager.py` - Create and manage transaction splits

**LLM Usage:**
- Vision model (GPT-4o or Claude Sonnet) for invoice parsing
- Text model for item categorization
- Cost: ~$0.02-0.05 per invoice

### 7. Onboarding Agent (NEW)
**Location**: `accountantiq/agents/onboarding_agent/` (to be created)
**Purpose**: Accelerate initial setup with intelligent match suggestions
**Input**: Historical Sage data + Unmatched bank transactions
**Output**: Suggested matches for bulk approval
**Status**: 📋 Planned

**Use Case:**
```
Problem: Initial import has 1,202 unmatched transactions (13% match rate)
Solution: LLM analyzes patterns and suggests 842 likely matches
Result: User approves 842 in 30 seconds, only 360 need manual review
        (70% reduction in manual effort)
```

**Subcomponents:**
- `pattern_analyzer.py` - Analyze historical Sage patterns
- `match_suggester.py` - Suggest bank→sage matches using LLM
- `bulk_approver.py` - Interface for reviewing suggestions

**LLM Usage:**
- Batch processing for efficiency
- Pattern analysis + match suggestions
- Cost: ~$0.25-0.45 per onboarding session

---

## Agent Independence & Modularity

### Design Principles

1. **Single Responsibility**: Each agent does ONE thing well
2. **Loose Coupling**: Agents communicate through database, not direct calls
3. **Independent Operation**: Each agent can run standalone
4. **Composable**: Agents can be orchestrated into pipelines

### Example: Using Agents Independently

```bash
# Use parser agent only
python -m accountantiq.cli parse sage --file data.csv -w workspace

# Use itemizer agent only (when implemented)
python -m accountantiq.cli itemize \
    --transaction-id 1234 \
    --invoice invoice.pdf \
    -w workspace

# Use onboarding agent only (when implemented)
python -m accountantiq.cli onboard \
    --use-llm \
    --sage history.csv \
    --bank statement.csv \
    -w workspace
```

### Example: Orchestrated Pipeline

```bash
# Full pipeline (current agents)
python -m accountantiq.cli process \
    -w workspace \
    --sage history.csv \
    --bank statement.csv \
    --output result.csv

# This internally calls:
# 1. Parser Agent (sage)
# 2. Learner Agent
# 3. Parser Agent (bank)
# 4. Classifier Agent
# 5. Reviewer Agent (if interactive)
# 6. Exporter Agent
```

---

## Agent Communication

### Database-Centric Architecture

Agents communicate through **shared database state**:

```
┌─────────────────┐
│   DuckDB        │
│   Database      │
├─────────────────┤
│ - transactions  │ ← Written by parsers, read by learner/classifier
│ - rules         │ ← Written by learner, read by classifier
│ - splits        │ ← Written by itemizer, read by exporter
│ - overrides     │ ← Written by reviewer, read by learner
│ - agent_logs    │ ← Written by all agents
└─────────────────┘
         ↑
         │ (read/write)
         │
    ┌────┴────┬────────┬────────┬─────────┬──────────┬──────────┐
    │         │        │        │         │          │          │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼────┐ ┌─▼─────┐ ┌──▼──────┐ ┌─▼────────┐
│Parser │ │Learner│ │Classifier│ │Reviewer│ │Exporter│ │Itemizer │ │Onboarding│
│ Agent │ │ Agent │ │  Agent  │ │ Agent  │ │ Agent  │ │  Agent  │ │  Agent   │
└───────┘ └───────┘ └─────────┘ └────────┘ └────────┘ └─────────┘ └──────────┘
```

**Benefits:**
- No tight coupling between agents
- Can add/remove agents without affecting others
- Easy to test agents in isolation
- Agents can run in parallel (where appropriate)

---

## Agent Lifecycle

### Standard Agent Interface

All agents follow this pattern:

```python
class BaseAgent:
    """Base class for all agents."""

    def __init__(self, workspace_path: str):
        """Initialize with workspace path."""
        self.workspace_path = workspace_path
        self.db = Database(workspace_path)

    def run(self, **kwargs) -> AgentResult:
        """
        Execute agent logic.

        Returns:
            AgentResult with status, stats, and error info
        """
        start_time = time.time()

        try:
            # 1. Validate inputs
            self._validate_inputs(**kwargs)

            # 2. Execute agent logic
            result = self._execute(**kwargs)

            # 3. Log agent activity
            self._log_activity(result, start_time)

            return result

        except Exception as e:
            return AgentResult(
                agent=self.agent_name,
                status="error",
                error_message=str(e)
            )

        finally:
            self.db.close()

    def _execute(self, **kwargs):
        """Subclasses implement this."""
        raise NotImplementedError
```

### Agent Result Format

All agents return standardized results:

```python
{
    "agent": "itemizer",
    "status": "complete",  # or "error", "partial"
    "stats": {
        "items_parsed": 4,
        "items_classified": 4,
        "confidence_avg": 0.92
    },
    "duration_ms": 1234,
    "next_step": "Review split suggestions",
    "error_message": None  # if status="error"
}
```

---

## Adding New Agents (Template)

### Step 1: Create Agent Directory

```bash
mkdir -p accountantiq/agents/my_agent
touch accountantiq/agents/my_agent/__init__.py
touch accountantiq/agents/my_agent/my_agent.py
```

### Step 2: Implement Agent Class

```python
# my_agent.py
from accountantiq.core.database import Database
from accountantiq.core.models import AgentResult

class MyAgent:
    """Description of what this agent does."""

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.db = Database(workspace_path)

    def run(self, **kwargs) -> AgentResult:
        """Execute agent logic."""
        try:
            # Your logic here
            result = self._execute(**kwargs)

            return AgentResult(
                agent="my_agent",
                status="complete",
                stats={"processed": result}
            )

        except Exception as e:
            return AgentResult(
                agent="my_agent",
                status="error",
                error_message=str(e)
            )

        finally:
            self.db.close()

    def _execute(self, **kwargs):
        """Core agent logic."""
        # Implement your agent's functionality
        pass
```

### Step 3: Add CLI Command

```python
# In accountantiq/cli.py

@app.command()
def my_command(
    workspace: str = typer.Option(..., "-w", help="Workspace name"),
    # Add your parameters
):
    """Description of command."""
    from accountantiq.agents.my_agent.my_agent import MyAgent

    agent = MyAgent(workspace)
    result = agent.run()

    console.print(f"[green]✓ {result.stats}[/green]")
```

### Step 4: Test Agent

```bash
python -m accountantiq.cli my-command -w test_workspace
```

---

## Orchestration Options

### Option 1: CLI Orchestration (Current)

```python
# orchestrator.py
class AccountantOrchestrator:
    """Orchestrates multiple agents."""

    def run_full_pipeline(self):
        # Step 1: Parse
        parser = ParserAgent(self.workspace)
        parser.run()

        # Step 2: Learn
        learner = LearnerAgent(self.workspace)
        learner.run()

        # Step 3: Classify
        classifier = ClassifierAgent(self.workspace)
        classifier.run()

        # ... continue with other agents
```

### Option 2: Task Queue (Future Enhancement)

```python
# For parallel processing or async workflows
from celery import Celery

app = Celery('accountantiq')

@app.task
def run_parser(workspace, file_path):
    agent = ParserAgent(workspace)
    return agent.run(file_path)

@app.task
def run_learner(workspace):
    agent = LearnerAgent(workspace)
    return agent.run()

# Chain tasks
chain(
    run_parser.s(workspace, file_path),
    run_learner.s(workspace),
    run_classifier.s(workspace)
).apply_async()
```

---

## Agent Dependency Graph

### Current Pipeline

```
sage.csv ──► Parser Agent ──► Transactions (history)
                                    │
                                    ▼
                            Learner Agent ──► Rules
                                    │             │
bank.csv ──► Parser Agent ──► Transactions      │
                              (bank)             │
                                    │             │
                                    ▼             ▼
                            Classifier Agent ─────►
                                    │
                                    ▼
                            Reviewer Agent ──► Overrides
                                    │
                                    ▼
                            Exporter Agent ──► sage_import.csv
```

### With New Agents

```
                            ┌──────────────────┐
invoice.pdf ──────────────► │ Itemizer Agent   │ ──► Transaction Splits
                            └──────────────────┘         │
                                                         ▼
sage.csv ──► Parser Agent ──► Transactions (history)    │
                                    │                    │
                                    ▼                    │
                            Learner Agent ──► Rules      │
                                    │            │       │
                                    │            │       │
bank.csv ──► Parser Agent ──────┐  │            │       │
                                │  │            │       │
                                ▼  ▼            ▼       │
                        ┌────────────────────┐          │
                        │ Onboarding Agent   │          │
                        │ (LLM suggestions)  │          │
                        └────────────────────┘          │
                                    │                   │
                                    ▼                   │
                            Classifier Agent ───────────┤
                                    │                   │
                                    ▼                   │
                            Reviewer Agent              │
                                    │                   │
                                    ▼                   ▼
                            Exporter Agent ─────────────► sage_import.csv
                            (includes splits)
```

---

## Key Takeaways

1. **Modular Design**: Each agent is independent and can be used standalone
2. **Database-Centric**: Agents communicate through shared database state
3. **Standardized Interface**: All agents follow same pattern (run → AgentResult)
4. **Easy to Extend**: Adding new agents is straightforward with template
5. **Flexible Orchestration**: Can run individually or as part of pipeline
6. **LLM Integration**: New agents (itemizer, onboarding) use LLM where it adds value
7. **Cost-Effective**: Strategic LLM use only where traditional methods fall short

---

## Next Steps

1. ✅ Review architecture and agent separation approach
2. 📋 Implement Itemizer Agent (Week 1-2)
3. 📋 Implement Onboarding Agent (Week 3-4)
4. 📋 Update orchestrator to optionally include new agents
5. 📋 Add CLI commands for new agents
6. 📋 Write tests for each agent
7. 📋 Document usage patterns and examples
