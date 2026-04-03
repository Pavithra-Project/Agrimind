import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(os.path.dirname(__file__), 'schema.sql')) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("Database initialized.")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()
