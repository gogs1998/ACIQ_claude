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

    def run(self, min_confidence: float = 0.75, smart_matching: bool = True) -> LearnerResult:
        """
        Analyze historical transactions and generate rules.

        Args:
            min_confidence: Minimum confidence threshold for rules
            smart_matching: If True, match bank and Sage transactions by date+amount

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

            # Get bank transactions if they exist (for smart matching)
            bank_txns = db.get_transactions(source="bank")

            # Build vendor→nominal code mappings
            vendor_mappings = self._analyze_patterns(historical_txns)

            # If we have bank data, do smart matching by date+amount
            smart_rules = 0
            if smart_matching and bank_txns:
                smart_rules = self._create_smart_rules(historical_txns, bank_txns, db, min_confidence)

            # Generate rules from historical data alone
            basic_rules = 0
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
                    basic_rules += 1

            total_rules = smart_rules + basic_rules

            # Log action
            db.log_agent_action(
                agent_name="learner",
                action="learn_patterns",
                input_summary=f"historical_txns={len(historical_txns)}, bank_txns={len(bank_txns)}, smart_matching={smart_matching}",
                output_summary=f"smart_rules={smart_rules}, basic_rules={basic_rules}, total={total_rules}",
                duration_ms=int((time.time() - start_time) * 1000)
            )

            return LearnerResult(
                agent="learner",
                status="complete",
                stats={
                    "historical_transactions": len(historical_txns),
                    "rules_generated": total_rules,
                    "smart_rules": smart_rules,
                    "basic_rules": basic_rules,
                    "unique_vendors": len(vendor_mappings),
                    "avg_confidence": sum(d['confidence'] for d in vendor_mappings.values()) / len(vendor_mappings) if vendor_mappings else 0
                },
                duration_ms=int((time.time() - start_time) * 1000),
                next_step="classifier"
            )

    def _create_smart_rules(
        self,
        sage_txns: List[dict],
        bank_txns: List[dict],
        db: Database,
        min_confidence: float
    ) -> int:
        """
        Create rules by matching bank and Sage transactions by date+amount.

        This learns the ACTUAL mapping between bank descriptions and Sage nominal codes.

        Args:
            sage_txns: Sage historical transactions (with nominal codes)
            bank_txns: Bank transactions (without nominal codes)
            db: Database connection
            min_confidence: Minimum confidence for rules

        Returns:
            Number of smart rules created
        """
        from datetime import date as Date
        from decimal import Decimal

        # Build index of Sage transactions by (date, absolute amount)
        sage_index = defaultdict(list)
        for txn in sage_txns:
            if txn.get('nominal_code'):
                # Create key from date and amount
                txn_date = txn['date']
                if isinstance(txn_date, str):
                    # Convert string date to date object
                    from datetime import datetime
                    try:
                        txn_date = datetime.strptime(txn_date, "%Y-%m-%d").date()
                    except:
                        continue

                # Use ABSOLUTE amount (ignore sign differences between bank/Sage)
                amount = float(txn.get('amount', 0))
                amount_key = round(abs(amount), 2)

                key = (txn_date, amount_key)
                sage_index[key].append(txn)

        # Match bank transactions to Sage transactions
        matches = []
        for bank_txn in bank_txns:
            bank_date = bank_txn['date']
            if isinstance(bank_date, str):
                from datetime import datetime
                try:
                    bank_date = datetime.strptime(bank_date, "%Y-%m-%d").date()
                except:
                    continue

            # Use ABSOLUTE amount to match regardless of sign
            bank_amount = round(abs(float(bank_txn.get('amount', 0))), 2)
            key = (bank_date, bank_amount)

            # Find matching Sage transaction(s)
            if key in sage_index:
                sage_matches = sage_index[key]
                for sage_txn in sage_matches:
                    matches.append({
                        'bank_vendor': bank_txn['vendor'],
                        'sage_vendor': sage_txn['vendor'],
                        'nominal_code': sage_txn['nominal_code'],
                        'date': bank_date,
                        'amount': bank_amount
                    })

        # Build rules from matches
        # Group by bank_vendor → nominal_code
        vendor_code_map = defaultdict(lambda: defaultdict(int))
        for match in matches:
            bank_vendor = match['bank_vendor'].lower().strip()
            nominal_code = match['nominal_code']
            vendor_code_map[bank_vendor][nominal_code] += 1

        # Create rules
        rules_created = 0
        for bank_vendor, code_counts in vendor_code_map.items():
            total = sum(code_counts.values())
            most_common = max(code_counts.items(), key=lambda x: x[1])
            nominal_code, count = most_common

            # Calculate confidence (round to 2 decimal places for Pydantic)
            confidence = count / total
            confidence_rounded = round(confidence, 2)

            if confidence >= min_confidence:
                rule = Rule(
                    vendor_pattern=bank_vendor,
                    nominal_code=nominal_code,
                    rule_type="exact",  # Exact match for bank vendor names
                    confidence=Decimal(str(confidence_rounded)),
                    match_count=count,
                    created_by="learner"
                )
                db.insert_rule(rule.to_dict())
                rules_created += 1

        return rules_created

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
