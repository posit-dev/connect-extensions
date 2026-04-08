<script setup>
import { ref, inject } from 'vue';
import * as api from '../api.js';

const showError = inject('showError');

const query = ref('');
const results = ref([]);
const loading = ref(false);
const expandedSchemas = ref(new Set());

let debounceTimer = null;

function onInput() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(search, 300);
}

async function search() {
  const q = query.value.trim();
  if (!q) {
    results.value = [];
    return;
  }
  loading.value = true;
  try {
    const data = await api.searchTools(q);
    results.value = data.results || [];
  } catch (e) {
    showError(`Search failed: ${e.message}`);
    results.value = [];
  } finally {
    loading.value = false;
  }
}

function toggleSchema(key) {
  if (expandedSchemas.value.has(key)) {
    expandedSchemas.value.delete(key);
  } else {
    expandedSchemas.value.add(key);
  }
}

function formatSchema(raw) {
  if (!raw || raw === 'null') return null;
  try {
    const obj = typeof raw === 'string' ? JSON.parse(raw) : raw;
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(raw);
  }
}
</script>

<template>
  <section class="section">
    <div class="search-input-wrapper">
      <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35" />
      </svg>
      <input
        v-model="query"
        class="search-input"
        placeholder='Search tools... e.g. "run SQL queries", "send email"'
        @input="onInput"
        @keydown.enter="search"
      >
    </div>

    <div v-if="loading" class="loading">Searching...</div>

    <div v-else-if="query.trim() && results.length === 0 && !loading" class="muted">
      No matching tools found.
    </div>

    <div v-else class="search-results">
      <div v-for="r in results" :key="`${r.server_guid}:${r.tool_name}`" class="search-tool-card">
        <div class="search-tool-header">
          <span class="health-dot" :class="r.server_healthy ? 'healthy' : 'unhealthy'" />
          <span class="tool-name">{{ r.tool_name }}</span>
          <span v-if="r.score != null" class="search-tool-score">
            score: {{ Number(r.score).toFixed(3) }}
          </span>
        </div>
        <div class="search-tool-server">{{ r.server_name || r.server_guid }}</div>
        <div v-if="r.description" class="tool-desc">{{ r.description }}</div>
        <template v-if="formatSchema(r.input_schema)">
          <button
            class="schema-toggle"
            @click="toggleSchema(`${r.server_guid}:${r.tool_name}`)"
          >
            {{ expandedSchemas.has(`${r.server_guid}:${r.tool_name}`) ? 'Hide' : 'Show' }} input schema
          </button>
          <pre
            v-if="expandedSchemas.has(`${r.server_guid}:${r.tool_name}`)"
            class="tool-schema"
          >{{ formatSchema(r.input_schema) }}</pre>
        </template>
      </div>
    </div>
  </section>
</template>
