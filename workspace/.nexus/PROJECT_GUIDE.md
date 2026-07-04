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
- `def create_tweet(text: str) -> Tweet:` — Implement tweet creation logic to store tweets in the database.

### src/models/user.py
- `def login_user(username: str, password: str) -> User:` — Implement user login logic to authenticate a user.

### src/views/timeline.py
- `def view_timeline() -> List[Tweet]:` — This function should retrieve the timeline of tweets from the database. It should return a list of Tweet objects, ordered by creation date.
