<script setup lang="ts">
defineProps<{
  viewMode: string;
  traceSortOrder: string;
  nameFilter: string | null;
  totalTraces: number;
  visibleTraces: number;
  hasAnyFilter: boolean;
  allExpanded: boolean;
}>();

defineEmits<{
  'update:viewMode': [mode: string];
  'update:traceSortOrder': [order: string];
  'update:nameFilter': [name: string | null];
  toggleAllTraces: [];
}>();
</script>

<template>
  <div class="flex items-center justify-between mb-2">
    <div class="flex items-center gap-2">
      <p class="text-xs text-gray-400">
        {{ visibleTraces }}<template v-if="hasAnyFilter"> / {{ totalTraces }}</template> traces
      </p>
      <span
        v-if="nameFilter != null"
        class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium"
      >
        {{ nameFilter }}
        <button class="hover:text-blue-900" @click="$emit('update:nameFilter', null)">&times;</button>
      </span>
      <template v-if="viewMode !== 'aggregate'">
        <div class="flex items-center gap-0.5 border border-gray-200 rounded p-0.5">
          <button
            class="px-2 py-0.5 rounded text-xs transition-colors"
            :class="traceSortOrder === 'newest' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
            @click="$emit('update:traceSortOrder', 'newest')"
          >Newest</button>
          <button
            class="px-2 py-0.5 rounded text-xs transition-colors"
            :class="traceSortOrder === 'slowest' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
            @click="$emit('update:traceSortOrder', 'slowest')"
          >Slowest</button>
        </div>
        <button
          class="text-xs text-gray-400 hover:text-gray-600"
          @click="$emit('toggleAllTraces')"
        >{{ allExpanded ? 'Collapse all' : 'Expand all' }}</button>
      </template>
    </div>
    <div class="flex items-center gap-0.5 border border-gray-200 rounded p-0.5">
      <button
        class="px-2 py-0.5 rounded text-xs transition-colors"
        :class="viewMode === 'waterfall' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
        @click="$emit('update:viewMode', 'waterfall')"
      >Waterfall</button>
      <button
        class="px-2 py-0.5 rounded text-xs transition-colors"
        :class="viewMode === 'timeline' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
        @click="$emit('update:viewMode', 'timeline')"
      >Timeline</button>
      <button
        class="px-2 py-0.5 rounded text-xs transition-colors"
        :class="viewMode === 'aggregate' ? 'bg-gray-200 text-gray-800' : 'text-gray-400 hover:text-gray-600'"
        @click="$emit('update:viewMode', 'aggregate')"
      >Aggregate</button>
    </div>
  </div>
</template>
