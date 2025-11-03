#!/usr/bin/env python3
"""
LLM Chat Interface for AccountantIQ
Natural language interaction with your accounting data
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box
from pathlib import Path
import os
import json

from accountantiq.core.workspace import Workspace

console = Console()


class ChatInterface:
    """Natural language chat interface for accounting operations."""

    def __init__(self, workspace_name: str = "production"):
        """Initialize chat interface."""
        self.workspace = Workspace(
            workspace_name,
            str(Path("accountantiq/data/workspaces").absolute())
        )
        self.db = self.workspace.get_database()
        self.llm_client = None
        self.conversation_history = []

        # Initialize LLM
        self._initialize_llm()

    def _initialize_llm(self):
        """Initialize LLM client."""
        # Try OpenAI first
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                self.llm_client = openai.OpenAI(api_key=api_key)
                self.llm_provider = "openai"
                return
            except ImportError:
                pass

        # Try Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                self.llm_client = anthropic.Anthropic(api_key=api_key)
                self.llm_provider = "anthropic"
                return
            except ImportError:
                pass

        console.print("[red]⚠ No LLM API key found![/red]")
        console.print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY to use chat.")
        exit(1)

    def run(self):
        """Run interactive chat."""
        console.clear()
        self._show_welcome()

        while True:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if user_input.lower() in ['exit', 'quit', 'q']:
                console.print("\n[green]Goodbye![/green]\n")
                break

            if user_input.lower() in ['help', '?']:
                self._show_help()
                continue

            # Process with LLM
            response = self._process_with_llm(user_input)

            # Display response
            console.print(f"\n[bold yellow]Assistant[/bold yellow]: {response}\n")

        self.db.close()

    def _show_welcome(self):
        """Show welcome message."""
        welcome = """
[bold cyan]AccountantIQ - LLM Chat Interface[/bold cyan]

Chat naturally with your accounting data!

Examples:
  • "Change The Woodend to 7403"
  • "Show me all transactions over £500"
  • "What's coded as 7100?"
  • "Create rule: Starbucks → 7400"
  • "How many uncoded transactions?"
  • "Export my data"

Type 'help' for more examples, 'quit' to exit.
        """
        console.print(Panel(welcome, box=box.DOUBLE, border_style="cyan"))

    def _show_help(self):
        """Show help examples."""
        help_text = """
[bold cyan]What You Can Ask:[/bold cyan]

[bold yellow]Change Codes:[/bold yellow]
  • "Change Apple.Com/Bill to 7100"
  • "Recode all Amazon to 5000"
  • "Update Microsoft to 7103"

[bold yellow]View Data:[/bold yellow]
  • "Show uncoded transactions"
  • "What's the coverage?"
  • "List all 7500 transactions"
  • "Show vendors coded as 7400"

[bold yellow]Create Rules:[/bold yellow]
  • "Create rule: Starbucks → 7400"
  • "Add rule for Uber as 7500"

[bold yellow]Statistics:[/bold yellow]
  • "How many transactions are coded?"
  • "What's my progress?"
  • "Show me the breakdown by code"

[bold yellow]Export:[/bold yellow]
  • "Export to Sage"
  • "Generate CSV for import"

[bold yellow]Analysis:[/bold yellow]
  • "Show me expensive transactions"
  • "What are the biggest uncoded vendors?"
  • "Analyze my spending on 7500"
        """
        console.print(Panel(help_text, box=box.ROUNDED, border_style="yellow"))

    def _process_with_llm(self, user_input: str) -> str:
        """Process user input with LLM and execute actions."""

        # Get current stats for context
        bank_txns = self.db.get_transactions(source="bank")
        coded = [t for t in bank_txns if t.get('nominal_code')]
        uncoded = [t for t in bank_txns if not t.get('nominal_code')]

        context = {
            "total_transactions": len(bank_txns),
            "coded": len(coded),
            "uncoded": len(uncoded),
            "coverage_percent": round(len(coded) / len(bank_txns) * 100, 1)
        }

        # Build system prompt
        system_prompt = f"""You are an AI assistant for AccountantIQ, an automated bookkeeping system.

Current workspace stats:
- Total transactions: {context['total_transactions']}
- Coded: {context['coded']} ({context['coverage_percent']}%)
- Uncoded: {context['uncoded']}

You help users manage their accounting data through natural language.

When the user asks to change/update/recode transactions, respond with a JSON action:
{{
  "action": "update_code",
  "vendor": "vendor name",
  "new_code": "7403",
  "explanation": "Updated to Entertainment"
}}

When asked about data, query the database and respond naturally.

Common UK nominal codes:
- 1210: Bank Account
- 5000: Purchases
- 7100: IT & Software
- 7103: Accountancy
- 7104: Insurance
- 7200: Utilities/General
- 7300: Office Supplies
- 7400: Travel & Subsistence
- 7403: Entertainment
- 7500: Motor Expenses
- 7600: Professional Fees
- 7901: Bank Charges

Be helpful, concise, and execute actions when requested."""

        # Call LLM
        try:
            if self.llm_provider == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.3
                )
                llm_response = response.choices[0].message.content

            elif self.llm_provider == "anthropic":
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    temperature=0.3,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_input}
                    ]
                )
                llm_response = response.content[0].text

            # Check if LLM returned a JSON action
            if "```json" in llm_response or llm_response.strip().startswith("{"):
                action_result = self._execute_action(llm_response)
                return action_result

            return llm_response

        except Exception as e:
            return f"[red]Error: {e}[/red]"

    def _execute_action(self, llm_response: str) -> str:
        """Execute action from LLM response."""

        # Extract JSON
        try:
            # Handle markdown code blocks
            if "```json" in llm_response:
                json_str = llm_response.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_response:
                json_str = llm_response.split("```")[1].split("```")[0].strip()
            else:
                json_str = llm_response.strip()

            action = json.loads(json_str)
        except:
            return llm_response  # Not a JSON action, return as-is

        # Execute action
        if action.get("action") == "update_code":
            vendor = action.get("vendor")
            new_code = action.get("new_code")
            explanation = action.get("explanation", "")

            # Find transactions
            bank_txns = self.db.get_transactions(source="bank")
            matching = [t for t in bank_txns if vendor.lower() in t['vendor'].lower()]

            if not matching:
                return f"No transactions found for vendor: {vendor}"

            # Update transactions
            for txn in matching:
                self.db.update_transaction(txn['id'], {
                    'nominal_code': new_code,
                    'confidence': 1.0,
                    'assigned_by': 'llm_chat',
                    'reviewed': True
                })

            # Update/create rule
            self.db.conn.execute(
                "DELETE FROM rules WHERE vendor_pattern = ?",
                [matching[0]['vendor']]
            )

            rule_id = self.db.insert_rule({
                'vendor_pattern': matching[0]['vendor'],
                'nominal_code': new_code,
                'rule_type': 'exact',
                'confidence': 1.0,
                'created_by': 'reviewer'
            })

            result = f"""✓ Updated {len(matching)} transactions for "{matching[0]['vendor']}"
✓ Changed to {new_code} ({explanation})
✓ Rule created (ID: {rule_id})

Future transactions from this vendor will auto-code to {new_code}."""

            return result

        return "Action not recognized."

    def __del__(self):
        """Cleanup."""
        if hasattr(self, 'db'):
            self.db.close()


def main():
    """Entry point."""
    import sys

    workspace = sys.argv[1] if len(sys.argv) > 1 else "production"

    chat = ChatInterface(workspace_name=workspace)
    chat.run()


if __name__ == "__main__":
    main()
