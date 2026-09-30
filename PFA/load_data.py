import random
from datetime import date, timedelta

from sqlalchemy import text

from db import connect

random.seed(1)

merchants = {
    "food": ["Swiggy", "Zomato", "BigBasket", "Starbucks"],
    "transport": ["Uber", "Ola", "Metro"],
    "rent": ["Landlord"],
    "shopping": ["Amazon", "Flipkart"],
    "bills": ["Airtel", "BESCOM"],
}
payment_methods = ["upi", "card", "cash"]

rows = []
start = date(2026, 7, 1)
for transaction_id in range(1, 51):
    category = random.choice(list(merchants))
    merchant = random.choice(merchants[category])
    transaction_date = start + timedelta(days=random.randint(0, 89))
    if category == "rent":
        amount = 15000
    elif category == "food":
        amount = random.randint(80, 800)
    else:
        amount = random.randint(100, 2500)
    payment_method = random.choice(payment_methods)
    rows.append(
        (transaction_id, transaction_date, merchant, category, amount, payment_method)
    )

# each transaction from tuple to dictionaty
records = [
    {
        "id": row[0],
        "date": row[1],
        "merchant": row[2],
        "category": row[3],
        "amount": row[4],
        "paymentmethod": row[5],
    }
    for row in rows
]

# conn is now your connection to PostgreSQL.
with connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS transactions"))
    conn.execute(
        text(
            """
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                merchant TEXT NOT NULL,
                category TEXT NOT NULL,
                amount NUMERIC(10, 2) NOT NULL,
                paymentmethod TEXT NOT NULL
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO transactions
                (id, date, merchant, category, amount, paymentmethod)
            VALUES (:id, :date, :merchant, :category, :amount, :paymentmethod)
            """
        ),
        records,
    )
    conn.commit()

print(f"Inserted {len(rows)} rows into transactions")

"""

But with SQLAlchemy's expression API, you can write something like:

select(transactions).where(
    transactions.c.category == "food"
)

                    SQLAlchemy
                         │
          ┌──────────────┴──────────────┐
          ↓                             ↓
     Raw SQL approach            SQLAlchemy API / ORM
          │                             │
     You write SQL              You write Python
          │                             │
          ↓                             ↓
      text("SELECT...")       select(...).where(...)
          │                             │
          └──────────────┬──────────────┘
                         ↓
                    SQLAlchemy
                         ↓
                      Psycopg
                         ↓
                    PostgreSQL
"""