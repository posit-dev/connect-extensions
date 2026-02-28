"""Message response generation."""


def generate_response(message: str, context: list[dict] | None = None) -> str:
    """Generate a response to a user message.

    Args:
        message: The user's message text.
        context: Optional conversation history (for future use).

    Returns:
        The response text.
    """
    return _get_last_word_question(message)


def _get_last_word_question(text: str) -> str:
    """Extract the last word and return it as a question."""
    words = text.strip().rstrip("?!.,").split()
    if words:
        return f"{words[-1].capitalize()}?"
    return "Hmm?"
