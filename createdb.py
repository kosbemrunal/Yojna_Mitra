import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )""")

c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                sender TEXT,
                message TEXT
            )""")

conn.commit()
conn.close()

print("Database has been created successfully!")
