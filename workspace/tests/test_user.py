import pytest
from src.models.user import create_user


@pytest.fixture
def user_db():
    # Setup: Create a temporary SQLite database for testing
    import sqlite3

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    # Create the users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    yield conn

    # Teardown: Close the database connection
    conn.close()


@pytest.mark.parametrize(
    "username, password",
    [
        ("testuser1", "password123"),
        ("testuser2", "securepass456"),
        ("testuser3", "anotherpassword789"),
    ],
)
def test_create_user(user_db, username, password):
    # Insert a user into the database
    cursor = user_db.cursor()
    cursor.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)", (username, password)
    )

    # Commit the transaction
    user_db.commit()

    # Retrieve the inserted user from the database
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()

    # Assertions
    assert result is not None, "User should be created successfully"
    assert result[1] == username, "Username should match the inserted value"
    assert result[2] == password, "Password should match the inserted value"
