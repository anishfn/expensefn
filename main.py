from fastmcp import FastMCP
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")


def init_db():
    """
    Initialize the SQLite database.

    Creates the 'expenses' and 'credits' tables if they do not already exist.
    """
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS credits(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,        -- Date of credit (YYYY-MM-DD)
                amount REAL NOT NULL,      -- Credit amount (always positive)
                source TEXT NOT NULL,      -- Where the credit came from (e.g., Salary, Refund)
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)


init_db()


@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    """
    Add a new expense entry to the database.

    Parameters:
        date (str): Date of the expense
        amount (float): Amount spent
        category (str): Expense category
        subcategory (str, optional): Subcategory for finer classification
        note (str, optional): Additional description

    Returns:
        dict: Status and the ID of the newly created expense
    """
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
def add_credit(date, amount, source, subcategory="", note=""):
    """
    Record an incoming credit (income, refund, reimbursement, etc.).

    Credits are stored separately from expenses so that net balance
    calculations (total credits - total expenses) remain clean and
    auditable without mixing debit and credit rows in one table.

    Parameters:
        date (str): Date of the credit (YYYY-MM-DD)
        amount (float): Credit amount — must be positive
        source (str): Where the credit came from (e.g., Salary, Freelance, Refund)
        subcategory (str, optional): Finer classification within the source
        note (str, optional): Additional description

    Returns:
        dict: Status, the ID of the new credit record, and a validation
              error message if the amount was not positive
    """
    if amount <= 0:
        return {"status": "error", "message": "Credit amount must be positive", "id": None}

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO credits(date, amount, source, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, source, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}


@mcp.tool()
def list_credits(start_date, end_date):
    """
    Retrieve all credit records within a given date range (inclusive).

    Parameters:
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)

    Returns:
        list[dict]: List of credit records as dictionaries
    """
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, source, subcategory, note
            FROM credits
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def net_balance(start_date, end_date):
    """
    Calculate the net balance (total credits minus total expenses) for a period.

    Parameters:
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)

    Returns:
        dict: total_credits, total_expenses, and net (positive = surplus,
              negative = deficit) for the requested date range
    """
    with sqlite3.connect(DB_PATH) as c:
        total_credits = c.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM credits WHERE date BETWEEN ? AND ?",
            (start_date, end_date)
        ).fetchone()[0]

        total_expenses = c.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date BETWEEN ? AND ?",
            (start_date, end_date)
        ).fetchone()[0]

    return {
        "total_credits": total_credits,
        "total_expenses": total_expenses,
        "net": total_credits - total_expenses
    }


@mcp.tool()
def edit_expense(id, date=None, amount=None, category=None, subcategory=None, note=None):
    """
    Update one or more fields of an existing expense by its ID.

    Parameters:
        id (int): The unique ID of the expense to edit
        date (str, optional): New date for the expense (YYYY-MM-DD)
        amount (float, optional): New amount
        category (str, optional): New category
        subcategory (str, optional): New subcategory
        note (str, optional): New note/description

    Returns:
        dict: Status ('ok', 'not_found', or 'no_changes') and the affected expense ID
    """
    fields = {"date": date, "amount": amount, "category": category,
              "subcategory": subcategory, "note": note}
    updates = {k: v for k, v in fields.items() if v is not None}

    if not updates:
        return {"status": "no_changes", "id": id}

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    params = list(updates.values()) + [id]

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(f"UPDATE expenses SET {set_clause} WHERE id = ?", params)
        if cur.rowcount == 0:
            return {"status": "not_found", "id": id}
        return {"status": "ok", "id": id}


@mcp.tool()
def delete_expense(id):
    """
    Permanently delete an expense record by its ID.

    Parameters:
        id (int): The unique ID of the expense to delete

    Returns:
        dict: Status ('ok' or 'not_found') and the affected expense ID
    """
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (id,))
        if cur.rowcount == 0:
            return {"status": "not_found", "id": id}
        return {"status": "ok", "id": id}


@mcp.tool()
def list_expenses(start_date, end_date):
    """
    Retrieve all expenses within a given date range (inclusive).

    Parameters:
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)

    Returns:
        list[dict]: List of expense records as dictionaries
    """
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def summarize(start_date, end_date, category=None):
    """
    Generate a summary of expenses grouped by category.

    Parameters:
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)
        category (str, optional): Filter for a specific category

    Returns:
        list[dict]: Aggregated totals per category
    """
    with sqlite3.connect(DB_PATH) as c:
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """
    Provide category definitions as a JSON resource.
    """
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)