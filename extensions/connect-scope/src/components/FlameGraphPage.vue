<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import type { ContentItem, Job, OtlpRecord, OtlpSpan, FlatSpan, TraceGroup } from "../types";
import { otlpValue, buildTraceGroup } from "../utils/trace-builder";
import { timeAgo, formatDuration } from "../utils/formatting";
import { useTraceFilters } from "../composables/useTraceFilters";
import { apiBase } from "../api";
import FlameChart from "./FlameChart.vue";
import TraceFilterSidebar from "./TraceFilterSidebar.vue";
import SpanDetailPanel from "./SpanDetailPanel.vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";

const props = defineProps<{
  content: ContentItem;
  job: Job;
}>();

const isLoading = ref(false);
const error = ref<string | null>(null);
const records = ref<OtlpRecord[]>([]);

// --- Selected span / trace detail ---
const selectedSpanId = ref<string | null>(null);
const detailSpanId = ref<string | null>(null);

function onSelectSpan(spanId: string | null) {
  selectedSpanId.value = spanId;
  detailSpanId.value = null;
}

function onDetailSelectSpan(spanId: string | null) {
  detailSpanId.value = spanId;
}

const detailSpan = computed(() => {
  if (!detailSpanId.value || !selectedTraceGroup.value) return null;
  return selectedTraceGroup.value.spans.find(s => s.spanId === detailSpanId.value) ?? null;
});

onMounted(async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await fetch(
      `${apiBase}/api/content/${props.content.guid}/jobs/${props.job.key}/traces`
    );
    if (!response.ok) throw new Error("Failed to fetch traces");
    records.value = await response.json();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Unknown error";
  } finally {
    isLoading.value = false;
  }
});

// --- Raw spans ---
const rawSpans = computed((): OtlpSpan[] =>
  records.value
    .flatMap(r => r.resourceSpans ?? [])
    .flatMap(rs => rs.scopeSpans ?? [])
    .flatMap(ss => ss.spans ?? [])
);

// --- Per-trace groups (for the waterfall detail view) ---
const perTraceGroups = computed((): Map<string, TraceGroup> => {
  const byTrace = new Map<string, OtlpSpan[]>();
  for (const s of rawSpans.value) {
    const tid = s.traceId ?? "unknown";
    const arr = byTrace.get(tid);
    if (arr) arr.push(s);
    else byTrace.set(tid, [s]);
  }
  const groups = new Map<string, TraceGroup>();
  for (const [tid, spans] of byTrace) {
    groups.set(tid, buildTraceGroup(tid, spans));
  }
  return groups;
});

// --- spanId → traceId lookup ---
const spanToTrace = computed((): Map<string, string> => {
  const m = new Map<string, string>();
  for (const s of rawSpans.value) {
    if (s.spanId && s.traceId) m.set(s.spanId, s.traceId);
  }
  return m;
});

// --- Selected trace group ---
const selectedTraceGroup = computed((): TraceGroup | null => {
  if (!selectedSpanId.value) return null;
  const traceId = spanToTrace.value.get(selectedSpanId.value);
  if (!traceId) return null;
  return perTraceGroups.value.get(traceId) ?? null;
});

/**
 * Build a single flat span list across all traces in this job,
 * with offsets computed relative to the global time range.
 */
const flameData = computed(() => {
  const raw = rawSpans.value;
  if (raw.length === 0) return { spans: [] as FlatSpan[], maxDepth: 0, totalDurationMs: 0, startNs: 0n };

  // Pre-parse timestamps
  const startMap = new Map<OtlpSpan, bigint>();
  const endMap = new Map<OtlpSpan, bigint | null>();
  for (const s of raw) {
    startMap.set(s, BigInt(s.startTimeUnixNano ?? "0"));
    endMap.set(s, s.endTimeUnixNano != null ? BigInt(s.endTimeUnixNano) : null);
  }

  // Global time bounds across all traces in this job
  let globalStart = BigInt("9".repeat(20));
  let globalEnd = 0n;
  for (const s of raw) {
    const t0 = startMap.get(s)!;
    const t1 = endMap.get(s) ?? t0;
    if (t0 < globalStart) globalStart = t0;
    if (t1 > globalEnd) globalEnd = t1;
  }
  const globalDurationNs = globalEnd - globalStart || 1n;

  // Group by trace
  const byTrace = new Map<string, OtlpSpan[]>();
  for (const s of raw) {
    const tid = s.traceId ?? "unknown";
    const arr = byTrace.get(tid);
    if (arr) arr.push(s);
    else byTrace.set(tid, [s]);
  }

  const flat: FlatSpan[] = [];

  for (const [, traceSpans] of byTrace) {
    const byId = new Map<string, OtlpSpan>();
    for (const s of traceSpans) {
      if (s.spanId) byId.set(s.spanId, s);
    }
    const childrenByParent = new Map<string, OtlpSpan[]>();
    for (const s of traceSpans) {
      const pid = s.parentSpanId;
      if (pid && byId.has(pid)) {
        const arr = childrenByParent.get(pid);
        if (arr) arr.push(s);
        else childrenByParent.set(pid, [s]);
      }
    }

    const cmp = (a: OtlpSpan, b: OtlpSpan) =>
      startMap.get(a)! < startMap.get(b)! ? -1 : 1;
    for (const children of childrenByParent.values()) children.sort(cmp);

    const visit = (s: OtlpSpan, depth: number) => {
      const sNs = startMap.get(s)!;
      const eNs = endMap.get(s) ?? null;
      const durationMs = eNs != null ? Number(eNs - sNs) / 1_000_000 : null;
      const offsetPct = Number((sNs - globalStart) * 10000n / globalDurationNs) / 100;
      const widthPct = eNs != null
        ? Number((eNs - sNs) * 10000n / globalDurationNs) / 100
        : 0;

      const exceptionEvent = s.events?.find(e => e.name === "exception") ?? null;
      const exAttr = (key: string) => {
        const a = exceptionEvent?.attributes?.find(a => a.key === key);
        return a ? otlpValue(a.value) : undefined;
      };

      flat.push({
        name: s.name,
        spanId: s.spanId ?? `anon-${flat.length}`,
        parentSpanId: s.parentSpanId ?? null,
        startNs: sNs,
        durationMs,
        depth,
        offsetPct,
        widthPct,
        hasError: s.status?.code === 2,
        attributes: s.attributes ?? [],
        statusMessage: s.status?.message ?? null,
        exception: exceptionEvent
          ? { type: exAttr("exception.type"), message: exAttr("exception.message"), stacktrace: exAttr("exception.stacktrace") }
          : null,
      });

      for (const child of childrenByParent.get(s.spanId ?? "") ?? []) {
        visit(child, depth + 1);
      }
    };

    const roots = traceSpans
      .filter(s => !s.parentSpanId || !byId.has(s.parentSpanId))
      .sort(cmp);
    for (const root of roots) visit(root, 0);
  }

  const maxDepth = flat.reduce((m, s) => Math.max(m, s.depth), 0);
  const totalDurationMs = Number(globalDurationNs) / 1_000_000;

  return { spans: flat, maxDepth, totalDurationMs, startNs: globalStart };
});

/**
 * Wrap the flat spans in a synthetic TraceGroup so we can reuse useTraceFilters.
 */
const syntheticTraceGroups = computed((): TraceGroup[] => {
  const d = flameData.value;
  if (d.spans.length === 0) return [];
  return [{
    traceId: "flame",
    label: "Flame graph",
    startNs: d.startNs,
    startMs: Number(d.startNs / 1_000_000n),
    totalDurationMs: d.totalDurationMs,
    hasError: d.spans.some(s => s.hasError),
    spanCount: d.spans.length,
    maxDepth: d.maxDepth,
    spans: d.spans,
  }];
});

const {
  durationSliderValue, durationStops, searchQuery,
  activeFilters, expandedFacets, allFacets, sortedFacets, activeFilterMap,
  hasAnyFilter, matchingSpanIds,
  onDurationSlider, addFilter, removeFilter,
  toggleFacet, clearAllFilters,
} = useTraceFilters(() => syntheticTraceGroups.value);

const STATUS_LABEL: Record<number, string> = { 0: "Active", 1: "Finished", 2: "Finalized" };
const STATUS_COLOR: Record<number, string> = { 0: "text-green-600", 1: "text-gray-400", 2: "text-gray-400" };
</script>

<template>
  <div>
    <div class="mb-4">
      <h2 class="text-lg font-semibold text-gray-800">{{ content.title || content.name }}</h2>
      <div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5 text-sm text-gray-500">
        <span class="font-mono text-xs text-gray-400">{{ job.key }}</span>
        <span>started {{ timeAgo(job.start_time) }}</span>
        <span :class="STATUS_COLOR[job.status]">{{ STATUS_LABEL[job.status] }}</span>
      </div>
    </div>

    <LoadingSpinner v-if="isLoading" message="Loading traces..." class="mt-16" />

    <div v-else-if="error" class="text-sm text-red-600">
      {{ error }}
    </div>

    <div v-else-if="flameData.spans.length === 0" class="text-sm text-gray-400 mt-8 text-center">
      No trace data found for this job.
    </div>

    <div v-else class="flex gap-6">
      <TraceFilterSidebar
        :duration-stops="durationStops"
        :duration-slider-value="durationSliderValue"
        :sorted-facets="sortedFacets"
        :expanded-facets="expandedFacets"
        :active-filter-map="activeFilterMap"
        :all-facets="allFacets"
        :active-filters="activeFilters"
        :has-any-filter="hasAnyFilter"
        :search-query="searchQuery"
        @update:duration-slider-value="onDurationSlider"
        @update:search-query="searchQuery = $event"
        @toggle-facet="toggleFacet"
        @add-filter="addFilter"
        @remove-filter="removeFilter"
        @clear-all-filters="clearAllFilters"
      />

      <div class="flex-1 min-w-0">
        <FlameChart
          :spans="flameData.spans"
          :max-depth="flameData.maxDepth"
          :total-duration-ms="flameData.totalDurationMs"
          :matching-span-ids="matchingSpanIds"
          :has-any-filter="hasAnyFilter"
          @select-span="onSelectSpan"
        />

        <!-- Trace detail panel -->
        <div
          v-if="selectedTraceGroup"
          class="mt-4 border border-gray-200 bg-white rounded-lg px-4 py-3"
        >
          <div class="flex items-center justify-between mb-2">
            <div>
              <h3 class="text-sm font-semibold text-gray-800">{{ selectedTraceGroup.label }}</h3>
              <p class="text-xs text-gray-500 mt-0.5">
                {{ selectedTraceGroup.spanCount }} spans &middot;
                {{ formatDuration(selectedTraceGroup.totalDurationMs) }}
              </p>
            </div>
            <button
              class="px-2 py-1 text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
              @click="onSelectSpan(null)"
            >Close</button>
          </div>

          <FlameChart
            :spans="selectedTraceGroup.spans"
            :max-depth="selectedTraceGroup.maxDepth"
            :total-duration-ms="selectedTraceGroup.totalDurationMs"
            :matching-span-ids="matchingSpanIds"
            :has-any-filter="hasAnyFilter"
            @select-span="onDetailSelectSpan"
          />

          <SpanDetailPanel
            v-if="detailSpan"
            :span="detailSpan"
            :show-name="true"
            @close="detailSpanId = null"
          />
        </div>
      </div>
    </div>
  </div>
</template>
