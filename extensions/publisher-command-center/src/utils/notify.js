import m from "mithril";

// App-wide queue for surfacing failures to the user. Write actions (lock, rename,
// delete, stop process) call notifyError() in their .catch so a failed action is
// shown clearly to the user. Rendered by the Notifications component mounted in
// the Layout.
export const notifications = [];
let nextId = 0;

export function notifyError(message) {
  const id = nextId++;
  notifications.push({ id, message });
  m.redraw();
  // Auto-dismiss so transient failures don't pile up; the user can also close it.
  setTimeout(() => dismiss(id), 8000);
  return id;
}

// Pull the server-provided reason out of a Mithril request error so messages can
// tell the user why something failed. Mithril puts the parsed response body on
// err.response, and the API returns { detail: "..." }; fall back when it's absent.
export function reason(err, fallback = "Please try again.") {
  return (err && err.response && err.response.detail) || fallback;
}

export function dismiss(id) {
  const index = notifications.findIndex((n) => n.id === id);
  if (index !== -1) {
    notifications.splice(index, 1);
    m.redraw();
  }
}
