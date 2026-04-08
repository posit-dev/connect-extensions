<script setup>
import { ref, computed, inject, watch, onMounted, onUnmounted } from 'vue';
import * as api from '../api.js';

const showError = inject('showError');
const reloadKey = inject('reloadKey');
const triggerReload = inject('triggerReload');
const canEdit = inject('canEdit');

const tags = ref([]);           // watched tags: [{tag, tag_id}]
const available = ref([]);      // Connect tags: [{id, name, parent_id, ...}]
const search = ref('');
const indexingTags = ref(new Set());
const pickerOpen = ref(false);
const wrapperRef = ref(null);

// Build a map of tag id → full display path (e.g. "Category / mcp-server")
const tagPathMap = computed(() => {
  const byId = {};
  for (const t of available.value) {
    byId[t.id] = t;
  }
  const paths = {};
  for (const t of available.value) {
    const parts = [];
    let cur = t;
    while (cur) {
      parts.unshift(cur.name);
      cur = cur.parent_id ? byId[cur.parent_id] : null;
    }
    paths[t.id] = parts.join(' / ');
  }
  return paths;
});

// Watched tag IDs for quick lookup
const watchedIds = computed(() => new Set(tags.value.map((t) => t.tag_id).filter(Boolean)));
const watchedNames = computed(() => new Set(tags.value.map((t) => t.tag)));

// Filter available tags by search
const filteredTags = computed(() => {
  const q = search.value.toLowerCase().trim();
  return available.value.filter((t) => {
    if (!q) return true;
    const path = (tagPathMap.value[t.id] || t.name).toLowerCase();
    return path.includes(q) || t.name.toLowerCase().includes(q);
  });
});

function isWatched(t) {
  return watchedIds.value.has(t.id) || watchedNames.value.has(t.name);
}

function isIndexing(t) {
  return indexingTags.value.has(t.name);
}

async function load() {
  try {
    const data = await api.listTags();
    tags.value = data.watched || [];
    available.value = data.available || [];
  } catch (e) {
    showError(`Failed to load tags: ${e.message}`);
  }
}

async function toggle(t) {
  if (isIndexing(t)) return;

  if (isWatched(t)) {
    try {
      await api.removeTag(t.name);
      await load();
      triggerReload();
    } catch (e) {
      showError(`Failed to remove tag: ${e.message}`);
    }
    return;
  }

  // Add — stream indexing progress via SSE.
  indexingTags.value = new Set([...indexingTags.value, t.name]);
  tags.value = [...tags.value, { tag: t.name, tag_id: t.id }];

  try {
    await api.addTag(t.name, t.id, (event) => {
      if (event.event === 'server_indexed') {
        // Refresh server list as each server is indexed.
        triggerReload();
      } else if (event.event === 'done') {
        indexingTags.value = new Set([...indexingTags.value].filter((n) => n !== t.name));
        triggerReload();
      } else if (event.event === 'error') {
        showError(`Indexing error: ${event.message}`);
        indexingTags.value = new Set([...indexingTags.value].filter((n) => n !== t.name));
      }
    });
  } catch (e) {
    showError(`Failed to add tag: ${e.message}`);
  }

  // Clean up in case stream ended without a done event.
  indexingTags.value = new Set([...indexingTags.value].filter((n) => n !== t.name));
  await load();
}

async function removeTag(t) {
  try {
    await api.removeTag(t.tag);
    await load();
    triggerReload();
  } catch (e) {
    showError(`Failed to remove tag: ${e.message}`);
  }
}

function onClickOutside(e) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target)) {
    pickerOpen.value = false;
  }
}

onMounted(() => {
  load();
  document.addEventListener('mousedown', onClickOutside);
});
onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside);
});
watch(reloadKey, load);
</script>

<template>
  <section class="section">
    <div class="section-header">
      <h2 class="section-title">Watched tags</h2>
    </div>
    <p class="section-desc">
      Content tagged with these tags is automatically discovered as MCP servers.
    </p>

    <div class="tag-list">
      <span v-if="tags.length === 0 && !pickerOpen" class="muted">No watched tags configured.</span>
      <span v-for="t in tags" :key="t.tag" class="tag-chip">
        {{ t.tag }}
        <span v-if="indexingTags.has(t.tag)" class="tag-spinner" />
        <button v-else-if="canEdit" @click="removeTag(t)" title="Remove tag">&times;</button>
      </span>
    </div>

    <div v-if="canEdit" class="tag-picker-wrapper" ref="wrapperRef">
      <button
        class="btn btn-add-tag"
        @click="pickerOpen = !pickerOpen; search = ''"
      >
        {{ pickerOpen ? 'Done' : '+ Add tags' }}
      </button>

      <div v-if="pickerOpen" class="tag-picker">
        <input
          v-model="search"
          class="tag-picker-search"
          placeholder="Filter tags..."
          autofocus
        >
        <div class="tag-picker-list">
          <div v-if="available.length === 0" class="tag-picker-empty">
            No tags available on the Connect server.
          </div>
          <div v-else-if="filteredTags.length === 0" class="tag-picker-empty">
            No tags matching "{{ search }}"
          </div>
          <label
            v-for="t in filteredTags"
            :key="t.id"
            class="tag-picker-item"
            :class="{ disabled: isIndexing(t) }"
          >
            <input
              type="checkbox"
              :checked="isWatched(t)"
              :disabled="isIndexing(t)"
              @change="toggle(t)"
            >
            <span class="tag-picker-name">{{ t.name }}</span>
            <span v-if="isIndexing(t)" class="tag-spinner" />
            <span v-else-if="tagPathMap[t.id] !== t.name" class="tag-picker-path">
              {{ tagPathMap[t.id] }}
            </span>
          </label>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tag-list {
  margin-bottom: 12px;
}

.tag-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(68, 112, 153, 0.3);
  border-top-color: #7eb8da;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.tag-picker-wrapper {
  position: relative;
}

.btn-add-tag {
  font-size: 0.8125rem;
}

.tag-picker {
  position: absolute;
  top: 100%;
  left: 0;
  width: 340px;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  margin-top: 6px;
  z-index: 50;
  overflow: hidden;
}

.tag-picker-search {
  width: 100%;
  border: none;
  border-bottom: 1px solid #374151;
  padding: 10px 12px;
  font-size: 0.8125rem;
  outline: none;
  background: #111827;
  color: #e5e7eb;
}

.tag-picker-search::placeholder {
  color: #6b7280;
}

.tag-picker-search:focus {
  background: #1f2937;
}

.tag-picker-list {
  max-height: 260px;
  overflow-y: auto;
}

.tag-picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background 0.1s;
  font-size: 0.8125rem;
}

.tag-picker-item:hover {
  background: #263040;
}

.tag-picker-item.disabled {
  opacity: 0.7;
  pointer-events: none;
}

.tag-picker-item input[type="checkbox"] {
  accent-color: #447099;
  flex-shrink: 0;
}

.tag-picker-name {
  font-weight: 500;
  color: #e5e7eb;
}

.tag-picker-path {
  font-size: 0.6875rem;
  color: #6b7280;
  margin-left: auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.tag-picker-empty {
  padding: 16px 12px;
  font-size: 0.8125rem;
  color: #6b7280;
  text-align: center;
}
</style>
