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

    # Create a table for users if it doesn't already exist
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


from typing import List


def login_user(username: str, password: str) -> User:
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Create a table for users if it doesn't already exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")

    # Check if the user exists in the database
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user:
        # Verify the password
        if user[2] == password:
            # Create a new User object with the provided username and password
            return User(user[1], user[2])
        else:
            raise ValueError("Invalid password")
    else:
        raise ValueError("User not found")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
