<script setup lang="ts">
import { ref } from "vue";
import type { FlatSpan } from "../types";
import SpanDetailPanel from "./SpanDetailPanel.vue";

defineProps<{
  spans: FlatSpan[];
  maxDepth: number;
  expandedSpans: Set<string>;
  matchingSpanIds: Set<string>;
  hasAnyFilter: boolean;
}>();

const emit = defineEmits<{
  toggleSpan: [spanId: string];
}>();

const hoveredSpan = ref<FlatSpan | null>(null);
const tooltipPos = ref({ x: 0, y: 0 });

function onSpanMouseMove(e: MouseEvent, span: FlatSpan) {
  hoveredSpan.value = span;
  const container = (e.currentTarget as HTMLElement).closest('.timeline-container');
  if (container) {
    const rect = container.getBoundingClientRect();
    tooltipPos.value = { x: e.clientX - rect.left + 8, y: e.clientY - rect.top - 32 };
  }
}

function onSpanMouseLeave() {
  hoveredSpan.value = null;
}

function isSpanDimmed(spanId: string, hasAnyFilter: boolean, matchingSpanIds: Set<string>): boolean {
  return hasAnyFilter && !matchingSpanIds.has(spanId);
}
</script>

<template>
  <div class="mt-0.5">
    <div
      class="relative w-full timeline-container"
      :style="{ height: `${(maxDepth + 1) * 22}px` }"
    >
      <div
        v-for="span in spans"
        :key="span.spanId"
        class="absolute overflow-hidden cursor-pointer rounded-sm border px-1 flex items-center transition-opacity"
        :class="[
          span.hasError
            ? (expandedSpans.has(span.spanId) ? 'bg-red-300 border-red-400' : 'bg-red-200 border-red-300 hover:bg-red-300')
            : (expandedSpans.has(span.spanId) ? 'bg-blue-400 border-blue-500' : 'bg-blue-200 border-blue-300 hover:bg-blue-300'),
          isSpanDimmed(span.spanId, hasAnyFilter, matchingSpanIds) ? 'opacity-30' : '',
        ]"
        :style="{
          left: `${span.offsetPct}%`,
          width: `${Math.max(span.widthPct, 0.3)}%`,
          top: `${span.depth * 22}px`,
          height: '20px',
        }"
        tabindex="0"
        role="button"
        @click="emit('toggleSpan', span.spanId)"
        @keydown.enter="emit('toggleSpan', span.spanId)"
        @keydown.space.prevent="emit('toggleSpan', span.spanId)"
        @mousemove="onSpanMouseMove($event, span)"
        @mouseleave="onSpanMouseLeave"
      >
        <span
          v-if="span.widthPct > 2"
          class="text-xs font-mono truncate leading-none text-gray-800 select-none"
        >{{ span.name }}</span>
      </div>

      <!-- Positioned tooltip -->
      <div
        v-if="hoveredSpan"
        class="absolute z-20 px-2 py-1 rounded bg-gray-800 text-white text-xs font-mono whitespace-nowrap pointer-events-none shadow-lg"
        :style="{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }"
      >
        {{ hoveredSpan.name }}
        <template v-if="hoveredSpan.durationMs != null"> — {{ hoveredSpan.durationMs.toFixed(1) }} ms</template>
      </div>
    </div>

    <!-- Color legend -->
    <div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-blue-200 border border-blue-300"></span> Normal</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-red-200 border border-red-300"></span> Error</span>
    </div>

    <!-- Detail panels -->
    <template v-for="span in spans" :key="`detail-${span.spanId}`">
      <Transition name="panel">
        <SpanDetailPanel v-if="expandedSpans.has(span.spanId)" :span="span" :show-name="true" @close="emit('toggleSpan', span.spanId)" />
      </Transition>
    </template>
  </div>
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
