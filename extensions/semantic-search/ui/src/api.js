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

export function search(query, { limit = 20, appMode, contentCategory, mode } = {}) {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (limit) params.set('limit', limit);
  if (appMode) params.set('app_mode', appMode);
  if (contentCategory) params.set('content_category', contentCategory);
  if (mode) params.set('mode', mode);
  return request(`api/search?${params}`);
}

export function getFilters() {
  return request('api/filters');
}

export function getStatus() {
  return request('api/status');
}

export function triggerReindex() {
  return request('api/reindex', { method: 'POST' });
}
