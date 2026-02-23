<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import type { FlatSpan } from "../types";
import SpanDetailPanel from "./SpanDetailPanel.vue";
import { formatDuration } from "../utils/formatting";

const ROW_HEIGHT = 24;
const AXIS_HEIGHT = 28;
const LABEL_PADDING = 4;
const CHAR_WIDTH = 7;

const props = defineProps<{
  spans: FlatSpan[];
  maxDepth: number;
  totalDurationMs: number;
  matchingSpanIds?: Set<string>;
  hasAnyFilter?: boolean;
}>();

// --- State ---
const svgRef = ref<SVGSVGElement | null>(null);
const containerRef = ref<HTMLDivElement | null>(null);
const svgWidth = ref(800);
const hoveredSpan = ref<FlatSpan | null>(null);
const tooltipPos = ref({ x: 0, y: 0 });
const selectedSpanId = ref<string | null>(null);

// Zoom: percentage range of the trace (0–100)
const viewport = ref({ start: 0, end: 100 });
const isDragging = ref(false);
const dragStartX = ref(0);
const dragCurrentX = ref(0);

const isZoomed = computed(() => viewport.value.start > 0.01 || viewport.value.end < 99.99);
const svgHeight = computed(() => AXIS_HEIGHT + (props.maxDepth + 1) * ROW_HEIGHT);
const viewRange = computed(() => viewport.value.end - viewport.value.start);

const selectedSpan = computed(() =>
  selectedSpanId.value ? props.spans.find(s => s.spanId === selectedSpanId.value) ?? null : null
);

// --- Colors ---
function spanColor(span: FlatSpan, selected: boolean): { fill: string; stroke: string } {
  if (span.hasError) {
    return selected
      ? { fill: "#f87171", stroke: "#ef4444" }
      : { fill: "#fca5a5", stroke: "#f87171" };
  }
  return selected
    ? { fill: "#60a5fa", stroke: "#3b82f6" }
    : { fill: "#bfdbfe", stroke: "#93c5fd" };
}

// --- Layout ---
const visibleSpans = computed(() => {
  const { start, end } = viewport.value;
  const range = end - start;
  const minPct = range / svgWidth.value; // 1px threshold in percent
  return props.spans.filter((s) => {
    const sEnd = s.offsetPct + s.widthPct;
    return sEnd >= start && s.offsetPct <= end && s.widthPct >= minPct;
  });
});

function spanRect(span: FlatSpan) {
  const { start } = viewport.value;
  const range = viewRange.value;
  const w = svgWidth.value;
  const x = ((span.offsetPct - start) / range) * w;
  const width = (span.widthPct / range) * w;
  const y = AXIS_HEIGHT + span.depth * ROW_HEIGHT;
  return { x, y, width, height: ROW_HEIGHT };
}

function truncateLabel(text: string, widthPx: number): string {
  const max = Math.floor((widthPx - LABEL_PADDING * 2) / CHAR_WIDTH);
  if (max <= 0) return "";
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + "\u2026";
}

// --- Time axis ---
const timeTicks = computed(() => {
  const { start, end } = viewport.value;
  const range = end - start;
  const dMs = props.totalDurationMs;
  const count = 6;
  const ticks: Array<{ x: number; label: string }> = [];
  for (let i = 0; i < count; i++) {
    const pct = start + (i / (count - 1)) * range;
    const ms = (pct / 100) * dMs;
    ticks.push({
      x: (i / (count - 1)) * svgWidth.value,
      label: formatDuration(ms),
    });
  }
  return ticks;
});

// --- Resize observer ---
let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (containerRef.value) {
    svgWidth.value = containerRef.value.clientWidth;
    resizeObserver = new ResizeObserver((entries) => {
      for (const e of entries) svgWidth.value = e.contentRect.width;
    });
    resizeObserver.observe(containerRef.value);
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", onWindowMouseUp);
});

// --- Hover ---
function onSpanHover(e: MouseEvent, span: FlatSpan) {
  hoveredSpan.value = span;
  if (containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect();
    tooltipPos.value = {
      x: e.clientX - rect.left + 12,
      y: e.clientY - rect.top - 40,
    };
  }
}

// --- Click to select ---
function onSpanClick(spanId: string) {
  selectedSpanId.value = selectedSpanId.value === spanId ? null : spanId;
}

// --- Drag-to-zoom ---
function onSvgMouseDown(e: MouseEvent) {
  if (e.button !== 0) return;
  isDragging.value = true;
  const rect = svgRef.value!.getBoundingClientRect();
  dragStartX.value = e.clientX - rect.left;
  dragCurrentX.value = dragStartX.value;
  window.addEventListener("mousemove", onWindowMouseMove);
  window.addEventListener("mouseup", onWindowMouseUp);
}

function onWindowMouseMove(e: MouseEvent) {
  if (!isDragging.value || !svgRef.value) return;
  const rect = svgRef.value.getBoundingClientRect();
  dragCurrentX.value = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
}

function onWindowMouseUp() {
  if (!isDragging.value) return;
  isDragging.value = false;
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", onWindowMouseUp);

  const w = svgWidth.value;
  if (w === 0) return;
  const x1 = Math.min(dragStartX.value, dragCurrentX.value);
  const x2 = Math.max(dragStartX.value, dragCurrentX.value);

  if ((x2 - x1) / w < 0.02) return;

  const { start } = viewport.value;
  const range = viewRange.value;
  viewport.value = { start: start + (x1 / w) * range, end: start + (x2 / w) * range };
}

function resetZoom() {
  viewport.value = { start: 0, end: 100 };
}

// --- Keyboard ---
function onKeyDown(e: KeyboardEvent) {
  if (e.key === "Escape") {
    if (selectedSpanId.value) {
      selectedSpanId.value = null;
      e.preventDefault();
    } else if (isZoomed.value) {
      resetZoom();
      e.preventDefault();
    }
  }
}

onMounted(() => window.addEventListener("keydown", onKeyDown));
onUnmounted(() => window.removeEventListener("keydown", onKeyDown));

watch(() => props.spans, () => {
  viewport.value = { start: 0, end: 100 };
  selectedSpanId.value = null;
});

function isSpanDimmed(spanId: string): boolean {
  return !!props.hasAnyFilter && !!props.matchingSpanIds && !props.matchingSpanIds.has(spanId);
}

const selectionRect = computed(() => {
  if (!isDragging.value) return null;
  const x = Math.min(dragStartX.value, dragCurrentX.value);
  const w = Math.abs(dragCurrentX.value - dragStartX.value);
  return { x, y: 0, width: w, height: svgHeight.value };
});
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-1.5">
      <p class="text-xs text-gray-400">Drag to zoom &middot; click a span for details</p>
      <button
        v-if="isZoomed"
        class="px-2 py-0.5 text-xs text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"
        @click="resetZoom"
      >Reset zoom</button>
    </div>

    <div ref="containerRef" class="relative">
      <svg
        ref="svgRef"
        class="w-full select-none"
        :height="svgHeight"
        :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
        preserveAspectRatio="none"
        @mousedown.prevent="onSvgMouseDown"
      >
        <!-- Span blocks -->
        <g v-for="span in visibleSpans" :key="span.spanId">
          <rect
            :x="spanRect(span).x"
            :y="spanRect(span).y"
            :width="spanRect(span).width"
            :height="spanRect(span).height"
            :fill="spanColor(span, selectedSpanId === span.spanId).fill"
            :stroke="spanColor(span, selectedSpanId === span.spanId).stroke"
            stroke-width="1"
            rx="0"
            class="cursor-pointer"
            :opacity="isSpanDimmed(span.spanId) ? 0.3 : 1"
            @click.stop="onSpanClick(span.spanId)"
            @mouseenter="onSpanHover($event, span)"
            @mousemove="onSpanHover($event, span)"
            @mouseleave="hoveredSpan = null"
          />
          <text
            v-if="spanRect(span).width > 40"
            :x="spanRect(span).x + LABEL_PADDING"
            :y="spanRect(span).y + (ROW_HEIGHT - 2) / 2"
            dominant-baseline="central"
            class="text-[11px] fill-gray-800 pointer-events-none select-none"
            font-family="ui-monospace, monospace"
          >{{ truncateLabel(span.name, spanRect(span).width) }}</text>
        </g>

        <!-- Time axis (top) -->
        <line
          :x1="0" :y1="AXIS_HEIGHT" :x2="svgWidth" :y2="AXIS_HEIGHT"
          stroke="#d1d5db" stroke-width="1"
        />
        <g v-for="(tick, i) in timeTicks" :key="i">
          <line
            :x1="tick.x" :y1="AXIS_HEIGHT - 4"
            :x2="tick.x" :y2="AXIS_HEIGHT"
            stroke="#9ca3af" stroke-width="1"
          />
          <text
            :x="tick.x"
            :y="14"
            :text-anchor="i === 0 ? 'start' : i === timeTicks.length - 1 ? 'end' : 'middle'"
            class="text-[10px] fill-gray-400"
            font-family="ui-monospace, monospace"
          >{{ tick.label }}</text>
        </g>

        <!-- Drag selection overlay -->
        <rect
          v-if="selectionRect"
          :x="selectionRect.x"
          :y="selectionRect.y"
          :width="selectionRect.width"
          :height="selectionRect.height"
          fill="rgba(59,130,246,0.1)"
          stroke="#3b82f6"
          stroke-width="1"
          stroke-dasharray="4,4"
          class="pointer-events-none"
        />
      </svg>

      <!-- Tooltip -->
      <div
        v-if="hoveredSpan && !isDragging"
        class="absolute z-20 px-2 py-1.5 rounded bg-gray-800 text-white text-xs font-mono whitespace-nowrap pointer-events-none shadow-lg"
        :style="{ left: `${tooltipPos.x}px`, top: `${tooltipPos.y}px` }"
      >
        <div class="font-semibold">{{ hoveredSpan.name }}</div>
        <div v-if="hoveredSpan.durationMs != null" class="text-gray-300">
          {{ formatDuration(hoveredSpan.durationMs) }}
        </div>
      </div>
    </div>

    <!-- Color legend -->
    <div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
      <span class="flex items-center gap-1">
        <span class="w-3 h-3 rounded-sm bg-blue-200 border border-blue-300"></span>
        Normal
      </span>
      <span class="flex items-center gap-1">
        <span class="w-3 h-3 rounded-sm bg-red-200 border border-red-300"></span>
        Error
      </span>
    </div>

    <!-- Detail panel for selected span -->
    <Transition name="panel">
      <SpanDetailPanel
        v-if="selectedSpan"
        :span="selectedSpan"
        :show-name="true"
        @close="selectedSpanId = null"
      />
    </Transition>
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
