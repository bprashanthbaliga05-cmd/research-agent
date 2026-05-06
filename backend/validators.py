import re

MAX_LENGTH = 200
MIN_LENGTH = 3
MIN_WORDS = 2

# Patterns that suggest prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"you are now",
    r"forget you are",
    r"act as",
    r"jailbreak",
    r"prompt injection",
    r"system prompt",
    r"<script",
    r"javascript:",
    r"eval\(",
    r"__import__",
]

def validate_topic(topic: str) -> tuple[bool, str]:
    # Check empty
    if not topic or not topic.strip():
        return False, "Topic cannot be empty"

    topic = topic.strip()

    # Check minimum length
    if len(topic) < MIN_LENGTH:
        return False, f"Topic too short — minimum {MIN_LENGTH} characters"

    # Check maximum length
    if len(topic) > MAX_LENGTH:
        return False, f"Topic too long — maximum {MAX_LENGTH} characters (yours: {len(topic)})"

    # Check minimum words
    words = topic.split()
    if len(words) < MIN_WORDS:
        return False, f"Please be more specific — at least {MIN_WORDS} words required"

    # Check for prompt injection patterns
    topic_lower = topic.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, topic_lower):
            return False, "Invalid topic — please enter a genuine research topic"

    # Check for excessive special characters (spam signal)
    special_chars = re.findall(r'[^a-zA-Z0-9\s\-\.,?]', topic)
    if len(special_chars) > 10:
        return False, "Topic contains too many special characters"

    # Check for ALL CAPS (spam signal)
    if topic.isupper() and len(topic) > 10:
        return False, "Please don't use all capitals"

    return True, ""