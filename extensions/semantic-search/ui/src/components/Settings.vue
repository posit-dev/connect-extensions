<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue';
import * as api from '../api.js';
import ContentCard from './ContentCard.vue';

const status = ref(null);
const query = ref('');
const results = ref([]);
const loading = ref(false);
const searchMode = ref('hybrid');
const error = ref('');
// pending covers the window between clicking Re-index and the backend
// actually flipping status.running — /api/reindex returns immediately.
const pending = ref(false);
let errorTimer = null;
let debounceTimer = null;
let statusPollTimer = null;

function showError(msg) {
  error.value = msg;
  clearTimeout(errorTimer);
  errorTimer = setTimeout(() => { error.value = ''; }, 5000);
}

async function loadStatus() {
  try {
    status.value = await api.getStatus();
  } catch (e) {
    showError(`Status failed: ${e.message}`);
    return;
  }
  if (status.value?.running) {
    // Keep polling until the cycle finishes so the button stays disabled.
    clearTimeout(statusPollTimer);
    statusPollTimer = setTimeout(loadStatus, 2000);
  } else {
    pending.value = false;
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function onInput() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(doSearch, 300);
}

async function doSearch() {
  loading.value = true;
  try {
    const data = await api.search(query.value.trim(), { mode: searchMode.value });
    results.value = data.results || [];
  } catch (e) {
    showError(`Search failed: ${e.message}`);
    results.value = [];
  } finally {
    loading.value = false;
  }
}

async function reindex() {
  pending.value = true;
  try {
    await api.triggerReindex();
  } catch (e) {
    pending.value = false;
    showError(`Re-index failed: ${e.message}`);
    return;
  }
  await loadStatus();
}

watch(searchMode, doSearch);

onMounted(loadStatus);
onBeforeUnmount(() => {
  clearTimeout(debounceTimer);
  clearTimeout(errorTimer);
  clearTimeout(statusPollTimer);
});
</script>

<template>
  <main class="container settings">
    <h1 class="settings-title">Semantic Search — Settings</h1>

    <section class="settings-section">
      <div class="settings-section-header">
        <h2>Indexer status</h2>
        <button
          class="btn"
          :disabled="pending || (status && status.running)"
          @click="reindex"
        >
          {{ pending || (status && status.running) ? 'Re-indexing…' : 'Re-index now' }}
        </button>
      </div>
      <dl v-if="status" class="settings-kv">
        <dt>Items indexed</dt><dd>{{ status.content_count ?? '—' }}</dd>
        <dt>Last run</dt><dd>{{ formatDate(status.last_run) }}</dd>
        <dt>Running</dt><dd>{{ status.running ? 'yes' : 'no' }}</dd>
        <dt>Interval (s)</dt><dd>{{ status.interval_seconds ?? '—' }}</dd>
      </dl>
      <p v-else class="muted">Loading status…</p>
      <details v-if="status && status.last_result" class="settings-details">
        <summary>last_result</summary>
        <pre class="settings-pre">{{ JSON.stringify(status.last_result, null, 2) }}</pre>
      </details>
    </section>

    <section class="settings-section">
      <h2>Search (A/B algorithms)</h2>
      <div class="search-input-wrapper">
        <input
          v-model="query"
          class="search-input"
          placeholder="Query…"
          @input="onInput"
          @keydown.enter="doSearch"
        >
      </div>
      <div class="filters">
        <div class="mode-toggle">
          <label class="mode-option" :class="{ active: searchMode === 'hybrid' }">
            <input type="radio" v-model="searchMode" value="hybrid"> Hybrid
          </label>
          <label class="mode-option" :class="{ active: searchMode === 'vector' }">
            <input type="radio" v-model="searchMode" value="vector"> Vector
          </label>
          <label class="mode-option" :class="{ active: searchMode === 'fts' }">
            <input type="radio" v-model="searchMode" value="fts"> FTS5
          </label>
        </div>
      </div>

      <div v-if="loading" class="loading">Searching...</div>
      <div v-else-if="results.length === 0 && query.trim()" class="muted">
        No matching content.
      </div>
      <div v-else class="results">
        <ContentCard
          v-for="r in results"
          :key="r.guid"
          :item="r"
          :show-score="true"
        />
      </div>
    </section>
  </main>

  <Teleport to="body">
    <div v-if="error" class="error-toast-container">
      <div class="error-toast">{{ error }}</div>
    </div>
  </Teleport>
</template>
