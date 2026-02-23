<script setup lang="ts">
import type { TraceGroup } from "../types";
import { formatTime, formatDuration } from "../utils/formatting";

defineProps<{
  group: TraceGroup;
  isExpanded: boolean;
  maxTraceDurationMs: number;
}>();

defineEmits<{
  toggle: [];
}>();
</script>

<template>
  <div
    class="flex items-center gap-2 py-0.5 rounded cursor-pointer select-none hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1"
    :class="isExpanded ? 'border-b border-gray-100 pb-2 mb-2 hover:bg-transparent' : ''"
    tabindex="0"
    role="button"
    :aria-expanded="isExpanded"
    @click="$emit('toggle')"
    @keydown.enter="$emit('toggle')"
    @keydown.space.prevent="$emit('toggle')"
  >
    <!-- Chevron + name + timestamp -->
    <div class="w-80 shrink-0 flex items-center gap-1.5 min-w-0 pl-1">
      <svg class="w-3 h-3 shrink-0 text-gray-400 transition-transform duration-100"
           :class="isExpanded ? 'rotate-90' : ''"
           viewBox="0 0 6 10" fill="none"
           stroke="currentColor" stroke-width="1.5"
           stroke-linecap="round" stroke-linejoin="round">
        <polyline points="1,1 5,5 1,9" />
      </svg>
      <div class="min-w-0">
        <div class="flex items-center gap-1.5 min-w-0">
          <span class="text-sm font-semibold text-gray-800 truncate" :title="group.label">{{ group.label }}</span>
          <span v-if="group.hasError" class="text-red-500 shrink-0 text-xs" title="One or more spans errored">●</span>
        </div>
        <div class="text-xs text-gray-400 leading-none mt-0.5">{{ formatTime(group.startMs) }} · {{ group.spanCount }} spans</div>
      </div>
    </div>
    <!-- Summary bar -->
    <div class="relative flex-1 h-5 bg-gray-100 rounded overflow-hidden">
      <div class="absolute inset-y-0 left-0 bg-blue-400 rounded"
           :style="{ width: `${(group.totalDurationMs / maxTraceDurationMs) * 100}%` }">
      </div>
    </div>
    <!-- Total duration -->
    <div class="w-16 text-right text-xs text-gray-600 shrink-0 font-mono whitespace-nowrap">
      {{ formatDuration(group.totalDurationMs) }}
    </div>
  </div>
</template>
