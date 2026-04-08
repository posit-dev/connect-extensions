const BASE = '';

async function request(url, options = {}) {
  const resp = await fetch(`${BASE}${url}`, options);
  if (!resp.ok) {
    let message = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      message = body.detail || JSON.stringify(body);
    } catch {
      // keep the status message
    }
    throw new Error(message);
  }
  return resp.json();
}

export function listTags() {
  return request('api/tags');
}

/**
 * Add a watched tag and stream indexing progress via SSE.
 * @param {string} tag - Tag name
 * @param {string} [tagId] - Connect tag UUID
 * @param {function} [onEvent] - Called with each SSE event object
 * @returns {Promise} Resolves when the stream ends
 */
export async function addTag(tag, tagId, onEvent) {
  const params = new URLSearchParams({ tag });
  if (tagId) params.set('tag_id', tagId);

  const resp = await fetch(`${BASE}api/tags?${params}`, { method: 'POST' });
  if (!resp.ok) {
    let message = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      message = body.detail || JSON.stringify(body);
    } catch { /* keep status */ }
    throw new Error(message);
  }

  if (!onEvent) return;

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Parse SSE frames from buffer.
    const lines = buffer.split('\n');
    buffer = lines.pop(); // keep incomplete line
    let currentEvent = null;
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          onEvent({ event: currentEvent, ...data });
        } catch { /* skip malformed */ }
        currentEvent = null;
      }
    }
  }
}

export function removeTag(tag) {
  return request(`api/tags/${encodeURIComponent(tag)}`, { method: 'DELETE' });
}

export function listServers(tag) {
  const qs = tag ? `?tag=${encodeURIComponent(tag)}` : '';
  return request(`api/servers${qs}`);
}

export function listServerTools(guid) {
  return request(`api/servers/${encodeURIComponent(guid)}/tools`);
}

export function searchTools(query, limit = 10) {
  return request(`api/search?query=${encodeURIComponent(query)}&limit=${limit}`);
}

export function triggerReindex() {
  return request('api/reindex', { method: 'POST' });
}

export function getMe() {
  return request('api/me');
}

export function getSettings() {
  return request('api/settings');
}

export function updateSettings(settings) {
  return request('api/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
}
