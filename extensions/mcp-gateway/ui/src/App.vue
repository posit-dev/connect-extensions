<script setup>
import { ref, onMounted } from 'vue';
import * as api from './api.js';
import ConnectionGuide from './components/ConnectionGuide.vue';
import ToolSearch from './components/ToolSearch.vue';
import WatchedTags from './components/WatchedTags.vue';
import ServerList from './components/ServerList.vue';

const error = ref('');
let errorTimer = null;

function showError(msg) {
  error.value = msg;
  clearTimeout(errorTimer);
  errorTimer = setTimeout(() => { error.value = ''; }, 5000);
}

const reindexing = ref(false);

async function reindex() {
  reindexing.value = true;
  try {
    await api.triggerReindex();
  } catch (e) {
    showError(`Re-index failed: ${e.message}`);
  } finally {
    setTimeout(() => { reindexing.value = false; }, 3000);
  }
}

// Expose error handler to child components via provide.
import { provide } from 'vue';
provide('showError', showError);

// A shared reload trigger so children can tell each other to refresh.
const reloadKey = ref(0);
provide('reloadKey', reloadKey);
provide('triggerReload', () => { reloadKey.value++; });

// Permission and settings state
const canEdit = ref(false);
const callToolEnabled = ref(false);
const showCallToolModal = ref(false);

onMounted(async () => {
  try {
    const me = await api.getMe();
    canEdit.value = (me.role === 'owner' || me.role === 'editor');
  } catch {
    canEdit.value = false;
  }
  try {
    const settings = await api.getSettings();
    callToolEnabled.value = settings.call_tool_enabled || false;
  } catch {
    // default to false
  }
});

async function toggleCallTool(newValue) {
  if (newValue) {
    showCallToolModal.value = true;  // Show warning first
    return;
  }
  // Disable directly
  try {
    const result = await api.updateSettings({ call_tool_enabled: false });
    callToolEnabled.value = result.call_tool_enabled;
  } catch (e) {
    showError(`Failed to update settings: ${e.message}`);
  }
}

async function confirmEnableCallTool() {
  showCallToolModal.value = false;
  try {
    const result = await api.updateSettings({ call_tool_enabled: true });
    callToolEnabled.value = result.call_tool_enabled;
  } catch (e) {
    showError(`Failed to update settings: ${e.message}`);
  }
}

provide('canEdit', canEdit);
provide('callToolEnabled', callToolEnabled);
provide('toggleCallTool', toggleCallTool);
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <div class="logo">
        <svg class="logo-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <defs>
            <linearGradient id="aiGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#EC4899" />
              <stop offset="100%" stop-color="#8B5CF6" />
            </linearGradient>
          </defs>
          <line x1="5" y1="8" x2="5" y2="20" />
          <line x1="19" y1="8" x2="19" y2="20" />
          <line x1="1" y1="20" x2="23" y2="20" />
          <path d="M1 10 Q5 4 12 8 Q19 4 23 10" />
          <line x1="8" y1="6.8" x2="8" y2="20" />
          <line x1="12" y1="8" x2="12" y2="20" />
          <line x1="16" y1="6.8" x2="16" y2="20" />
          <path d="M21,1 Q21,3 19,3 Q21,3 21,5 Q21,3 23,3 Q21,3 21,1 Z" fill="url(#aiGradient)" />
        </svg>
        Bridge
      </div>
      <button v-if="canEdit" class="btn" :disabled="reindexing" @click="reindex">
        {{ reindexing ? 'Indexing...' : 'Re-index' }}
      </button>
    </div>
  </header>

  <main class="container">
    <ConnectionGuide />
    <ToolSearch />
    <WatchedTags />
    <ServerList />
  </main>

  <Teleport to="body">
    <div v-if="error" class="error-toast-container">
      <div class="error-toast">{{ error }}</div>
    </div>
  </Teleport>

  <Teleport to="body">
    <div v-if="showCallToolModal" class="modal-overlay" @click.self="showCallToolModal = false">
      <div class="modal">
        <h3 class="modal-title">Enable call_tool?</h3>
        <p class="modal-body">
          <strong>Security warning:</strong> Enabling <code>call_tool</code> allows AI agents
          to execute any discovered tool after a single permission grant. Unlike direct tool
          calls which require individual approval, <code>call_tool</code> acts as a universal
          proxy — once permitted, all registered tools can be called without further confirmation.
        </p>
        <p class="modal-body">
          Only enable this if your MCP client does not support dynamic tool registration
          (tools/list_changed notifications).
        </p>
        <div class="modal-actions">
          <button class="btn" @click="showCallToolModal = false">Cancel</button>
          <button class="btn btn-danger" @click="confirmEnableCallTool">Enable call_tool</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
