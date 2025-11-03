"""
AI-powered nominal code suggester.
Combines rule-based + LLM suggestions for transaction coding.
"""

from typing import Dict, List, Optional, Tuple
import os
from decimal import Decimal


class AISuggester:
    """Suggests nominal codes using rule-based + LLM approaches."""

    def __init__(self, use_llm: bool = False, llm_provider: str = "openai"):
        """
        Initialize AI suggester.

        Args:
            use_llm: Whether to use LLM for suggestions
            llm_provider: LLM provider ('openai' or 'anthropic')
        """
        self.use_llm = use_llm
        self.llm_provider = llm_provider
        self.llm_client = None

        if use_llm:
            self._initialize_llm()

    def _initialize_llm(self):
        """Initialize LLM client if API key is available."""
        if self.llm_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    import openai
                    self.llm_client = openai.OpenAI(api_key=api_key)
                except ImportError:
                    print("⚠ OpenAI library not installed. Run: pip install openai")
            else:
                print("⚠ OPENAI_API_KEY not set. LLM suggestions disabled.")

        elif self.llm_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    import anthropic
                    self.llm_client = anthropic.Anthropic(api_key=api_key)
                except ImportError:
                    print("⚠ Anthropic library not installed. Run: pip install anthropic")
            else:
                print("⚠ ANTHROPIC_API_KEY not set. LLM suggestions disabled.")

    def suggest(
        self,
        transaction: Dict,
        historical_rules: List[Dict] = None,
        nominal_codes: Dict[str, str] = None
    ) -> List[Tuple[str, str, float]]:
        """
        Suggest nominal codes for a transaction.

        Args:
            transaction: Transaction dict with vendor, amount, details, etc.
            historical_rules: List of learned rules from database
            nominal_codes: Dict of nominal_code -> description

        Returns:
            List of (nominal_code, reasoning, confidence) tuples, sorted by confidence
        """
        suggestions = []

        # Layer 1: Rule-based suggestions (fast, free)
        rule_suggestions = self._rule_based_suggest(transaction)
        suggestions.extend(rule_suggestions)

        # Layer 2: LLM suggestions (intelligent, costs API calls)
        if self.use_llm and self.llm_client:
            llm_suggestions = self._llm_suggest(transaction, nominal_codes)
            suggestions.extend(llm_suggestions)

        # Remove duplicates, keep highest confidence
        seen = {}
        for code, reason, conf in suggestions:
            if code not in seen or conf > seen[code][1]:
                seen[code] = (reason, conf)

        # Sort by confidence descending
        result = [(code, reason, conf) for code, (reason, conf) in seen.items()]
        result.sort(key=lambda x: x[2], reverse=True)

        return result[:5]  # Top 5 suggestions

    def _rule_based_suggest(self, transaction: Dict) -> List[Tuple[str, str, float]]:
        """Rule-based suggestions using keyword matching."""
        vendor = transaction.get('vendor', '').lower()
        details = transaction.get('details', '').lower()
        amount = float(transaction.get('amount', 0))
        combined = vendor + ' ' + details

        suggestions = []

        # IT & Software
        if any(x in combined for x in ['apple', 'microsoft', 'google', 'software', 'adobe', 'dropbox', 'zoom']):
            suggestions.append(('7100', 'IT/Software subscription (keyword match)', 0.80))

        # Travel & Subsistence
        if any(x in combined for x in ['hotel', 'restaurant', 'cafe', 'food', 'eat', 'coffee', 'lunch', 'dinner']):
            suggestions.append(('7400', 'Travel & Subsistence (keyword match)', 0.75))

        # Motor expenses
        if any(x in combined for x in ['parking', 'fuel', 'petrol', 'diesel', 'uber', 'taxi', 'car', 'mot', 'kwik fit']):
            suggestions.append(('7500', 'Motor expenses (keyword match)', 0.75))

        # Insurance
        if 'insurance' in combined or 'admiral' in combined:
            suggestions.append(('7104', 'Insurance (keyword match)', 0.85))

        # Medical/Health
        if any(x in combined for x in ['medical', 'dental', 'doctor', 'pharma', 'health', 'clinic', 'surgery']):
            suggestions.append(('7200', 'Medical/Healthcare (keyword match)', 0.80))

        # Professional fees
        if any(x in combined for x in ['professional', 'membership', 'gdc', 'registration', 'subscription', 'accountant']):
            suggestions.append(('7600', 'Professional fees (keyword match)', 0.75))

        # Stationery/Office
        if any(x in combined for x in ['stationery', 'office', 'supplies', 'paper', 'printer', 'ink']):
            suggestions.append(('7300', 'Office supplies (keyword match)', 0.70))

        # Purchases (Amazon, eBay, etc)
        if any(x in combined for x in ['amazon', 'ebay', 'purchase', 'buy']):
            suggestions.append(('5000', 'Purchases (keyword match)', 0.65))

        # Utilities
        if any(x in combined for x in ['electric', 'gas', 'water', 'broadband', 'internet', 'phone', 'mobile']):
            suggestions.append(('7200', 'Utilities (keyword match)', 0.75))

        # Bank charges
        if any(x in combined for x in ['charges', 'bank fee', 'overdraft']):
            suggestions.append(('7901', 'Bank charges (keyword match)', 0.90))

        # High-value items might be capital expenditure
        if abs(amount) > 500:
            suggestions.append(('0030', 'Possible capital expenditure (high value)', 0.50))

        return suggestions

    def _llm_suggest(
        self,
        transaction: Dict,
        nominal_codes: Dict[str, str] = None
    ) -> List[Tuple[str, str, float]]:
        """Use LLM to suggest nominal codes with reasoning."""

        if not self.llm_client:
            return []

        # Build prompt
        vendor = transaction.get('vendor', 'Unknown')
        amount = float(transaction.get('amount', 0))
        details = transaction.get('details', '')
        date = transaction.get('date', '')

        # Format nominal codes for context
        codes_context = ""
        if nominal_codes:
            codes_context = "\n\nAvailable Nominal Codes:\n"
            for code, desc in sorted(nominal_codes.items())[:20]:  # Show top 20
                codes_context += f"- {code}: {desc}\n"

        prompt = f"""You are an expert accountant helping code business transactions.

Transaction to code:
- Date: {date}
- Vendor: {vendor}
- Amount: £{amount:.2f}
- Details: {details}
{codes_context}

Common UK nominal code categories:
- 1200-1299: Bank accounts
- 5000-5999: Purchases/Cost of Sales
- 7100: IT & Software
- 7104: Insurance
- 7200: Utilities/General expenses
- 7300: Office supplies
- 7400: Travel & Subsistence
- 7500: Motor expenses
- 7600: Professional fees
- 7901: Bank charges

Suggest the most appropriate nominal code for this transaction.
Provide your answer in this exact format:

CODE: [4-digit code]
REASONING: [One sentence explaining why]
CONFIDENCE: [0.0-1.0]

If unsure, suggest multiple codes, one per line."""

        try:
            if self.llm_provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",  # Fast and cheap
                    messages=[
                        {"role": "system", "content": "You are an expert UK accountant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )
                content = response.choices[0].message.content

            elif self.llm_provider == "anthropic":
                response = self.llm_client.messages.create(
                    model="claude-3-haiku-20240307",  # Fast and cheap
                    max_tokens=200,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                content = response.content[0].text

            # Parse LLM response
            return self._parse_llm_response(content)

        except Exception as e:
            print(f"⚠ LLM suggestion failed: {e}")
            return []

    def _parse_llm_response(self, content: str) -> List[Tuple[str, str, float]]:
        """Parse LLM response into suggestions."""
        suggestions = []
        lines = content.strip().split('\n')

        current_code = None
        current_reason = None
        current_conf = None

        for line in lines:
            line = line.strip()
            if line.startswith('CODE:'):
                current_code = line.replace('CODE:', '').strip()
            elif line.startswith('REASONING:'):
                current_reason = line.replace('REASONING:', '').strip()
            elif line.startswith('CONFIDENCE:'):
                conf_str = line.replace('CONFIDENCE:', '').strip()
                try:
                    current_conf = float(conf_str)
                except ValueError:
                    current_conf = 0.7  # Default

                # Complete suggestion
                if current_code and current_reason:
                    suggestions.append((
                        current_code,
                        f"LLM: {current_reason}",
                        current_conf
                    ))
                    current_code = None
                    current_reason = None
                    current_conf = None

        return suggestions


# Standard UK nominal codes (simplified)
STANDARD_NOMINAL_CODES = {
    "1200": "Bank Current Account",
    "1210": "Bank Deposit Account",
    "0030": "Office Equipment",
    "0040": "Furniture and Fixtures",
    "0050": "Motor Vehicles",
    "5000": "Purchases",
    "5001": "Cost of Sales",
    "6201": "Advertising",
    "7000": "Gross Wages",
    "7100": "IT & Software",
    "7103": "Accountancy Fees",
    "7104": "Insurance",
    "7200": "Light, Heat, Power",
    "7300": "Printing, Postage and Stationery",
    "7400": "Travel and Subsistence",
    "7500": "Motor Expenses",
    "7501": "Vehicle Hire",
    "7600": "Professional Fees",
    "7700": "Repairs and Renewals",
    "7800": "Telephone and Fax",
    "7900": "Sundry Expenses",
    "7901": "Bank Charges",
    "7902": "Bad Debts",
    "7903": "Subscriptions and Memberships",
}
