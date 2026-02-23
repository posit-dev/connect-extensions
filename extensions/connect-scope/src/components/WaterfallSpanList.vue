<script setup lang="ts">
import type { FlatSpan } from "../types";
import { formatDuration } from "../utils/formatting";
import SpanDetailPanel from "./SpanDetailPanel.vue";

defineProps<{
  spans: FlatSpan[];
  expandedSpans: Set<string>;
  matchingSpanIds: Set<string>;
  hasAnyFilter: boolean;
}>();

const emit = defineEmits<{
  toggleSpan: [spanId: string];
}>();

function isSpanDimmed(spanId: string, hasAnyFilter: boolean, matchingSpanIds: Set<string>): boolean {
  return hasAnyFilter && !matchingSpanIds.has(spanId);
}
</script>

<template>
  <ul class="space-y-0.5 mt-0.5">
    <li v-for="span in spans" :key="span.spanId"
        class="py-0.5 cursor-pointer transition-opacity"
        :class="isSpanDimmed(span.spanId, hasAnyFilter, matchingSpanIds) ? 'opacity-30' : ''"
        tabindex="0"
        role="button"
        @click="emit('toggleSpan', span.spanId)"
        @keydown.enter="emit('toggleSpan', span.spanId)"
        @keydown.space.prevent="emit('toggleSpan', span.spanId)">
      <div class="flex items-center gap-2">
        <!-- Name, indented by depth with CSS tree lines -->
        <div class="w-80 shrink-0 flex items-center min-w-0 relative"
             :style="{ paddingLeft: `${span.depth * 16 + 4}px` }">
          <template v-if="span.depth > 0">
            <div class="absolute border-l border-gray-200"
                 :style="{ left: `${(span.depth - 1) * 16 + 14}px`, top: '0', bottom: '50%' }"></div>
            <div class="absolute border-t border-gray-200"
                 :style="{ left: `${(span.depth - 1) * 16 + 14}px`, top: '50%', width: '10px' }"></div>
          </template>
          <span class="text-sm text-gray-600 truncate bg-white px-0.5 z-10 relative" :title="span.name">{{ span.name }}</span>
          <svg v-if="span.hasError" class="shrink-0 ml-1 w-3.5 h-3.5 text-red-500" viewBox="0 0 20 20" fill="currentColor" title="Error">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0v-4.5A.75.75 0 0110 5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
          </svg>
        </div>
        <!-- Timeline bar -->
        <div class="relative flex-1 h-5 bg-gray-100 rounded overflow-hidden">
          <div class="absolute inset-y-0 rounded"
               :class="span.hasError ? 'bg-red-300' : 'bg-blue-300'"
               :style="{ left: `${span.offsetPct}%`, width: `${Math.max(span.widthPct, 0.5)}%` }">
          </div>
        </div>
        <!-- Duration -->
        <div class="text-right text-xs text-gray-500 shrink-0 font-mono whitespace-nowrap">
          <template v-if="span.durationMs != null">
            {{ formatDuration(span.durationMs) }}
          </template>
          <template v-else>—</template>
        </div>
      </div>

      <!-- Detail panel -->
      <Transition name="panel">
        <SpanDetailPanel v-if="expandedSpans.has(span.spanId)" :span="span" @close="emit('toggleSpan', span.spanId)" />
      </Transition>
    </li>
  </ul>
</template>

<style scoped>
.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.15s ease, max-height 0.15s ease;
  overflow: hidden;
}
.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  max-height: 0;
}
.panel-enter-to,
.panel-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
