import sqlite3


from datetime import datetime

import sqlite3


class Tweet:
    def __init__(self, text):
        self.text = text
        self.created_at = datetime.now()


def create_tweet(text: str) -> Tweet:
    # Connect to the SQLite database (or create it if it doesn't exist)
    conn = sqlite3.connect("tweets.db")
    cursor = conn.cursor()

    # Create a table for tweets if it doesn't exist
    cursor.execute("""CREATE TABLE IF NOT EXISTS tweets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Insert the new tweet into the database
    cursor.execute("INSERT INTO tweets (text) VALUES (?)", (text,))
    conn.commit()

    # Retrieve the newly created tweet from the database
    cursor.execute("SELECT * FROM tweets WHERE text = ?", (text,))
    tweet_data = cursor.fetchone()

    # Create a new Tweet object and return it
    tweet = Tweet(tweet_data[1])
    tweet.id = tweet_data[0]

    # Close the database connection
    conn.close()

    return tweet
