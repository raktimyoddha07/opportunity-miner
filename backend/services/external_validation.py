"""
External validation service (extralogic Upgrade 5).

Runs after internal validation passes. Checks three free public signals:
  A. Google Trends via pytrends (interest over 12 months, rising detection)
  B. Hacker News via Algolia API (free, no auth required)
  C. Product Hunt via search scrape (competition level)

Returns an external_signals dict to be stored on the Opportunity row.
"""
from __future__ import annotations

import time
import requests


# ---------------------------------------------------------------------------
# Signal A: Google Trends
# ---------------------------------------------------------------------------

def check_google_trends(keyword: str) -> dict:
    """
    Query Google Trends for the keyword over the past 12 months.
    Returns: { avg_interest, is_rising, trend_data }
    """
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
        pt.build_payload([keyword], timeframe="today 12-m")
        df = pt.interest_over_time()
        if df is None or df.empty or keyword not in df.columns:
            return {"avg_interest": 0, "is_rising": False, "available": False}

        series = df[keyword]
        avg_interest = float(series.mean())

        # "Rising" = last 3 months average > overall average
        recent = series.iloc[-13:]  # ~3 months of weekly data
        is_rising = float(recent.mean()) > avg_interest * 1.1

        return {
            "avg_interest": round(avg_interest, 1),
            "is_rising": is_rising,
            "available": True,
        }
    except Exception as e:
        print(f"[external_validation] Google Trends failed for '{keyword}': {e}")
        return {"avg_interest": 0, "is_rising": False, "available": False}


# ---------------------------------------------------------------------------
# Signal B: Hacker News (Algolia API — free, no auth)
# ---------------------------------------------------------------------------

def check_hacker_news(keyword: str) -> dict:
    """
    Query HN Algolia search API for comments mentioning the keyword.
    Returns: { hn_mentions }
    """
    try:
        url = "https://hn.algolia.com/api/v1/search"
        params = {"query": keyword, "tags": "comment", "hitsPerPage": 50}
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return {"hn_mentions": data.get("nbHits", 0), "available": True}
    except Exception as e:
        print(f"[external_validation] HN Algolia failed for '{keyword}': {e}")
    return {"hn_mentions": 0, "available": False}


# ---------------------------------------------------------------------------
# Signal C: Product Hunt (public search)
# ---------------------------------------------------------------------------

def check_product_hunt(keyword: str) -> dict:
    """
    Query Product Hunt search to count existing products in this space.
    Returns: { product_count, competition_label }
    """
    try:
        url = "https://www.producthunt.com/search"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html",
        }
        resp = requests.get(
            url, params={"q": keyword}, headers=headers, timeout=10
        )
        # Count product cards by looking for a common HTML pattern
        html = resp.text
        count = html.count('data-test="post-item"')
        if count == 0:
            # Fallback: count product links
            count = html.count("/posts/")
            count = min(count // 3, 50)  # rough de-dup

        if count == 0:
            label = "untapped"
        elif count <= 5:
            label = "low_competition"
        elif count <= 15:
            label = "moderate_competition"
        else:
            label = "competitive"

        return {"product_count": count, "competition_label": label, "available": True}
    except Exception as e:
        print(f"[external_validation] Product Hunt failed for '{keyword}': {e}")
    return {"product_count": 0, "competition_label": "unknown", "available": False}


# ---------------------------------------------------------------------------
# Combined external confidence score
# ---------------------------------------------------------------------------

def compute_external_confidence(
    internal_confidence: int,
    trends: dict,
    hn: dict,
    ph: dict,
) -> int:
    """
    Compute combined confidence using internal + external signals.

    Formula (from extralogic.md):
      confidence = internal
                 + 2 if google_trends_rising
                 + 1 if hn_mentions > 5
                 + 3 if product_hunt_count == 0
                 - 1 if product_hunt_count > 10
    """
    score = internal_confidence
    if trends.get("is_rising"):
        score += 2
    if hn.get("hn_mentions", 0) > 5:
        score += 1
    ph_count = ph.get("product_count", 0)
    if ph_count == 0:
        score += 3
    elif ph_count > 10:
        score -= 1
    return max(0, min(score, 100))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_external_validation(topic: str, internal_confidence: int) -> dict:
    """
    Run all three external signals for a given topic keyword.
    Sleeps 1 second between external calls to be respectful of rate limits.

    Returns a dict suitable for JSON storage on the Opportunity row.
    """
    # Truncate to core topic (first 3 words) to improve Trends/HN match quality
    core_topic = " ".join(topic.split()[:4])

    trends = check_google_trends(core_topic)
    time.sleep(1)
    hn = check_hacker_news(core_topic)
    time.sleep(1)
    ph = check_product_hunt(core_topic)

    external_confidence = compute_external_confidence(internal_confidence, trends, hn, ph)

    return {
        "topic": core_topic,
        "google_trends": trends,
        "hacker_news": hn,
        "product_hunt": ph,
        "external_confidence": external_confidence,
    }
