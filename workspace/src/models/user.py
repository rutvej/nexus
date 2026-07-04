import sqlite3


import sqlite3


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password


def create_user(username: str, password: str) -> User:
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Create a table for users if it doesn't exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")

    # Insert the new user into the database
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)", (username, password)
    )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Create a new User object with the provided username and password
    return User(username, password)


def login_user(username: str, password: str) -> User:
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Create a table for users if it doesn't exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")

    # Retrieve the user from the database by username and password
    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?", (username, password)
    )
    user_data = cursor.fetchone()

    if user_data:
        # Create a new User object with the retrieved data
        return User(user_data[1], user_data[2])
    else:
        # Return None if the user is not found
        return None

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
