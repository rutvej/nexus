def create_tweet(text: str) -> int:
    # Assuming 'db' is a database connection object
    db.execute("INSERT INTO tweets (text) VALUES (?)", (text,))
    return db.lastrowid  # Returns the ID of the newly inserted tweet
