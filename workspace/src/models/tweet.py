import sqlite3


import sqlite3


class Tweet:
    def __init__(self, text):
        self.text = text


def create_tweet(text: str) -> Tweet:
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("tweets.db")
    cursor = conn.cursor()

    # Create a table for tweets if it doesn't exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS tweets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL
    )""")

    # Insert the new tweet into the database
    cursor.execute("INSERT INTO tweets (text) VALUES (?)", (text,))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # Create a new Tweet object with the provided text
    return Tweet(text)
