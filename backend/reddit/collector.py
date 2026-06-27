from datetime import datetime, timezone
import praw
from backend.reddit.client import get_reddit_client

def collect_from_subreddits(
    subreddits: list[str],
    post_limit: int = 100,
    max_comment_depth: int = 3
) -> list[dict]:
    """
    Collects raw submissions and recursive comments from a list of subreddits,
    formatting each into the source-agnostic SourceDocument schema.
    """
    client = get_reddit_client()
    source_documents = []
    seen_ids = set()

    for sub_name in subreddits:
        try:
            subreddit = client.subreddit(sub_name)
            
            # Fetch from the four feeds
            feeds = [
                subreddit.hot(limit=post_limit),
                subreddit.top(limit=post_limit),
                subreddit.rising(limit=post_limit),
                subreddit.new(limit=post_limit)
            ]

            for feed in feeds:
                for submission in feed:
                    if submission.id in seen_ids:
                        continue
                    seen_ids.add(submission.id)

                    # 1. Format submission (post title + body) as SourceDocument
                    doc = {
                        "source": "reddit",
                        "source_id": f"t3_{submission.id}",
                        "title": submission.title or "",
                        "content": submission.selftext or "",
                        "author": str(submission.author) if submission.author else "[deleted]",
                        "url": f"https://reddit.com{submission.permalink}",
                        "created_at": datetime.fromtimestamp(submission.created_utc, timezone.utc),
                        "metadata": {
                            "score": submission.score,
                            "comment_count": submission.num_comments,
                            "subreddit": sub_name,
                            "permalink": submission.permalink,
                            "is_comment": False
                        }
                    }
                    source_documents.append(doc)

                    # 2. Collect comments recursively
                    try:
                        # Limit replaces MoreComments objects. limit=0 skips fetching more to speed up run
                        submission.comments.replace_more(limit=0)
                        traverse_comments(
                            comment_list=submission.comments,
                            current_depth=1,
                            max_depth=max_comment_depth,
                            subreddit_name=sub_name,
                            results=source_documents,
                            seen_ids=seen_ids
                        )
                    except Exception as e:
                        # Log error internally and continue collecting
                        print(f"Error fetching comments for submission {submission.id}: {e}")

        except Exception as e:
            print(f"Error collecting from subreddit {sub_name}: {e}")

    return source_documents

def traverse_comments(
    comment_list,
    current_depth: int,
    max_depth: int,
    subreddit_name: str,
    results: list,
    seen_ids: set
):
    """
    Recursively traverses a PRAW comment forest, converting comments to SourceDocument format.
    """
    if current_depth > max_depth:
        return

    for comment in comment_list:
        if isinstance(comment, praw.models.MoreComments):
            continue
        if comment.id in seen_ids:
            continue
        seen_ids.add(comment.id)

        doc = {
            "source": "reddit",
            "source_id": f"t1_{comment.id}",
            "title": "",
            "content": comment.body or "",
            "author": str(comment.author) if comment.author else "[deleted]",
            "url": f"https://reddit.com{comment.permalink}",
            "created_at": datetime.fromtimestamp(comment.created_utc, timezone.utc),
            "metadata": {
                "score": comment.score,
                "subreddit": subreddit_name,
                "permalink": comment.permalink,
                "parent_id": comment.parent_id,
                "is_comment": True
            }
        }
        results.append(doc)

        # Recurse if replies exist
        if hasattr(comment, "replies") and comment.replies:
            traverse_comments(
                comment_list=comment.replies,
                current_depth=current_depth + 1,
                max_depth=max_depth,
                subreddit_name=subreddit_name,
                results=results,
                seen_ids=seen_ids
            )
