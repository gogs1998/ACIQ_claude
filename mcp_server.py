#!/usr/bin/env python3
"""
MCP Server for AccountantIQ
Connects Claude Desktop to your accounting data via Model Context Protocol
"""

import json
import sys
from pathlib import Path
from typing import Any

from accountantiq.core.workspace import Workspace


class AccountantIQMCPServer:
    """MCP Server for AccountantIQ."""

    def __init__(self, workspace_name: str = "production"):
        """Initialize MCP server."""
        self.workspace = Workspace(
            workspace_name,
            str(Path("accountantiq/data/workspaces").absolute())
        )
        self.db = self.workspace.get_database()

    def handle_request(self, request: dict) -> dict:
        """Handle MCP request."""
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            return self._list_tools()
        elif method == "tools/call":
            return self._call_tool(params)
        elif method == "resources/list":
            return self._list_resources()
        elif method == "resources/read":
            return self._read_resource(params)
        else:
            return {"error": f"Unknown method: {method}"}

    def _list_tools(self) -> dict:
        """List available tools."""
        return {
            "tools": [
                {
                    "name": "get_stats",
                    "description": "Get workspace statistics (total transactions, coded, uncoded, coverage)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_uncoded_transactions",
                    "description": "Get list of uncoded transactions with vendor names and amounts",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number to return (default 50)"
                            }
                        }
                    }
                },
                {
                    "name": "update_transaction_code",
                    "description": "Update nominal code for transactions from a specific vendor",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "vendor": {
                                "type": "string",
                                "description": "Vendor name to match"
                            },
                            "nominal_code": {
                                "type": "string",
                                "description": "New 4-digit nominal code"
                            },
                            "create_rule": {
                                "type": "boolean",
                                "description": "Whether to create a rule for future transactions (default true)"
                            }
                        },
                        "required": ["vendor", "nominal_code"]
                    }
                },
                {
                    "name": "search_transactions",
                    "description": "Search transactions by vendor, amount, or date range",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "vendor": {
                                "type": "string",
                                "description": "Vendor name to search for"
                            },
                            "min_amount": {
                                "type": "number",
                                "description": "Minimum amount"
                            },
                            "max_amount": {
                                "type": "number",
                                "description": "Maximum amount"
                            },
                            "nominal_code": {
                                "type": "string",
                                "description": "Filter by nominal code"
                            }
                        }
                    }
                },
                {
                    "name": "export_to_sage",
                    "description": "Export coded transactions to Sage 50 CSV format",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Output filename (default: sage_import.csv)"
                            }
                        }
                    }
                },
                {
                    "name": "get_vendor_groups",
                    "description": "Get uncoded transactions grouped by vendor, sorted by count",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Top N vendors to return (default 20)"
                            }
                        }
                    }
                }
            ]
        }

    def _call_tool(self, params: dict) -> dict:
        """Call a tool."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            if tool_name == "get_stats":
                return self._get_stats()
            elif tool_name == "get_uncoded_transactions":
                return self._get_uncoded_transactions(arguments)
            elif tool_name == "update_transaction_code":
                return self._update_transaction_code(arguments)
            elif tool_name == "search_transactions":
                return self._search_transactions(arguments)
            elif tool_name == "export_to_sage":
                return self._export_to_sage(arguments)
            elif tool_name == "get_vendor_groups":
                return self._get_vendor_groups(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}

    def _get_stats(self) -> dict:
        """Get workspace statistics."""
        bank_txns = self.db.get_transactions(source="bank")
        coded = [t for t in bank_txns if t.get('nominal_code')]
        uncoded = [t for t in bank_txns if not t.get('nominal_code')]

        rules = self.db.get_rules()

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "total_transactions": len(bank_txns),
                    "coded": len(coded),
                    "uncoded": len(uncoded),
                    "coverage_percent": round(len(coded) / len(bank_txns) * 100, 1) if bank_txns else 0,
                    "total_rules": len(rules)
                }, indent=2)
            }]
        }

    def _get_uncoded_transactions(self, args: dict) -> dict:
        """Get uncoded transactions."""
        limit = args.get("limit", 50)

        bank_txns = self.db.get_transactions(source="bank")
        uncoded = [t for t in bank_txns if not t.get('nominal_code')][:limit]

        result = []
        for t in uncoded:
            result.append({
                "id": t['id'],
                "date": str(t['date']),
                "vendor": t['vendor'],
                "amount": float(t['amount']),
                "details": t.get('details', '')
            })

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    def _update_transaction_code(self, args: dict) -> dict:
        """Update transaction codes for a vendor."""
        vendor = args.get("vendor")
        nominal_code = args.get("nominal_code")
        create_rule = args.get("create_rule", True)

        if not vendor or not nominal_code:
            return {"error": "vendor and nominal_code required"}

        # Find matching transactions
        bank_txns = self.db.get_transactions(source="bank")
        matching = [t for t in bank_txns if vendor.lower() in t['vendor'].lower()]

        if not matching:
            return {"error": f"No transactions found for vendor: {vendor}"}

        # Update transactions
        for txn in matching:
            self.db.update_transaction(txn['id'], {
                'nominal_code': nominal_code,
                'confidence': 1.0,
                'assigned_by': 'mcp_client',
                'reviewed': True
            })

        # Create rule if requested
        rule_id = None
        if create_rule:
            # Delete old rule
            self.db.conn.execute(
                "DELETE FROM rules WHERE vendor_pattern = ?",
                [matching[0]['vendor']]
            )

            # Create new rule
            rule_id = self.db.insert_rule({
                'vendor_pattern': matching[0]['vendor'],
                'nominal_code': nominal_code,
                'rule_type': 'exact',
                'confidence': 1.0,
                'created_by': 'reviewer'
            })

        return {
            "content": [{
                "type": "text",
                "text": f"Updated {len(matching)} transactions for '{matching[0]['vendor']}' to {nominal_code}. Rule ID: {rule_id}"
            }]
        }

    def _search_transactions(self, args: dict) -> dict:
        """Search transactions."""
        vendor = args.get("vendor", "").lower()
        min_amount = args.get("min_amount")
        max_amount = args.get("max_amount")
        nominal_code = args.get("nominal_code")

        bank_txns = self.db.get_transactions(source="bank")

        # Filter
        results = []
        for t in bank_txns:
            if vendor and vendor not in t['vendor'].lower():
                continue
            if min_amount and float(t['amount']) < min_amount:
                continue
            if max_amount and float(t['amount']) > max_amount:
                continue
            if nominal_code and t.get('nominal_code') != nominal_code:
                continue

            results.append({
                "date": str(t['date']),
                "vendor": t['vendor'],
                "amount": float(t['amount']),
                "nominal_code": t.get('nominal_code', 'UNCODED')
            })

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(results[:100], indent=2)  # Limit to 100
            }]
        }

    def _export_to_sage(self, args: dict) -> dict:
        """Export to Sage format."""
        from accountantiq.agents.exporter_agent.exporter_agent import ExporterAgent

        filename = args.get("filename", "sage_import.csv")

        exporter = ExporterAgent(str(self.workspace.workspace_path))
        result = exporter.run(output_filename=filename)

        if result.status == "complete":
            return {
                "content": [{
                    "type": "text",
                    "text": f"Exported {result.stats['transactions_exported']} transactions to {result.stats['output_file']}"
                }]
            }
        else:
            return {"error": result.error_message}

    def _get_vendor_groups(self, args: dict) -> dict:
        """Get vendor groups."""
        limit = args.get("limit", 20)

        from collections import defaultdict

        bank_txns = self.db.get_transactions(source="bank")
        uncoded = [t for t in bank_txns if not t.get('nominal_code')]

        by_vendor = defaultdict(list)
        for t in uncoded:
            by_vendor[t['vendor']].append(t)

        # Sort by count
        sorted_vendors = sorted(
            by_vendor.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:limit]

        result = []
        for vendor, txns in sorted_vendors:
            result.append({
                "vendor": vendor,
                "count": len(txns),
                "total_amount": sum(float(t['amount']) for t in txns),
                "example_amount": float(txns[0]['amount'])
            })

        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }

    def _list_resources(self) -> dict:
        """List available resources."""
        return {
            "resources": [
                {
                    "uri": "accountantiq://stats",
                    "name": "Workspace Statistics",
                    "description": "Current workspace stats",
                    "mimeType": "application/json"
                },
                {
                    "uri": "accountantiq://uncoded",
                    "name": "Uncoded Transactions",
                    "description": "All uncoded transactions",
                    "mimeType": "application/json"
                }
            ]
        }

    def _read_resource(self, params: dict) -> dict:
        """Read a resource."""
        uri = params.get("uri")

        if uri == "accountantiq://stats":
            return self._get_stats()
        elif uri == "accountantiq://uncoded":
            return self._get_uncoded_transactions({"limit": 1000})
        else:
            return {"error": f"Unknown resource: {uri}"}

    def run(self):
        """Run MCP server (stdio mode)."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                response = self.handle_request(request)

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                error_response = {"error": str(e)}
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()


def main():
    """Entry point."""
    server = AccountantIQMCPServer()
    server.run()


if __name__ == "__main__":
    main()
