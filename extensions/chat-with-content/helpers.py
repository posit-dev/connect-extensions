from datetime import datetime, timezone

# Static/rendered content the app can extract text from. Interactive apps (Shiny,
# Streamlit, ...) render in the browser, so their HTML holds no content to chat with.
CHATTABLE_APP_MODES = ("jupyter-static", "quarto-static", "rmd-static", "static")

# Upper bound on the markdown handed to the LLM. A large report can produce a DOM
# far bigger than the model's context window; truncating keeps the request within
# bounds instead of erroring, at the cost of dropping the tail of very long pages.
MAX_CONTEXT_CHARS = 100_000


def time_since_deployment(deployment_time_str):
    """
    Human-readable time since deployment, e.g. "last deployed 3 hours ago".

    Args:
        deployment_time_str: ISO datetime string like "2025-03-19T23:16:11Z",
            or None/empty when Connect has no deployment time for the content.

    Returns:
        str: The phrase, or "" when no deployment time is available.
    """
    # Content that has never been deployed reports no time; skip the label rather
    # than crash on a None passed to fromisoformat().
    if not deployment_time_str:
        return ""

    try:
        deployment_time = datetime.fromisoformat(
            deployment_time_str.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        # A malformed timestamp shouldn't crash the whole content list; just omit
        # the "last deployed" phrase for this one item.
        return ""
    current_time = datetime.now(timezone.utc)

    time_diff = current_time - deployment_time
    total_seconds = time_diff.total_seconds()

    # Handle clock skew where the deployment time is slightly in the future
    if total_seconds < 0:
        return "last deployed in the future"

    if total_seconds < 60:
        value = int(total_seconds)
        unit = "second" if value == 1 else "seconds"
    elif total_seconds < 3600:  # Less than 1 hour
        value = int(total_seconds // 60)
        unit = "minute" if value == 1 else "minutes"
    elif total_seconds < 86400:  # Less than 1 day
        value = int(total_seconds // 3600)
        unit = "hour" if value == 1 else "hours"
    elif total_seconds < 604800:  # Less than 1 week
        value = int(total_seconds // 86400)
        unit = "day" if value == 1 else "days"
    elif total_seconds < 2629746:  # Less than 1 month (avg 30.44 days)
        value = int(total_seconds // 604800)
        unit = "week" if value == 1 else "weeks"
    elif total_seconds < 31556952:  # Less than 1 year (365.24 days)
        value = int(total_seconds // 2629746)
        unit = "month" if value == 1 else "months"
    else:
        value = int(total_seconds // 31556952)
        unit = "year" if value == 1 else "years"

    return f"last deployed {value} {unit} ago"


def is_chattable_content(item):
    """Whether a Connect content item exposes static text the app can chat with."""
    return (
        item.app_mode in CHATTABLE_APP_MODES
        and item.app_role != "none"
        and item.content_category != "pin"
    )


def content_choice_label(item):
    """Dropdown label for a content item, tolerating a missing title or owner."""
    title = item.title or item.name or item.guid
    owner = getattr(item, "owner", None)
    name = ""
    if owner is not None:
        name = f"{owner.first_name or ''} {owner.last_name or ''}".strip()
    deployed = time_since_deployment(item.last_deployed_time)

    # Join only the parts we actually have so the label never shows " -  ".
    suffix = " ".join(part for part in (name, deployed) if part)
    return f"{title} - {suffix}" if suffix else title


def truncate_for_context(markdown, max_chars=MAX_CONTEXT_CHARS):
    """Cap the content markdown so a large page can't overflow the model context."""
    if len(markdown) <= max_chars:
        return markdown
    return (
        markdown[:max_chars]
        + "\n\n[Content truncated because it exceeds the size this app sends to the model.]"
    )
