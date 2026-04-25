from fastmcp import FastMCP
import os
import aiosqlite
import tempfile

TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("expensefn")


def init_db():
    import sqlite3
    with sqlite3.connect(DB_PATH) as c:
        c.execute("PRAGMA journal_mode=WAL")

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
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                source TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

        c.execute("INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')")
        c.execute("DELETE FROM expenses WHERE category = 'test'")


init_db()


@mcp.tool()
async def add_expense(date, amount, category, subcategory="", note=""):
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, category, subcategory, note)
            )
            await c.commit()
            return {"status": "ok", "id": cur.lastrowid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def add_credit(date, amount, source, subcategory="", note=""):
    if amount <= 0:
        return {"status": "error", "message": "Credit amount must be positive", "id": None}

    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                "INSERT INTO credits(date, amount, source, subcategory, note) VALUES (?,?,?,?,?)",
                (date, amount, source, subcategory, note)
            )
            await c.commit()
            return {"status": "ok", "id": cur.lastrowid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def list_credits(start_date, end_date):
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                """
                SELECT id, date, amount, source, subcategory, note
                FROM credits
                WHERE date BETWEEN ? AND ?
                ORDER BY id ASC
                """,
                (start_date, end_date)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def net_balance(start_date, end_date):
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur1 = await c.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM credits WHERE date BETWEEN ? AND ?",
                (start_date, end_date)
            )
            total_credits = (await cur1.fetchone())[0]

            cur2 = await c.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date BETWEEN ? AND ?",
                (start_date, end_date)
            )
            total_expenses = (await cur2.fetchone())[0]

        return {
            "total_credits": total_credits,
            "total_expenses": total_expenses,
            "net": total_credits - total_expenses
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def edit_expense(id, date=None, amount=None, category=None, subcategory=None, note=None):
    updates = {k: v for k, v in {
        "date": date,
        "amount": amount,
        "category": category,
        "subcategory": subcategory,
        "note": note
    }.items() if v is not None}

    if not updates:
        return {"status": "no_changes", "id": id}

    set_clause = ", ".join(f"{k}=?" for k in updates)
    params = list(updates.values()) + [id]

    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(f"UPDATE expenses SET {set_clause} WHERE id = ?", params)
            await c.commit()

            if cur.rowcount == 0:
                return {"status": "not_found", "id": id}
            return {"status": "ok", "id": id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def delete_expense(id):
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute("DELETE FROM expenses WHERE id = ?", (id,))
            await c.commit()

            if cur.rowcount == 0:
                return {"status": "not_found", "id": id}
            return {"status": "ok", "id": id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def list_expenses(start_date, end_date):
    try:
        async with aiosqlite.connect(DB_PATH) as c:
            cur = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY id ASC
                """,
                (start_date, end_date)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
async def summarize(start_date, end_date, category=None):
    try:
        async with aiosqlite.connect(DB_PATH) as c:
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

            cur = await c.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in await cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    try:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        import json
        return json.dumps({"categories": ["Food", "Transport", "Other"]}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    # mcp.run()