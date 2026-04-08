<script setup>
import { ref, computed, inject } from 'vue';

const canEdit = inject('canEdit');
const callToolEnabled = inject('callToolEnabled');
const toggleCallTool = inject('toggleCallTool');

const gatewayUrl = computed(() => {
  const loc = window.location;
  return `${loc.protocol}//${loc.host}${loc.pathname.replace(/\/$/, '')}`;
});

const mcpUrl = computed(() => `${gatewayUrl.value}/mcp`);

const open = ref(true);
const activeTab = ref('claude-code');

const tabs = [
  { id: 'claude-code', label: 'Claude Code' },
  { id: 'claude-desktop', label: 'Claude Desktop' },
  { id: 'vscode', label: 'VS Code (Continue)' },
  { id: 'cursor', label: 'Cursor' },
];
</script>

<template>
  <section class="guide-section">
    <button class="guide-toggle" @click="open = !open">
      <svg
        class="guide-chevron"
        :class="{ open }"
        width="16" height="16" viewBox="0 0 24 24"
        fill="none" stroke="currentColor" stroke-width="2"
      >
        <path d="M9 18l6-6-6-6" />
      </svg>
      <span class="guide-toggle-text">Connect to Bridge</span>
    </button>

    <div v-if="open" class="guide-body">
      <p class="guide-intro">
        This gateway exposes MCP tools that LLMs use to discover, execute, and
        manage tools across all registered servers:
      </p>

      <div class="tools-ref">
        <div class="tools-ref-item">
          <code class="tools-ref-name">search_tools</code>
          <span class="tools-ref-desc">
            Semantic search across all indexed MCP tools. Accepts a natural-language
            <code>query</code> and optional <code>limit</code> (default 10). Returns
            matching tool names, descriptions, input schemas, and the
            <code>server_guid</code> needed to call them.
          </span>
        </div>
        <div class="tools-ref-item">
          <code class="tools-ref-name">add_tools</code>
          <span class="tools-ref-desc">
            Register tools from <code>search_tools</code> results into the current
            session. Accepts a list of <code>tool_names</code>. Added tools become
            callable in subsequent prompts and are isolated to this session.
          </span>
        </div>
        <div class="tools-ref-item">
          <code class="tools-ref-name">remove_tools</code>
          <span class="tools-ref-desc">
            Remove dynamically registered tools from the current session. Permanent
            tools cannot be removed.
          </span>
        </div>
        <div class="tools-ref-item">
          <div class="tools-ref-name-row">
            <code class="tools-ref-name">call_tool</code>
            <label v-if="canEdit" class="toggle-label">
              <input
                type="checkbox"
                class="toggle-input"
                :checked="callToolEnabled"
                @change="toggleCallTool($event.target.checked)"
              >
              <span class="toggle-switch" />
            </label>
            <span v-else-if="callToolEnabled" class="status-badge enabled">Enabled</span>
            <span v-else class="status-badge disabled">Disabled</span>
          </div>
          <span class="tools-ref-desc">
            <template v-if="callToolEnabled">
              Immediate tool execution proxy. Requires
              <code>server_guid</code>, <code>tool_name</code>, and optional
              <code>arguments</code> from <code>search_tools</code> results.
              Use as a fallback when you need to execute a tool without waiting
              for <code>add_tools</code> registration.
            </template>
            <template v-else>
              Immediate tool execution proxy (currently disabled). When enabled,
              allows AI agents to call any discovered tool without first adding it.
              Enable this if your MCP client doesn't support dynamic tool registration.
            </template>
          </span>
        </div>
      </div>

      <div class="guide-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="guide-tab"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="guide-panel">
        <template v-if="activeTab === 'claude-code'">
          <p>Run this command:</p>
          <pre class="guide-code">claude mcp add --transport http mcp-gateway {{ mcpUrl }} \
  --header "Authorization: Key YOUR_POSIT_CONNECT_API_KEY"</pre>
        </template>

        <template v-if="activeTab === 'claude-desktop'">
          <p>
            Add to
            <code>~/Library/Application Support/Claude/claude_desktop_config.json</code>
            (macOS) or
            <code>%APPDATA%\Claude\claude_desktop_config.json</code> (Windows):
          </p>
          <pre class="guide-code">{
  "mcpServers": {
    "mcp-gateway": {
      "type": "streamable-http",
      "url": "{{ mcpUrl }}",
      "headers": {
        "Authorization": "Key YOUR_POSIT_CONNECT_API_KEY"
      }
    }
  }
}</pre>
        </template>

        <template v-if="activeTab === 'vscode'">
          <p>Add to your Continue config:</p>
          <pre class="guide-code">{
  "mcpServers": [
    {
      "name": "mcp-gateway",
      "transport": {
        "type": "streamable-http",
        "url": "{{ mcpUrl }}",
        "headers": {
          "Authorization": "Key YOUR_POSIT_CONNECT_API_KEY"
        }
      }
    }
  ]
}</pre>
        </template>

        <template v-if="activeTab === 'cursor'">
          <p>Add to your MCP settings in Cursor preferences:</p>
          <pre class="guide-code">{
  "mcp-gateway": {
    "url": "{{ mcpUrl }}",
    "headers": {
      "Authorization": "Key YOUR_POSIT_CONNECT_API_KEY"
    }
  }
}</pre>
        </template>
      </div>
    </div>
  </section>
</template>
