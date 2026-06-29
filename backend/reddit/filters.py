import re

# Standard low signal phrases to match exactly (lowercase, stripped)
LOW_SIGNAL_PHRASES = {
    "lol", "same", "this", "thanks", "following", "same here", 
    "+1", "me too", "upvoted", "bump", "agreed", "interest", "interested"
}

# Meta discussion keywords
META_PATTERNS = [
    r"what startup should i build",
    r"rate my idea",
    r"roast my saas",
    r"roast my startup",
    r"validate my idea",
    r"feedback on my startup",
    r"how to build a saas"
]

# Promotional keywords
PROMO_PATTERNS = [
    r"self-promotion",
    r"buy my product",
    r"check out my app",
    r"check out my website",
    r"use my referral link",
    r"discount code",
    r"sign up for my"
]

def should_discard_content(content: str, min_length: int = 40) -> tuple[bool, str]:
    """
    Evaluates whether the given content should be discarded according to filter rules.
    Returns (should_discard, reason_string).
    """
    if not content:
        return True, "empty content"

    cleaned = content.strip()

    # 1. Content is deleted or removed
    if cleaned in {"[deleted]", "[removed]"}:
        return True, "deleted or removed content"

    # 2. Length under threshold
    if len(cleaned) < min_length:
        return True, f"length ({len(cleaned)}) is under threshold of {min_length}"

    cleaned_lower = cleaned.lower()

    # 3. Low-signal exact/near matches
    # Remove simple punctuation at the end for matching
    stripped_punct = re.sub(r"[^\w\s]", "", cleaned_lower).strip()
    if stripped_punct in LOW_SIGNAL_PHRASES:
        return True, f"low-signal expression matching '{stripped_punct}'"

    # 4. Meta discussions
    for pattern in META_PATTERNS:
        if re.search(pattern, cleaned_lower):
            return True, f"meta discussion matching pattern '{pattern}'"

    # 5. Promotional content
    for pattern in PROMO_PATTERNS:
        if re.search(pattern, cleaned_lower):
            return True, f"promotional content matching pattern '{pattern}'"

    # 6. Basic URL spam detection (if the content is just a link)
    if re.match(r"^https?://[^\s]+$", cleaned):
        return True, "content is only a URL"

    return False, ""
