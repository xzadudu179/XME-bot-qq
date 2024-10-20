import sqlite3

XME_DB_PATH = "./data/xme/xme.db"

def connect_db():
    return sqlite3.connect(XME_DB_PATH)

def check_users(conn):
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE users ADD COLUMN items TEXT")

if __name__ == "__main__":
    conn = connect_db()
    check_users(conn)