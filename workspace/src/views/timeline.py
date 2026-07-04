from src.models.tweet import Tweet

from typing import List
import sqlite3


class Tweet:
    def __init__(self, id: int, text: str, user_id: int):
        self.id = id
        self.text = text
        self.user_id = user_id


from src.models.tweet import Tweet

from typing import List
import sqlite3


class Tweet:
    def __init__(self, id: int, text: str, user_id: int):
        self.id = id
        self.text = text
        self.user_id = user_id


from src.models.tweet import Tweet

from typing import List
import sqlite3


class Tweet:
    def __init__(self, id: int, text: str, user_id: int):
        self.id = id
        self.text = text
        self.user_id = user_id


def view_timeline() -> List[Tweet]:
    conn = sqlite3.connect("tweets.db")
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            user_id INTEGER NOT NULL
        )
    """)

    # Retrieve all tweets from the database
    cursor.execute("SELECT * FROM tweets")
    tweets = [Tweet(row[0], row[1], row[2]) for row in cursor.fetchall()]

    conn.close()
    return tweets
