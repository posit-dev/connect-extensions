<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import * as api from './api.js';
import ContentCard from './components/ContentCard.vue';
import Settings from './components/Settings.vue';

// Route without pulling in vue-router: evaluate pathname once at mount.
// The two pages (/ and /settings) don't link to each other, so reactive
// route tracking isn't needed.
const isSettings = computed(() =>
  window.location.pathname.replace(/\/+$/, '').endsWith('/settings')
);

const query = ref('');
const results = ref([]);
const loading = ref(false);
const appModes = ref([]);
const contentCategories = ref([]);
const selectedAppMode = ref('');
const selectedCategory = ref('');
const error = ref('');
const lastRun = ref(null);
let errorTimer = null;
let debounceTimer = null;

// Indexer runs every 60s by default. Flag the index as stale only well past
// that so transient fetch hiccups don't scare users; 30 min = 30 healthy
// intervals.
const STALE_AFTER_MS = 30 * 60 * 1000;
const staleMinutes = ref(0);
const isStale = computed(() => staleMinutes.value > 0);

function updateStaleness() {
  if (!lastRun.value) {
    staleMinutes.value = 0;
    return;
  }
  const ageMs = Date.now() - new Date(lastRun.value).getTime();
  staleMinutes.value = ageMs > STALE_AFTER_MS ? Math.floor(ageMs / 60000) : 0;
}
let stalenessTimer = null;

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

async function loadLastRun() {
  try {
    const s = await api.getStatus();
    lastRun.value = s?.last_run ?? null;
    updateStaleness();
  } catch {
    // status endpoint is best-effort; don't surface this to users
  }
}

function onInput() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(doSearch, 300);
}

async function doSearch() {
  loading.value = true;
  try {
    // No `mode` — backend defaults to hybrid. Algorithm toggle lives on /settings.
    const data = await api.search(query.value.trim(), {
      appMode: selectedAppMode.value || undefined,
      contentCategory: selectedCategory.value || undefined,
    });
    results.value = data.results || [];
  } catch (e) {
    showError(`Search failed: ${e.message}`);
    results.value = [];
  } finally {
    loading.value = false;
  }
}

// "Best match" split only applies when the user typed a query and there are
// multiple results; browse mode and single results render flat.
const hasQuery = computed(() => query.value.trim().length > 0);
const showSplit = computed(() => hasQuery.value && results.value.length >= 2);
const bestMatch = computed(() => (showSplit.value ? results.value[0] : null));
const otherResults = computed(() =>
  showSplit.value ? results.value.slice(1) : results.value
);

watch([selectedAppMode, selectedCategory], () => {
  doSearch();
});

onMounted(async () => {
  if (isSettings.value) return;
  await loadFilters();
  doSearch();
  loadLastRun();
  // Re-poll periodically so the stale banner appears without a reload.
  stalenessTimer = setInterval(loadLastRun, 60_000);
});

onBeforeUnmount(() => {
  clearTimeout(debounceTimer);
  clearTimeout(errorTimer);
  clearInterval(stalenessTimer);
});
</script>

<template>
  <Settings v-if="isSettings" />
  <main v-else class="container">
    <div v-if="isStale" class="stale-banner">
      Search results may be out of date — the index has not refreshed in {{ staleMinutes }} minutes.
    </div>
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
    </div>

    <div v-if="loading" class="loading">Searching...</div>

    <div v-else-if="results.length === 0 && (hasQuery || selectedAppMode || selectedCategory)" class="muted">
      No matching content found.
    </div>

    <template v-else>
      <template v-if="showSplit">
        <div class="results-section-label">Best match</div>
        <div class="content-card-wrapper content-card--best">
          <ContentCard :item="bestMatch" />
        </div>
        <div class="results-section-label results-section-label--other">Other results</div>
        <div class="results">
          <ContentCard v-for="r in otherResults" :key="r.guid" :item="r" />
        </div>
      </template>
      <div v-else class="results">
        <ContentCard v-for="r in otherResults" :key="r.guid" :item="r" />
      </div>
    </template>
  </main>

  <Teleport to="body">
    <div v-if="error" class="error-toast-container">
      <div class="error-toast">{{ error }}</div>
    </div>
  </Teleport>
</template>
