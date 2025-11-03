# AccountantIQ

**Autonomous bookkeeping tool with multi-agent AI system**

AccountantIQ learns from your historical Sage 50 data and automatically codes new bank transactions using a specialized 5-agent architecture.

## Architecture

AccountantIQ uses **Claude Code's native multi-agent system** with 5 specialized agents:

```
┌─────────────┐
│   PARSER    │  Ingests Sage/bank CSVs → DuckDB
└──────┬──────┘
       │
┌──────▼──────┐
│   LEARNER   │  Learns vendor→code patterns
└──────┬──────┘
       │
┌──────▼──────┐
│  CLASSIFIER │  Auto-codes new transactions
└──────┬──────┘
       │
┌──────▼──────┐
│  REVIEWER   │  Handles exceptions, learns from corrections
└──────┬──────┘
       │
┌──────▼──────┐
│  EXPORTER   │  Generates Sage 50 import CSV
└─────────────┘
```

### Agent Responsibilities

1. **Parser Agent**: Normalizes Sage 50 exports and bank statements into DuckDB
2. **Learner Agent**: Analyzes historical data to build fuzzy-matching rules
3. **Classifier Agent**: Applies rules to auto-code new transactions with confidence scores
4. **Reviewer Agent**: Handles low-confidence transactions, learns from user overrides
5. **Exporter Agent**: Generates valid Sage 50 Audit Trail CSV for import

Agents communicate through:
- Shared DuckDB database
- Workspace configuration files
- Orchestrator coordination

## Installation

### Prerequisites

- Python 3.11+
- pip or uv

### Install

```bash
# Clone repository
git clone https://github.com/gogs1998/ACIQ_claude.git
cd accountantiq

# Install with pip
pip install -e .

# Or with uv (faster)
uv pip install -e .
```

## Quick Start

### 1. Create Workspace

```bash
accountantiq workspace create my_practice
```

### 2. One-Shot Processing

Process everything in one command:

```bash
accountantiq process \
  --workspace my_practice \
  --sage sage_export.csv \
  --bank bank_statement.csv \
  --output coded_transactions.csv
```

### 3. Step-by-Step Processing

For more control, run each agent individually:

```bash
# Parse historical Sage data
accountantiq parse sage --file sage_export.csv --workspace my_practice

# Learn patterns
accountantiq learn --workspace my_practice

# Parse new bank statement
accountantiq parse bank --file bank_statement.csv --workspace my_practice

# Auto-code transactions
accountantiq classify --workspace my_practice

# Review exceptions (interactive)
accountantiq review --workspace my_practice

# Export to Sage format
accountantiq export --workspace my_practice --output result.csv
```

## CLI Commands

### Main Commands

```bash
# Full pipeline
accountantiq process -w <workspace> -s <sage.csv> -b <bank.csv> -o <output.csv>

# Parse files
accountantiq parse sage --file <sage.csv> -w <workspace>
accountantiq parse bank --file <bank.csv> -w <workspace>

# Learn patterns
accountantiq learn -w <workspace> --min-confidence 0.75

# Classify transactions
accountantiq classify -w <workspace> --threshold 0.70

# Review exceptions
accountantiq review -w <workspace>

# Export results
accountantiq export -w <workspace> -o <output.csv>

# Show statistics
accountantiq stats -w <workspace>
```

### Workspace Management

```bash
# Create workspace
accountantiq workspace create <name>

# List workspaces
accountantiq workspace list

# Delete workspace
accountantiq workspace delete <name> --confirm
```

### Rules Management

```bash
# List rules
accountantiq rules list -w <workspace>

# Filter by confidence
accountantiq rules list -w <workspace> --min-confidence 0.85

# Delete rule
accountantiq rules delete <rule_id> -w <workspace> --confirm
```

## Data Formats

### Current Status

The parser agents are **placeholders** waiting for real CSV formats. They will be customized once you provide:

1. **Sage 50 Export CSV**: Anonymized sample with exact column structure
2. **Bank Statement CSV**: Anonymized sample with exact column structure

**DO NOT assume data formats. Parsers will be built for YOUR exact formats.**

### Providing CSV Samples

When ready, provide:
- At least 10-20 rows of real data (anonymized)
- Keep exact column headers
- Preserve data types and formats
- Include edge cases (negative amounts, special characters, etc.)

## Database Schema

All agents share a DuckDB database with these tables:

**transactions**: All parsed transactions (history + bank)
**rules**: Vendor→nominal code mappings
**overrides**: User corrections that improve learning
**agent_logs**: Audit trail of agent actions

See `core/database.py` for complete schema.

## How It Works

### Learning Phase

1. Parser agent loads historical Sage 50 data
2. Learner agent analyzes vendor→nominal code patterns
3. Creates rules with confidence scores based on consistency

### Classification Phase

1. Parser agent loads new bank transactions
2. Classifier agent applies fuzzy matching against learned rules
3. High-confidence matches are auto-coded
4. Low-confidence matches flagged for review

### Review Phase

1. Reviewer agent presents exceptions to user
2. User approves or overrides suggestions
3. System learns from corrections, creates new rules
4. Rules improve over time

### Export Phase

1. Exporter agent formats coded transactions
2. Validates against Sage 50 requirements
3. Generates importable CSV file

## Configuration

Each agent has a YAML config in `agents/<agent_name>/agent_config.yaml`:

- **Parser**: Column mappings, date formats, validation rules
- **Learner**: Confidence thresholds, fuzzy match settings
- **Classifier**: Auto-coding thresholds, explanation templates
- **Reviewer**: Review policies, learning settings
- **Exporter**: Output format, Sage column mappings

## Project Structure

```
accountantiq/
├── agents/
│   ├── parser_agent/       # CSV parsing (Sage + bank)
│   ├── learner_agent/      # Pattern learning
│   ├── classifier_agent/   # Transaction coding
│   ├── reviewer_agent/     # Exception handling
│   └── exporter_agent/     # Sage CSV generation
├── core/
│   ├── database.py         # DuckDB schema + operations
│   ├── models.py           # Pydantic models
│   └── workspace.py        # Workspace management
├── orchestrator.py         # Multi-agent coordinator
├── cli.py                  # CLI interface
└── data/workspaces/        # User workspaces
```

## Technology Stack

- **Python 3.11+**: Modern Python features
- **DuckDB**: Embedded analytics database for agent communication
- **Polars**: Fast CSV parsing (10-100x faster than pandas)
- **rapidfuzz**: Fuzzy string matching for vendor names
- **Typer**: Modern CLI framework
- **Pydantic**: Data validation
- **Rich**: Beautiful terminal output

## Development Status

**Current Phase**: Foundation complete, awaiting real data

✅ Project structure
✅ Core database with DuckDB
✅ Pydantic models
✅ Workspace management
✅ Agent folder structure + configs
✅ Orchestrator for agent coordination
✅ CLI interface with all commands
⏳ **Waiting for**: Real Sage 50 and bank CSV samples
⏳ **Next**: Build custom parsers for your exact formats
⏳ **Then**: Build remaining agent logic

## Next Steps

1. **Provide CSV samples** (anonymized but real structure)
2. **Build custom parsers** for your Sage/bank formats
3. **Implement learner logic** (pattern recognition)
4. **Implement classifier logic** (fuzzy matching)
5. **Implement reviewer UI** (interactive exception handling)
6. **Implement exporter logic** (Sage 50 format validation)
7. **Test with real data**
8. **Iterate and improve**

## License

[Specify license]

## Contributing

[Contributing guidelines]

## Support

For issues and questions: [GitHub Issues](https://github.com/gogs1998/ACIQ_claude/issues)
