import sqlite3


import sqlite3


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password


from src.models.user import User

import sqlite3


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password


from typing import List


import sqlite3
from src.models.user import User

from typing import List


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password


def create_user(username: str, password: str) -> User:
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


import sqlite3
from src.models.user import User

from typing import List


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password


from typing import List


import sqlite3
from src.models.user import User

from typing import List


class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password


def login_user(username: str, password: str) -> User:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Create a table for users if it doesn't already exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user:
        if user[2] == password:
            return User(user[1], user[2])
        else:
            raise ValueError("Invalid password")
    else:
        raise ValueError("User not found")

    conn.commit()
    conn.close()


def create_user(username: str, password: str) -> User:
    from src.models.user import User
