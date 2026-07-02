import os
import pytest
from src.database import get_db
from src.models.user import create_user, login_user
from src.models.tweet import create_tweet
from src.views.timeline import get_timeline

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists("tweeter.db"):
        try:
            os.remove("tweeter.db")
        except Exception:
            pass
    import src.database
    src.database.init_db()
    yield
    if os.path.exists("tweeter.db"):
        try:
            os.remove("tweeter.db")
        except Exception:
            pass

def test_user_flow():
    # Test create user
    create_user("testuser", "testpassword")
    
    # Test login success
    assert login_user("testuser", "testpassword") is True
    
    # Test login failure
    assert login_user("testuser", "wrongpassword") is False
    assert login_user("nonexistent", "testpassword") is False

def test_tweet_flow():
    tweet_id = create_tweet("Hello from my test tweet!")
    assert isinstance(tweet_id, int)
    
    tweets = get_timeline()
    assert len(tweets) == 1
    assert tweets[0]["text"] == "Hello from my test tweet!"
