# Nexus Project Guide

## 1. Technology Stack
- Language: Python 3.12
- Database: SQLite
- Framework: Flask

## 2. Directory Structure
- src/: Core implementation files
- tests/: Unit and integration tests

## 3. Active Schemas
None yet.

## 4. Architectural Conventions
- All database operations must utilize the sqlite3 context manager.

## Interface Registry

### src/models/tweet.py
- `def create_tweet(text: str) -> int:` — This function should add a new tweet to the database.

### src/models/user.py
- `def login_user(username: str, password: str) -> bool:` — This function should authenticate a user and return True if successful.
- `def create_user(username: str, password: str) -> bool:` — This function should authenticate a user and return True if successful.

### src/views/timeline.py
- `def get_timeline() -> list:` — This function should retrieve all tweets from the database in descending order of creation time.
