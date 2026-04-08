<script setup>
defineProps({
  item: { type: Object, required: true },
});

function displayTitle(item) {
  return item.title || item.name || item.guid;
}

function ownerName(item) {
  const parts = [item.owner_first_name, item.owner_last_name].filter(Boolean);
  return parts.join(' ') || item.owner_username || '';
}

function contentLink(item) {
  return item.vanity_url || item.content_url || item.dashboard_url || '#';
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

function appModeLabel(mode) {
  const labels = {
    'shiny': 'Shiny',
    'rmd-static': 'R Markdown',
    'rmd-shiny': 'R Markdown (Shiny)',
    'quarto-static': 'Quarto',
    'quarto-shiny': 'Quarto (Shiny)',
    'jupyter-static': 'Jupyter',
    'jupyter-voila': 'Voilà',
    'api': 'Plumber API',
    'python-api': 'Python API',
    'python-fastapi': 'FastAPI',
    'python-dash': 'Dash',
    'python-streamlit': 'Streamlit',
    'python-shiny': 'Shiny for Python',
    'python-bokeh': 'Bokeh',
    'python-gradio': 'Gradio',
    'python-panel': 'Panel',
    'static': 'Static',
    'tensorflow-saved-model': 'TensorFlow',
  };
  return labels[mode] || mode || 'Unknown';
}
</script>

<template>
  <div class="content-card">
    <div class="card-header">
      <a :href="contentLink(item)" target="_blank" class="card-title">
        {{ displayTitle(item) }}
      </a>
      <span v-if="item.score != null" class="card-score">
        {{ item.score }}
      </span>
    </div>

    <div v-if="item.description" class="card-desc">{{ item.description }}</div>

    <div class="card-meta">
      <span v-if="item.app_mode" class="app-mode-badge">{{ appModeLabel(item.app_mode) }}</span>

      <span v-if="ownerName(item)" class="meta-item">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
        {{ ownerName(item) }}
      </span>

      <span v-if="item.last_deployed_time" class="meta-item">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
        {{ formatDate(item.last_deployed_time) }}
      </span>
    </div>

    <div v-if="item.tags && item.tags.length" class="card-tags">
      <span v-for="tag in item.tags" :key="tag.id || tag.name" class="tag-chip">
        {{ tag.name }}
      </span>
    </div>

    <div class="card-links">
      <a v-if="item.content_url" :href="item.content_url" target="_blank" class="card-link">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          <polyline points="15 3 21 3 21 9" />
          <line x1="10" y1="14" x2="21" y2="3" />
        </svg>
        Open
      </a>
      <a v-if="item.dashboard_url" :href="item.dashboard_url" target="_blank" class="card-link">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
        Dashboard
      </a>
    </div>
  </div>
</template>
