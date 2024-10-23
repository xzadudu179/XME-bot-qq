import sqlite3
XME_DB_PATH = "./data/xme/xme.db"

def connect_db():
    return sqlite3.connect(XME_DB_PATH)

def execute(conn, param):
    cursor = conn.cursor()
    cursor.execute(param)
    column_names = [cursor.description]
    print(column_names)
    return cursor.fetchall()

if __name__ == "__main__":
    conn = connect_db()
    print('\n'.join([str(i) for i in execute(conn, "SELECT * FROM user")]))

    # fac = Faction(1, 'Test', '啊娃娃大味道', db)
    # db.add_faction_info()
    # print(check_users(conn))
    # cursor = conn.cursor()
    # cursor.execute("DELETE FROM users WHERE id = 2197504382")
    # conn.commit()

    # # 关闭连接
    # conn.close()