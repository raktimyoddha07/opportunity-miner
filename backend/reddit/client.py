import praw
from backend.config import settings

def get_reddit_client() -> praw.Reddit:
    """
    Initializes and returns a PRAW Reddit client.
    Requires at least client_id, client_secret, and user_agent.
    Can also use username/password if configured.
    """
    # Initialize Reddit instance. If credentials are missing, PRAW will raise a prawcore.exceptions.ResponseException 
    return praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT
    )
