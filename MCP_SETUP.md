# MCP Server Setup - Connect Claude Desktop to AccountantIQ

## 🎯 The Vision

Instead of running CLI commands, just chat with Claude Desktop and manage your accounting data naturally!

**Example conversation:**
```
You: Change The Woodend and Angels Hotel to 7403

Claude: ✅ I've updated 24 transactions:
        • The Woodend: 11 transactions → 7403 (Entertainment)
        • Angels Hotel Bar & Res: 13 transactions → 7403 (Entertainment)
        • Created rules for both vendors

        Future transactions will auto-code to 7403.

You: What's my coverage now?

Claude: Your workspace has:
        • 1,287 coded transactions (82.1%)
        • 281 uncoded (17.9%)
        • 712 total rules

        You've improved coverage by 4.7% since initial import!

You: Show me the top 5 uncoded vendors

Claude: Here are the top 5 uncoded vendors:
        1. Sq *The Upper Krust (8 transactions, £382.08 total)
        2. Applecare Uk (7 transactions, £66.43 total)
        3. Teleta Pharma Ltd (6 transactions, £402.00 total)
        ...
```

## 🚀 Two Approaches

### Approach 1: Simple LLM Chat (Current)
```bash
# Requires: OpenAI or Anthropic API key
export OPENAI_API_KEY="sk-..."
python chat.py production
```

**Pros:**
- Works right now
- Simple setup
- Terminal-based

**Cons:**
- Separate terminal app
- Not integrated with Claude Desktop

### Approach 2: MCP Server (Recommended!)
Connect Claude Desktop to your AccountantIQ data via Model Context Protocol.

**Pros:**
- ✅ Chat directly in Claude Desktop
- ✅ No separate terminal needed
- ✅ Full Claude.ai interface
- ✅ Voice input support
- ✅ Better context management
- ✅ Integrated with your workflow

**Cons:**
- Requires Claude Desktop app
- Slightly more setup

---

## 📦 MCP Server Setup

### Step 1: Install Claude Desktop

Download from: https://claude.ai/download

### Step 2: Configure MCP Server

1. **Find your Claude Desktop config file:**

   **Windows:**
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

   **Mac:**
   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. **Add AccountantIQ MCP server:**

   Open the config file and add:

   ```json
   {
     "mcpServers": {
       "accountantiq": {
         "command": "python",
         "args": [
           "D:\\Claude\\ACIQ\\mcp_server.py"
         ],
         "env": {
           "WORKSPACE": "production"
         }
       }
     }
   }
   ```

   **Mac/Linux:**
   ```json
   {
     "mcpServers": {
       "accountantiq": {
         "command": "python3",
         "args": [
           "/path/to/ACIQ/mcp_server.py"
         ],
         "env": {
           "WORKSPACE": "production"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**

### Step 3: Verify Connection

In Claude Desktop, you should see a 🔌 icon or "MCP" indicator showing AccountantIQ is connected.

---

## 💬 What You Can Ask

### Change Transaction Codes
```
You: Change The Woodend to 7403
You: Recode all Apple transactions to 7100
You: Update Microsoft to IT expenses (7100)
```

### View Data
```
You: Show me uncoded transactions
You: What's my coverage?
You: List all transactions coded as 7500
You: Show me the top 10 uncoded vendors
```

### Create Rules
```
You: Create a rule: Starbucks → 7400
You: Add rule for all Uber transactions as 7500
```

### Analysis
```
You: How much have I spent on motor expenses (7500)?
You: Show me all transactions over £500
You: What are my biggest uncoded vendors?
You: Analyze my spending breakdown
```

### Export
```
You: Export to Sage 50
You: Generate the CSV for import
```

---

## 🛠️ Available MCP Tools

The MCP server exposes these tools to Claude:

### 1. `get_stats`
Get workspace statistics (coverage, totals, rules).

### 2. `get_uncoded_transactions`
List uncoded transactions with details.

**Parameters:**
- `limit` (optional): Max number to return

### 3. `update_transaction_code`
Update nominal code for a vendor's transactions.

**Parameters:**
- `vendor` (required): Vendor name
- `nominal_code` (required): New 4-digit code
- `create_rule` (optional): Create rule for future (default: true)

### 4. `search_transactions`
Search transactions by criteria.

**Parameters:**
- `vendor` (optional): Vendor name to search
- `min_amount` (optional): Minimum amount
- `max_amount` (optional): Maximum amount
- `nominal_code` (optional): Filter by code

### 5. `export_to_sage`
Export coded transactions to Sage 50 CSV.

**Parameters:**
- `filename` (optional): Output filename

### 6. `get_vendor_groups`
Get uncoded transactions grouped by vendor.

**Parameters:**
- `limit` (optional): Top N vendors (default: 20)

---

## 🎨 Example Conversations

### Example 1: Quick Batch Update
```
You: I need to recode some vendors. The Woodend and Angels Hotel should be 7403 (Entertainment)

Claude: I'll update those for you.

[Uses update_transaction_code tool]

✅ Updated:
• The Woodend: 11 transactions → 7403
• Angels Hotel Bar & Res: 13 transactions → 7403
• Created rules for both

Total: 24 transactions recoded to Entertainment (7403)

You: Perfect! What's my coverage now?

Claude: [Uses get_stats tool]

Your coverage is now 82.1% (1,287 out of 1,568 transactions coded).
You have 281 uncoded transactions remaining across 208 vendor groups.
```

### Example 2: Smart Analysis
```
You: What are my biggest expenses that aren't coded yet?

Claude: [Uses get_vendor_groups tool and search_transactions]

Here are your largest uncoded expenses:

1. Emma Findlay: 6 transactions, £6,629.64 total
   - Largest: £1,104.94
   - Suggest: 7600 (Professional Fees) or 7200 (General)

2. Close Brothers Ltd: 3 transactions, £19,105.26 total
   - Largest: £6,368.42
   - Suggest: 7901 (Bank Charges/Loan)

3. Wigmore Medical Lt: 4 transactions, £1,510.00 total
   - Suggest: 7200 (Medical/Healthcare)

Would you like me to code any of these?

You: Yes, code Emma Findlay as 7600 and Wigmore Medical as 7200

Claude: [Uses update_transaction_code twice]

✅ Done:
• Emma Findlay: 6 transactions → 7600 (Professional Fees)
• Wigmore Medical Lt: 4 transactions → 7200 (Healthcare)

That's 10 more transactions coded, bringing you to 82.7% coverage!
```

### Example 3: Export Workflow
```
You: I'm done reviewing. Export my data for Sage 50

Claude: [Uses export_to_sage tool]

✅ Exported 1,287 coded transactions to:
   D:\Claude\ACIQ\accountantiq\data\workspaces\production\exports\sage_import.csv

The file is ready to import into Sage 50:
1. Open Sage 50
2. File → Import → CSV
3. Select the file above
4. Map columns: Date, Type, Nominal Code, Reference, Details, Debit, Credit
5. Import!

Your 82.1% coverage means most of your bookkeeping is automated.
The remaining 281 transactions need manual review.
```

---

## 🔧 Troubleshooting

### MCP Server Not Connecting

1. **Check config file location:**
   ```bash
   # Windows
   echo %APPDATA%\Claude\claude_desktop_config.json

   # Mac
   echo ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Verify Python path:**
   ```bash
   which python  # Mac/Linux
   where python  # Windows
   ```

3. **Test MCP server directly:**
   ```bash
   python mcp_server.py
   # Should wait for input (stdin mode)
   ```

4. **Check Claude Desktop logs:**
   - Windows: `%APPDATA%\Claude\logs\`
   - Mac: `~/Library/Logs/Claude/`

### Database Locked Error

If you get "database locked":
- Close the dashboard if running
- Close any Python processes accessing the DB
- Restart Claude Desktop

---

## 🚀 Next Steps

1. **Set up MCP server** (5 minutes)
2. **Chat naturally** with your accounting data
3. **Code transactions** in plain English
4. **Export when done** - ready for Sage 50

**The future of accounting:**
- No CLI commands to remember
- No terminal windows
- Just chat naturally with Claude
- Voice input supported!

---

## 📊 Comparison

| Feature | Dashboard | Chat CLI | MCP Server |
|---------|-----------|----------|------------|
| **UI** | Rich terminal | Rich terminal | Claude Desktop |
| **Input** | Keyboard only | Text only | Text + Voice |
| **Context** | Single session | Single session | Persistent |
| **Integration** | Standalone | Standalone | Native Claude |
| **Learning Curve** | Low | Low | Lowest |
| **Best For** | Batch review | Quick updates | Everything |

## 🎯 Recommendation

**Start with:** Dashboard for initial bulk coding (fast, visual)
**Switch to:** MCP Server for ongoing maintenance (natural, integrated)
**Use:** Chat CLI for quick terminal updates (fast, no GUI needed)

---

**Ready to try?** Set up the MCP server and start chatting with your accounting data! 🚀
