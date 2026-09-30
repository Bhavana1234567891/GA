import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

load_dotenv()

"""
This tells SQLAlchemy:

"I want to connect to a PostgreSQL database, and use Psycopg as the driver."

So SQLAlchemy knows:

PostgreSQL database + Psycopg driver.

"""

url = URL.create(
    "postgresql+psycopg",
    username=os.environ.get("PGUSER", "postgres"),
    password=os.environ["PGPASSWORD"],
    host=os.environ.get("PGHOST", "localhost"),
    port=int(os.environ.get("PGPORT", "5432")),
    database=os.environ.get("PGDATABASE", "postgres"),
)

# The Engine is SQLAlchemy's main entry point for communicating with the database.
# engine is not the same thing as an actual database connection.
# It is more like a connection manager/factory.

engine = create_engine(url)

# conn = connect()
# SQLAlchemy obtains a database connection for you.

def connect():
    return engine.connect()
