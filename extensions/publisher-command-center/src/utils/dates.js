import { format, formatDistanceToNow, parseISO, isValid } from "date-fns";

// Connect returns ISO strings, and sometimes null (e.g. content that was never
// deployed). date-fns throws on null or invalid input, so normalize first and
// fall back to a placeholder instead of crashing the whole view.
function toDate(value) {
  if (value == null) return null;
  const date = typeof value === "string" ? parseISO(value) : new Date(value);
  return isValid(date) ? date : null;
}

export function formatDate(value, pattern, fallback = "Unknown") {
  const date = toDate(value);
  return date ? format(date, pattern) : fallback;
}

export function formatRelative(value, fallback = "unknown") {
  const date = toDate(value);
  return date ? formatDistanceToNow(date, { addSuffix: true }) : fallback;
}
