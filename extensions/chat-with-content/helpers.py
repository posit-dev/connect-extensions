from datetime import datetime, timezone


def time_since_deployment(deployment_time_str):
    """
    Calculate time since deployment from ISO format datetime string.

    Args:
        deployment_time_str (str): Datetime string in format "2025-03-19T23:16:11Z"

    Returns:
        str: Human-readable time difference like "last deployed 3 hours ago"
    """
    # Parse the deployment time
    deployment_time = datetime.fromisoformat(deployment_time_str.replace("Z", "+00:00"))

    # Get current time in UTC
    current_time = datetime.now(timezone.utc)

    # Calculate the difference
    time_diff = current_time - deployment_time
    total_seconds = time_diff.total_seconds()

    # Handle future dates
    if total_seconds < 0:
        return "last deployed in the future"

    # Convert to appropriate unit
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
