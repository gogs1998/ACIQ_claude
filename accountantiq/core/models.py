"""
Pydantic models for AccountantIQ data validation.
Used across all agents for consistent data structures.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import date, datetime
from decimal import Decimal


class Transaction(BaseModel):
    """Transaction model used across all agents."""

    id: Optional[int] = None
    date: date
    vendor: str = Field(min_length=1)
    amount: Decimal = Field(decimal_places=2)
    nominal_code: Optional[str] = None
    reference: Optional[str] = None
    details: Optional[str] = None
    source: Literal["history", "bank"]
    confidence: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=2)
    explanation: Optional[str] = None
    reviewed: bool = False
    assigned_by: Optional[str] = None  # Agent name that coded this
    created_at: Optional[datetime] = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Ensure amount is not zero."""
        if v == 0:
            raise ValueError("Amount cannot be zero")
        return v

    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        """Validate source is either 'history' or 'bank'."""
        if v not in ["history", "bank"]:
            raise ValueError("Source must be 'history' or 'bank'")
        return v

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        data = self.model_dump()
        # Convert date and datetime to strings for DuckDB
        if data.get('date'):
            data['date'] = data['date'].isoformat()
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat()
        # Convert Decimal to float for DuckDB
        if data.get('amount'):
            data['amount'] = float(data['amount'])
        if data.get('confidence'):
            data['confidence'] = float(data['confidence'])
        return data


class Rule(BaseModel):
    """Rule model for vendor pattern matching."""

    id: Optional[int] = None
    vendor_pattern: str = Field(min_length=1)
    nominal_code: str = Field(min_length=1)
    rule_type: Literal["exact", "fuzzy", "regex"] = "fuzzy"
    confidence: Decimal = Field(ge=0, le=1, decimal_places=2)
    match_count: int = Field(default=0, ge=0)
    created_by: Optional[Literal["learner", "reviewer"]] = None
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None

    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not (0 <= v <= 1):
            raise ValueError("Confidence must be between 0 and 1")
        return v

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        data = self.model_dump()
        if data.get('confidence'):
            data['confidence'] = float(data['confidence'])
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat()
        if data.get('last_used'):
            data['last_used'] = data['last_used'].isoformat()
        return data


class Override(BaseModel):
    """Override record when user corrects a transaction."""

    id: Optional[int] = None
    transaction_id: int
    original_code: str
    corrected_code: str
    created_rule_id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database insertion."""
        data = self.model_dump()
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat()
        return data


class AgentResult(BaseModel):
    """Standard result format returned by all agents."""

    agent: str
    status: Literal["complete", "error", "partial"]
    stats: dict = Field(default_factory=dict)
    next_step: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()


class ParserResult(AgentResult):
    """Result from parser agent."""

    agent: Literal["parser"] = "parser"
    stats: dict = Field(default_factory=lambda: {
        "rows_parsed": 0,
        "rows_inserted": 0,
        "errors": 0
    })


class LearnerResult(AgentResult):
    """Result from learner agent."""

    agent: Literal["learner"] = "learner"
    stats: dict = Field(default_factory=lambda: {
        "historical_transactions": 0,
        "rules_generated": 0,
        "unique_vendors": 0,
        "avg_confidence": 0.0
    })


class ClassifierResult(AgentResult):
    """Result from classifier agent."""

    agent: Literal["classifier"] = "classifier"
    stats: dict = Field(default_factory=lambda: {
        "processed": 0,
        "auto_coded": 0,
        "exceptions": 0,
        "avg_confidence": 0.0
    })


class ReviewerResult(AgentResult):
    """Result from reviewer agent."""

    agent: Literal["reviewer"] = "reviewer"
    stats: dict = Field(default_factory=lambda: {
        "reviewed": 0,
        "approved": 0,
        "overridden": 0,
        "new_rules_created": 0
    })


class ExporterResult(AgentResult):
    """Result from exporter agent."""

    agent: Literal["exporter"] = "exporter"
    stats: dict = Field(default_factory=lambda: {
        "transactions_exported": 0,
        "output_file": None
    })


class WorkspaceConfig(BaseModel):
    """Workspace configuration."""

    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    last_modified: Optional[datetime] = None
    sage_columns: Optional[dict] = None  # Will be populated after first Sage import
    bank_columns: Optional[dict] = None  # Will be populated after first bank import
    default_confidence_threshold: Decimal = Field(default=Decimal("0.70"), ge=0, le=1)
    min_rule_confidence: Decimal = Field(default=Decimal("0.75"), ge=0, le=1)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = self.model_dump()
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat()
        if data.get('last_modified'):
            data['last_modified'] = data['last_modified'].isoformat()
        if data.get('default_confidence_threshold'):
            data['default_confidence_threshold'] = float(data['default_confidence_threshold'])
        if data.get('min_rule_confidence'):
            data['min_rule_confidence'] = float(data['min_rule_confidence'])
        return data
