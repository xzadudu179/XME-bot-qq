import sqlite3

XME_DB_PATH = "./data/xme/xme.db"

def connect_db():
    return sqlite3.connect(XME_DB_PATH)

def check_users(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    column_names = [description[0] for description in cursor.description]
    print(column_names)
    return cursor.fetchall()

if __name__ == "__main__":
    conn = connect_db()
    print('\n'.join([str(i) for i in check_users(conn)]))
    # print(check_users(conn))