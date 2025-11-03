"""
Reviewer Agent - Handles exceptions and learns from user corrections.
"""

from pathlib import Path
import time
from typing import List, Optional

from accountantiq.core.database import Database
from accountantiq.core.models import ReviewerResult, Rule, Override


class ReviewerAgent:
    """Reviews low-confidence transactions and learns from corrections."""

    def __init__(self, workspace_path: str):
        """
        Initialize reviewer agent.

        Args:
            workspace_path: Path to workspace
        """
        self.workspace_path = Path(workspace_path)
        self.db_path = self.workspace_path / "accountant.db"

    def run(
        self,
        interactive: bool = True,
        review_threshold: float = 0.70
    ) -> ReviewerResult:
        """
        Review low-confidence transactions.

        Args:
            interactive: If True, prompt user for reviews (CLI mode)
            review_threshold: Confidence threshold for review

        Returns:
            ReviewerResult with statistics
        """
        start_time = time.time()

        with Database(str(self.db_path)) as db:
            # Get transactions needing review
            all_txns = db.get_transactions(source="bank", reviewed=False)
            needs_review = [
                t for t in all_txns
                if t.get('confidence') is None or float(t.get('confidence', 0)) < review_threshold
            ]

            if not needs_review:
                return ReviewerResult(
                    agent="reviewer",
                    status="complete",
                    stats={
                        "reviewed": 0,
                        "approved": 0,
                        "overridden": 0,
                        "new_rules_created": 0
                    },
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            reviewed = 0
            approved = 0
            overridden = 0
            new_rules = 0

            if interactive:
                # Interactive mode - would be implemented in CLI
                # For now, just mark as needing manual review
                pass
            else:
                # Non-interactive mode - just collect stats
                reviewed = len(needs_review)

            # Log action
            db.log_agent_action(
                agent_name="reviewer",
                action="review_transactions",
                input_summary=f"needs_review={len(needs_review)}",
                output_summary=f"reviewed={reviewed}, overridden={overridden}",
                duration_ms=int((time.time() - start_time) * 1000)
            )

            return ReviewerResult(
                agent="reviewer",
                status="complete",
                stats={
                    "reviewed": reviewed,
                    "approved": approved,
                    "overridden": overridden,
                    "new_rules_created": new_rules
                },
                duration_ms=int((time.time() - start_time) * 1000),
                next_step="exporter"
            )

    def handle_override(
        self,
        transaction_id: int,
        corrected_code: str,
        create_rule: bool = True
    ) -> Optional[int]:
        """
        Handle user override of a transaction.

        Args:
            transaction_id: ID of transaction being overridden
            corrected_code: User's corrected nominal code
            create_rule: If True, create new rule from override

        Returns:
            New rule ID if created, else None
        """
        with Database(str(self.db_path)) as db:
            # Get transaction
            txns = db.get_transactions()
            txn = next((t for t in txns if t['id'] == transaction_id), None)

            if not txn:
                return None

            original_code = txn.get('nominal_code')

            # Create override record
            override = Override(
                transaction_id=transaction_id,
                original_code=original_code,
                corrected_code=corrected_code
            )

            # Update transaction
            db.update_transaction(transaction_id, {
                'nominal_code': corrected_code,
                'confidence': 1.0,
                'reviewed': True,
                'assigned_by': 'reviewer',
                'explanation': f"User override from {original_code} to {corrected_code}"
            })

            # Create rule if requested
            rule_id = None
            if create_rule:
                rule = Rule(
                    vendor_pattern=txn['vendor'],
                    nominal_code=corrected_code,
                    rule_type="exact",
                    confidence=0.90,  # High confidence for user-created rules
                    created_by="reviewer"
                )
                rule_id = db.insert_rule(rule.to_dict())
                override.created_rule_id = rule_id

            # Save override
            db.insert_override(override.to_dict())

            return rule_id
