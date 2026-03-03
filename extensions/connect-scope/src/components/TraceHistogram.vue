<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import type { FlatSpan } from "../types";

const NUM_BINS = 100;
const BAR_HEIGHT = 48;

const props = defineProps<{
  spans: FlatSpan[];
  totalDurationMs: number;
}>();

const viewportModel = defineModel<{ start: number; end: number }>("viewport");

const containerRef = ref<HTMLDivElement | null>(null);
const svgRef = ref<SVGSVGElement | null>(null);
const containerWidth = ref(800);

// Drag-to-zoom state
const isDragging = ref(false);
const dragStartX = ref(0);
const dragCurrentX = ref(0);

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (containerRef.value) {
    containerWidth.value = containerRef.value.clientWidth;
    resizeObserver = new ResizeObserver((entries) => {
      for (const e of entries) containerWidth.value = e.contentRect.width;
    });
    resizeObserver.observe(containerRef.value);
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  window.removeEventListener("mousemove", onWindowMouseMove);
  window.removeEventListener("mouseup", onWindowMouseUp);
});

// Re-bucket root spans into NUM_BINS bins within the current viewport window.
// When zoomed, spans are redistributed across the visible range so bar width
// stays consistent and granularity increases.
const bins = computed(() => {
  const vp = viewportModel.value ?? { start: 0, end: 100 };
  const vpStart = vp.start;
  const vpEnd = vp.end;
  const vpRange = vpEnd - vpStart;

  const counts = new Array<number>(NUM_BINS).fill(0);
  const hasError = new Array<boolean>(NUM_BINS).fill(false);

  for (const span of props.spans) {
    // Skip spans outside the viewport
    if (span.offsetPct < vpStart || span.offsetPct >= vpEnd) continue;
    const bin = Math.min(
      Math.floor(((span.offsetPct - vpStart) / vpRange) * NUM_BINS),
      NUM_BINS - 1,
    );
    counts[bin]!++;
    if (span.hasError) hasError[bin] = true;
  }

  const maxCount = Math.max(...counts, 1);
  const barWidth = containerWidth.value / NUM_BINS;

  return counts.map((count, i) => ({
    count,
    maxCount,
    hasError: hasError[i],
    x: i * barWidth,
    width: barWidth,
    heightFraction: count / maxCount,
  }));
});

const maxCount = computed(() => bins.value[0]?.maxCount ?? 1);

// --- Drag-to-zoom ---
function onSvgMouseDown(e: MouseEvent) {
  if (e.button !== 0 || !viewportModel.value) return;
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

  const w = containerWidth.value;
  if (w === 0) return;
  const x1 = Math.min(dragStartX.value, dragCurrentX.value);
  const x2 = Math.max(dragStartX.value, dragCurrentX.value);

  if ((x2 - x1) / w < 0.02) return;

  const vp = viewportModel.value!;
  const range = vp.end - vp.start;
  viewportModel.value = {
    start: vp.start + (x1 / w) * range,
    end: vp.start + (x2 / w) * range,
  };
}

const selectionRect = computed(() => {
  if (!isDragging.value) return null;
  const x = Math.min(dragStartX.value, dragCurrentX.value);
  const w = Math.abs(dragCurrentX.value - dragStartX.value);
  return { x, y: 0, width: w, height: BAR_HEIGHT };
});
</script>

<template>
  <div ref="containerRef" class="relative w-full">
    <svg
      ref="svgRef"
      class="w-full block select-none"
      :class="viewportModel ? 'cursor-crosshair' : ''"
      :height="BAR_HEIGHT"
      :viewBox="`0 0 ${containerWidth} ${BAR_HEIGHT}`"
      preserveAspectRatio="none"
      @mousedown.prevent="onSvgMouseDown"
    >
      <rect
        v-for="(bin, i) in bins"
        :key="i"
        :x="bin.x"
        :y="BAR_HEIGHT * (1 - bin.heightFraction)"
        :width="bin.width"
        :height="BAR_HEIGHT * bin.heightFraction"
        :fill="bin.hasError ? '#fca5a5' : '#bfdbfe'"
      />

      <!-- Drag selection overlay -->
      <rect
        v-if="selectionRect"
        :x="selectionRect.x"
        :y="selectionRect.y"
        :width="selectionRect.width"
        :height="selectionRect.height"
        fill="rgba(59,130,246,0.15)"
        stroke="#3b82f6"
        stroke-width="1"
        stroke-dasharray="4,4"
        class="pointer-events-none"
      />
    </svg>
    <span
      class="absolute top-0 left-1 text-[10px] text-gray-400 font-mono leading-none pointer-events-none"
      style="padding-top: 2px"
    >{{ maxCount }}</span>
  </div>
</template>
