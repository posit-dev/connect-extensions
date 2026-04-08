<script setup>
import { ref, inject, watch, onMounted, onUnmounted } from 'vue';
import * as api from '../api.js';

const showError = inject('showError');
const reloadKey = inject('reloadKey');

const servers = ref([]);
const expanded = ref(new Set());
const toolsCache = ref({});  // guid → tools[]
const loadingTools = ref(new Set());
const expandedSchemas = ref(new Set());
const newServers = ref(new Set());  // GUIDs that just appeared

async function load() {
  try {
    const prevGuids = new Set(servers.value.map((s) => s.guid));
    const data = await api.listServers();
    const incoming = data.servers || [];
    servers.value = incoming;

    // Identify newly appeared servers.
    const fresh = incoming
      .map((s) => s.guid)
      .filter((g) => prevGuids.size > 0 && !prevGuids.has(g));

    if (fresh.length > 0) {
      newServers.value = new Set(fresh);
      // Remove the flash class after the animation completes.
      setTimeout(() => { newServers.value = new Set(); }, 1500);
    }
  } catch (e) {
    showError(`Failed to load servers: ${e.message}`);
  }
}

async function toggle(guid) {
  if (expanded.value.has(guid)) {
    expanded.value.delete(guid);
    return;
  }

  expanded.value.add(guid);

  if (!toolsCache.value[guid]) {
    loadingTools.value.add(guid);
    try {
      const data = await api.listServerTools(guid);
      toolsCache.value[guid] = data.tools || [];
    } catch (e) {
      showError(`Failed to load tools: ${e.message}`);
      toolsCache.value[guid] = [];
    } finally {
      loadingTools.value.delete(guid);
    }
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

function timeAgo(iso) {
  if (!iso) return '';
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

let pollTimer = null;

onMounted(() => {
  load();
  // Poll server list every 15s to pick up health check / indexing changes.
  pollTimer = setInterval(load, 15000);
});

onUnmounted(() => {
  clearInterval(pollTimer);
});

watch(reloadKey, () => {
  toolsCache.value = {};
  load();
});
</script>

<template>
  <section class="section">
    <div class="section-header">
      <h2 class="section-title">Discovered servers</h2>
      <span class="badge">{{ servers.length }}</span>
    </div>

    <div v-if="servers.length === 0" class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.5" opacity="0.3">
        <rect x="2" y="3" width="20" height="18" rx="2" />
        <path d="M8 12h8M8 8h8M8 16h4" />
      </svg>
      <p>No servers discovered yet. Add a watched tag above.</p>
    </div>

    <div v-else class="server-list">
      <div
        v-for="s in servers"
        :key="s.guid"
        class="server-card"
        :class="{ 'server-flash': newServers.has(s.guid) }"
      >
        <div class="server-header" @click="toggle(s.guid)">
          <span class="server-expand" :class="{ open: expanded.has(s.guid) }">&#9654;</span>
          <span class="health-dot" :class="s.healthy ? 'healthy' : 'unhealthy'"
                :title="s.healthy ? 'Healthy' : 'Unhealthy'" />
          <span class="server-name" :title="s.name">{{ s.name || s.guid }}</span>
          <span class="server-meta">
            <span class="tool-count-badge">{{ s.tool_count || 0 }} tools</span>
            <span v-if="s.last_health_check" :title="s.last_health_check">
              {{ timeAgo(s.last_health_check) }}
            </span>
          </span>
        </div>

        <div v-if="expanded.has(s.guid)">
          <div v-if="loadingTools.has(s.guid)" class="loading">Loading tools...</div>

          <template v-else-if="toolsCache[s.guid]">
            <div v-if="toolsCache[s.guid].length === 0" class="tool-item muted">
              No tools registered.
            </div>
            <div v-for="t in toolsCache[s.guid]" :key="t.doc_id" class="tool-item">
              <div class="tool-name">{{ t.tool_name }}</div>
              <div v-if="t.description" class="tool-desc">{{ t.description }}</div>
              <template v-if="formatSchema(t.input_schema)">
                <button class="schema-toggle" @click="toggleSchema(t.doc_id)">
                  {{ expandedSchemas.has(t.doc_id) ? 'Hide' : 'Show' }} input schema
                </button>
                <pre v-if="expandedSchemas.has(t.doc_id)" class="tool-schema">{{ formatSchema(t.input_schema) }}</pre>
              </template>
            </div>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.server-flash {
  animation: flashGreen 1.5s ease-out;
}

@keyframes flashGreen {
  0% {
    background-color: rgba(52, 168, 83, 0.15);
    box-shadow: 0 0 0 2px rgba(52, 168, 83, 0.25);
  }
  100% {
    background-color: transparent;
    box-shadow: none;
  }
}
</style>
