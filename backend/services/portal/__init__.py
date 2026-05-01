import re

_HTML_TAG_RE = re.compile(r'<[^>]+>')


def sanitize(text: str, max_len: int = 5000) -> str:
    """Strip HTML tags and limit length for user-generated content."""
    if not text:
        return ""
    clean = _HTML_TAG_RE.sub('', text)
    return clean[:max_len].strip()
