import sqlite3

XME_DB_PATH = "./data/xme/xme.db"

def connect_db():
    return sqlite3.connect(XME_DB_PATH)

def update(conn):
    cursor = conn.cursor()
    cursor.execute("""ALTER TABLE users ADD COLUMN permission INTEGER""")
    cursor.execute("""ALTER TABLE users ADD COLUMN bio TEXT""")
    cursor.execute("""ALTER TABLE users ADD COLUMN inventory TEXT""")

if __name__ == "__main__":
    conn = connect_db()
    update(conn)