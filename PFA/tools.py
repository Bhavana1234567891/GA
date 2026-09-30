from langchain_core.tools import tool
from sqlalchemy import Integer, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY

from db import connect


def as_transaction(row):
    return {
        "id": row[0],
        "date": str(row[1]),
        "merchant": row[2],
        "category": row[3],
        "amount": float(row[4]),
        "paymentmethod": row[5],
    }


@tool
def get_transactions() -> list:
    """Return every row from the transactions table."""
    with connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, date, merchant, category, amount, paymentmethod
                FROM transactions
                ORDER BY id
                """
            )
        ).fetchall()
        return [as_transaction(row) for row in rows]


@tool
def filter_transactions(
    category: str = "",
    merchant: str = "",
    paymentmethod: str = "",
    start_date: str = "",
    end_date: str = "",
    min_amount: float = 0,
    max_amount: float = 0,
) -> list:
    """Return transactions using only the filters that are provided.

    category must be a name returned by get_categories, such as food.
    merchant is a shop name, such as Amazon or Zomato.
    paymentmethod is upi, card, or cash.
    start_date and end_date use YYYY-MM-DD.
    min_amount keeps amounts greater than or equal to that number.
    max_amount keeps amounts less than or equal to that number.
    Pass an empty string, or 0 for an amount, to skip that filter.
    Use one filter or several. Do not fill a filter the user did not mention.
    """
    query = """
        SELECT id, date, merchant, category, amount, paymentmethod
        FROM transactions
        WHERE 1 = 1
    """
    values = {}
    if category:
        query += " AND category = :category"
        values["category"] = category
    if merchant:
        query += " AND merchant ILIKE :merchant"
        values["merchant"] = merchant
    if paymentmethod:
        query += " AND paymentmethod = :paymentmethod"
        values["paymentmethod"] = paymentmethod
    if start_date:
        query += " AND date >= :start_date"
        values["start_date"] = start_date
    if end_date:
        query += " AND date <= :end_date"
        values["end_date"] = end_date
    if min_amount:
        query += " AND amount >= :min_amount"
        values["min_amount"] = min_amount
    if max_amount:
        query += " AND amount <= :max_amount"
        values["max_amount"] = max_amount
    query += " ORDER BY id"

    with connect() as conn:
        rows = conn.execute(text(query), values).fetchall()
        return [as_transaction(row) for row in rows]


@tool
def calculate_total(transaction_ids: list[int]) -> float:
    """Add up the amount column for the given transaction ids."""
    statement = text(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE id = ANY(:transaction_ids)
        """
    ).bindparams(bindparam("transaction_ids", type_=ARRAY(Integer)))
    with connect() as conn:
        total = conn.execute(statement, {"transaction_ids": transaction_ids}).scalar()
        return float(total)


@tool
def get_categories() -> list:
    """Return the distinct category values stored in the transactions table."""
    with connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT category
                FROM transactions
                ORDER BY category
                """
            )
        ).fetchall()
        return [row[0] for row in rows]


"""
The model does not receive the list of merchants or categories from the database. It fills filter_transactions from the words in the user's question and from the tool description.

If you ask "How much did I spend on food?", the model copies food into category because you wrote that word. The description in tools.py also gives food as an example, so that name is easy for it to repeat. It never saw the rows Swiggy, Zomato, or BigBasket before the tool ran.


category is an exact category name, such as food.
start_date and end_date use YYYY-MM-DD.
Pass an empty string for any filter you want to skip.
When the name is unclear, the model can look it up first. get_categories reads the real category names from the table and sends them back. The next tool call can then use one of those names. The system prompt tells it to do that only when the category is unclear. There is no matching tool for merchants, so a merchant name has to come from your question, or from calling get_transactions and reading the rows.

If the model guesses a name that is not in the table, the query still runs. It returns no rows. The database does not correct the guess.


| Syntax              | Meaning                                |
| ------------------- | -------------------------------------- |
| `text(sql)`         | Tell SQLAlchemy this string is raw SQL |
| `conn.execute(...)` | Execute the SQL                        |
| `values`            | Values for named SQL parameters        |
| `.fetchall()`       | Get **all rows** returned              |
| `.scalar()`         | Get **one value**                      |
| `ORDER BY id`       | Sort results by `id`                   |
| `DESC`              | Highest → lowest                       |
| `ASC`               | Lowest → highest                       |
| `ARRAY(Integer)`    | Array/list of integers                 |
| `bindparam()`       | Define/configure a named SQL parameter |
| `type_=`            | Specify the parameter's data type      |
| `:category`         | Named SQL parameter                    |
| `:transaction_ids`  | Named SQL parameter                    |


bindparam()
     ↓
defines parameter + its type

execute()
     ↓
provides parameter + its value


"""
