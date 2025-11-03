"""
Learner Agent - Builds vendor→nominal code mappings from historical data.
"""

from pathlib import Path
import time
from typing import List
from collections import defaultdict

from accountantiq.core.database import Database
from accountantiq.core.models import LearnerResult, Rule
from rapidfuzz import fuzz


class LearnerAgent:
    """Learns vendor patterns from historical transactions."""

    def __init__(self, workspace_path: str):
        """
        Initialize learner agent.

        Args:
            workspace_path: Path to workspace
        """
        self.workspace_path = Path(workspace_path)
        self.db_path = self.workspace_path / "accountant.db"

    def run(self, min_confidence: float = 0.75) -> LearnerResult:
        """
        Analyze historical transactions and generate rules.

        Args:
            min_confidence: Minimum confidence threshold for rules

        Returns:
            LearnerResult with statistics
        """
        start_time = time.time()

        with Database(str(self.db_path)) as db:
            # Get historical transactions
            historical_txns = db.get_transactions(source="history")

            if not historical_txns:
                return LearnerResult(
                    agent="learner",
                    status="error",
                    error_message="No historical transactions found",
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            # Build vendor→nominal code mappings
            vendor_mappings = self._analyze_patterns(historical_txns)

            # Generate rules
            rules_created = 0
            for vendor_pattern, data in vendor_mappings.items():
                confidence = data['confidence']

                if confidence >= min_confidence:
                    rule = Rule(
                        vendor_pattern=vendor_pattern,
                        nominal_code=data['nominal_code'],
                        rule_type="fuzzy",
                        confidence=confidence,
                        match_count=data['count'],
                        created_by="learner"
                    )
                    db.insert_rule(rule.to_dict())
                    rules_created += 1

            # Log action
            db.log_agent_action(
                agent_name="learner",
                action="learn_patterns",
                input_summary=f"historical_txns={len(historical_txns)}",
                output_summary=f"rules_created={rules_created}",
                duration_ms=int((time.time() - start_time) * 1000)
            )

            return LearnerResult(
                agent="learner",
                status="complete",
                stats={
                    "historical_transactions": len(historical_txns),
                    "rules_generated": rules_created,
                    "unique_vendors": len(vendor_mappings),
                    "avg_confidence": sum(d['confidence'] for d in vendor_mappings.values()) / len(vendor_mappings) if vendor_mappings else 0
                },
                duration_ms=int((time.time() - start_time) * 1000),
                next_step="classifier"
            )

    def _analyze_patterns(self, transactions: List[dict]) -> dict:
        """
        Analyze transaction patterns to build vendor mappings.

        Args:
            transactions: List of historical transactions

        Returns:
            Dict mapping vendor patterns to nominal codes with confidence
        """
        vendor_codes = defaultdict(lambda: defaultdict(int))

        # Count vendor→nominal code occurrences
        for txn in transactions:
            if txn.get('nominal_code'):
                vendor = txn['vendor'].lower().strip()
                code = txn['nominal_code']
                vendor_codes[vendor][code] += 1

        # Calculate confidence scores
        result = {}
        for vendor, codes in vendor_codes.items():
            total = sum(codes.values())
            most_common_code = max(codes.items(), key=lambda x: x[1])
            code, count = most_common_code

            confidence = count / total
            result[vendor] = {
                'nominal_code': code,
                'count': count,
                'confidence': confidence
            }

        return result
