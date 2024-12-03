import sqlite3

def check_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    for user in users:
        print(user)  # 사용자 ID, 사용자 이름, 비밀번호 해시
    conn.close()

check_users()
