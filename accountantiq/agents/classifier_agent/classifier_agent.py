"""
Classifier Agent - Auto-codes new transactions using learned rules.
"""

from pathlib import Path
import time
from typing import List, Optional, Tuple

from accountantiq.core.database import Database
from accountantiq.core.models import ClassifierResult
from rapidfuzz import fuzz, process


class ClassifierAgent:
    """Classifies new transactions using learned rules."""

    def __init__(self, workspace_path: str):
        """
        Initialize classifier agent.

        Args:
            workspace_path: Path to workspace
        """
        self.workspace_path = Path(workspace_path)
        self.db_path = self.workspace_path / "accountant.db"

    def run(self, confidence_threshold: float = 0.70) -> ClassifierResult:
        """
        Classify uncoded bank transactions.

        Args:
            confidence_threshold: Minimum confidence to auto-code

        Returns:
            ClassifierResult with statistics
        """
        start_time = time.time()

        with Database(str(self.db_path)) as db:
            # Get bank transactions that need coding
            bank_txns = db.get_transactions(source="bank")
            uncoded = [t for t in bank_txns if not t.get('nominal_code')]

            if not uncoded:
                return ClassifierResult(
                    agent="classifier",
                    status="complete",
                    stats={
                        "processed": 0,
                        "auto_coded": 0,
                        "exceptions": 0,
                        "avg_confidence": 0.0
                    },
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            # Get rules
            rules = db.get_rules()

            # Classify each transaction
            auto_coded = 0
            exceptions = 0
            confidences = []

            for txn in uncoded:
                match, confidence, explanation = self._match_transaction(
                    txn, rules
                )

                if match and confidence >= confidence_threshold:
                    # Auto-code transaction
                    db.update_transaction(txn['id'], {
                        'nominal_code': match['nominal_code'],
                        'confidence': confidence,
                        'explanation': explanation,
                        'assigned_by': 'classifier'
                    })
                    db.update_rule_stats(match['id'])
                    auto_coded += 1
                    confidences.append(confidence)
                else:
                    # Mark as exception for review
                    exceptions += 1
                    if match:
                        # Store low-confidence suggestion
                        db.update_transaction(txn['id'], {
                            'nominal_code': match['nominal_code'],
                            'confidence': confidence,
                            'explanation': explanation + " [NEEDS REVIEW]",
                            'assigned_by': 'classifier'
                        })
                        confidences.append(confidence)

            # Log action
            db.log_agent_action(
                agent_name="classifier",
                action="classify_transactions",
                input_summary=f"uncoded={len(uncoded)}",
                output_summary=f"auto_coded={auto_coded}, exceptions={exceptions}",
                duration_ms=int((time.time() - start_time) * 1000)
            )

            return ClassifierResult(
                agent="classifier",
                status="complete",
                stats={
                    "processed": len(uncoded),
                    "auto_coded": auto_coded,
                    "exceptions": exceptions,
                    "avg_confidence": sum(confidences) / len(confidences) if confidences else 0.0
                },
                duration_ms=int((time.time() - start_time) * 1000),
                next_step="reviewer" if exceptions > 0 else "exporter"
            )

    def _match_transaction(
        self,
        transaction: dict,
        rules: List[dict]
    ) -> Tuple[Optional[dict], float, str]:
        """
        Match transaction to best rule.

        Args:
            transaction: Transaction to match
            rules: List of available rules

        Returns:
            Tuple of (matched_rule, confidence, explanation)
        """
        if not rules:
            return None, 0.0, "No rules available"

        vendor = transaction['vendor'].lower().strip()

        # Try exact match first
        for rule in rules:
            if rule['vendor_pattern'].lower().strip() == vendor:
                return (
                    rule,
                    float(rule['confidence']),
                    f"Exact match for vendor '{vendor}'"
                )

        # Try fuzzy match
        best_match = None
        best_score = 0

        for rule in rules:
            score = fuzz.ratio(vendor, rule['vendor_pattern'].lower().strip())
            if score > best_score and score >= 85:  # 85% similarity threshold
                best_score = score
                best_match = rule

        if best_match:
            # Combine rule confidence with match score
            combined_confidence = (float(best_match['confidence']) + (best_score / 100)) / 2
            return (
                best_match,
                combined_confidence,
                f"Fuzzy match ({best_score}% similar) to '{best_match['vendor_pattern']}'"
            )

        return None, 0.0, "No matching rule found"
