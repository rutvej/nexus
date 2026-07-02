def get_timeline() -> list:
    # Assuming 'db' is an instance of a database connection object
    return db.get_all_tweets(order_by="created_at", order_desc=True)
