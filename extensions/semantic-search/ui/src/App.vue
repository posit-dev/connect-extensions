<script setup>
import { ref, onMounted, watch } from 'vue';
import * as api from './api.js';
import ContentCard from './components/ContentCard.vue';

const query = ref('');
const results = ref([]);
const loading = ref(false);
const appModes = ref([]);
const contentCategories = ref([]);
const selectedAppMode = ref('');
const selectedCategory = ref('');
const searchMode = ref('hybrid');
const status = ref(null);
const error = ref('');
let errorTimer = null;
let debounceTimer = null;

function showError(msg) {
  error.value = msg;
  clearTimeout(errorTimer);
  errorTimer = setTimeout(() => { error.value = ''; }, 5000);
}

async function loadFilters() {
  try {
    const data = await api.getFilters();
    appModes.value = data.app_modes || [];
    contentCategories.value = data.content_categories || [];
  } catch {
    // filters unavailable — not critical
  }
}

async function loadStatus() {
  try {
    status.value = await api.getStatus();
  } catch {
    // status unavailable
  }
}

function onInput() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(doSearch, 300);
}

async function doSearch() {
  loading.value = true;
  try {
    const data = await api.search(query.value.trim(), {
      appMode: selectedAppMode.value || undefined,
      contentCategory: selectedCategory.value || undefined,
      mode: searchMode.value,
    });
    results.value = data.results || [];
  } catch (e) {
    showError(`Search failed: ${e.message}`);
    results.value = [];
  } finally {
    loading.value = false;
  }
}

async function reindex() {
  try {
    await api.triggerReindex();
    await loadStatus();
  } catch (e) {
    showError(`Re-index failed: ${e.message}`);
  }
}

watch([selectedAppMode, selectedCategory, searchMode], () => {
  doSearch();
});

onMounted(async () => {
  await loadFilters();
  await loadStatus();
  doSearch();
});
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <div class="logo">
        <svg class="logo-icon" width="22" height="22" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        Connect Semantic Search
      </div>
      <div class="header-actions">
        <span v-if="status" class="status-badge">
          {{ status.content_count }} items indexed
        </span>
        <button class="btn" @click="reindex">Re-index</button>
      </div>
    </div>
  </header>

  <main class="container">
    <div class="search-input-wrapper">
      <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35" />
      </svg>
      <input
        v-model="query"
        class="search-input"
        placeholder='Search content... e.g. "shiny dashboard", "quarterly report"'
        @input="onInput"
        @keydown.enter="doSearch"
      >
    </div>

    <div class="filters">
      <select v-model="selectedAppMode" class="filter-select">
        <option value="">All types</option>
        <option v-for="m in appModes" :key="m" :value="m">{{ m }}</option>
      </select>
      <select v-model="selectedCategory" class="filter-select">
        <option value="">All categories</option>
        <option v-for="c in contentCategories" :key="c" :value="c">{{ c }}</option>
      </select>
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

    <div v-else-if="results.length === 0 && (query.trim() || selectedAppMode || selectedCategory)" class="muted">
      No matching content found.
    </div>

    <div v-else class="results">
      <ContentCard v-for="r in results" :key="r.guid" :item="r" />
    </div>
  </main>

  <Teleport to="body">
    <div v-if="error" class="error-toast-container">
      <div class="error-toast">{{ error }}</div>
    </div>
  </Teleport>
</template>
