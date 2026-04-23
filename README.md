# expensefn

A lightweight MCP (Model Context Protocol) server for tracking expenses and credits using SQLite.

Designed for simplicity, auditability, and easy integration with AI agents or automation workflows.

---

## Features

* Track expenses with category, subcategory, and notes
* Record credits (income, refunds, etc.) separately
* Query expenses and credits by date range
* Compute net balance (credits - expenses)
* Edit and delete expense entries
* Generate category-wise summaries
* Expose categories as a JSON MCP resource

---

## Project Structure

```
expense-mcp/
├── __pycache__/
├── .venv/
├── .gitignore
├── .python-version
├── categories.json
├── expenses.db
├── main.py
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## Setup

### 1. Install dependencies

Using `uv` (recommended):

```
uv sync
```

Or with pip:

```
pip install fastmcp
```

---

### 2. Run the server

```
python main.py
```

On first run, the SQLite database (`expenses.db`) is initialized automatically.

---

## Using with Claude Desktop

You can install this MCP server directly into Claude Desktop.

### Install

```
uv run fastmcp install claude-desktop main.py
```

This registers the server so Claude can use it as a tool provider.

---

### After Installation

1. Open Claude Desktop
2. Go to MCP / Tools section
3. You should see `ExpenseTracker` available
4. Start querying naturally, for example:

```
Add an expense of 250 on 2026-04-23 for food
```

```
Show my expenses from 2026-04-01 to 2026-04-23
```

```
What is my net balance this month?
```

---

## MCP Tools

### add_expense

```
add_expense(date, amount, category, subcategory="", note="")
```

Adds a new expense entry.

---

### add_credit

```
add_credit(date, amount, source, subcategory="", note="")
```

Adds a credit (income).
Amount must be positive.

---

### list_expenses

```
list_expenses(start_date, end_date)
```

Returns all expenses in the given range.

---

### list_credits

```
list_credits(start_date, end_date)
```

Returns all credits in the given range.

---

### edit_expense

```
edit_expense(id, ...)
```

Updates one or more fields of an expense.

---

### delete_expense

```
delete_expense(id)
```

Deletes an expense by ID.

---

### net_balance

```
net_balance(start_date, end_date)
```

Returns:

```
{
  "total_credits": float,
  "total_expenses": float,
  "net": float
}
```

---

### summarize

```
summarize(start_date, end_date, category=None)
```

Returns aggregated expense totals grouped by category.

---

## MCP Resource

### Categories

```
expense://categories
```

Returns the contents of `categories.json`.

---

## Design Notes

* Expenses and credits are stored in separate tables
* SQLite is used for zero-config local storage
* Schema is intentionally minimal for easy extension
* Built as MCP tools for agent-based workflows

---

## Future Improvements

* Recurring transactions
* Budget tracking and alerts
* CSV export
* Multi-user support
* Tag-based filtering

---

## License

MIT License

