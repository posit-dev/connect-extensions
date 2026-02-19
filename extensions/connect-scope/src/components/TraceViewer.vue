<script setup lang="ts">
import { computed, onMounted, reactive } from "vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";
import { useTracesStore } from "../stores/traces";
import type { ContentItem, Job, OtlpRecord, OtlpSpan, FlatSpan } from "../types";

const props = defineProps<{
  content: ContentItem;
  job: Job;
}>();

const tracesStore = useTracesStore();

onMounted(() => {
  tracesStore.fetchTraces(props.content.guid, props.job.key);
});

interface TraceGroup {
  traceId: string;
  label: string;
  startNs: bigint;
  startMs: number;
  totalDurationMs: number;
  hasError: boolean;
  spanCount: number;
  spans: FlatSpan[];
}

function buildTraceGroup(traceId: string, spans: OtlpSpan[]): TraceGroup {
  const byId = new Map<string, OtlpSpan>();
  for (const s of spans) {
    if (s.spanId) byId.set(s.spanId, s);
  }

  let startNs = BigInt("9".repeat(20));
  let endNs = 0n;
  for (const s of spans) {
    const t0 = BigInt(s.startTimeUnixNano ?? "0");
    const t1 = BigInt(s.endTimeUnixNano ?? s.startTimeUnixNano ?? "0");
    if (t0 < startNs) startNs = t0;
    if (t1 > endNs) endNs = t1;
  }
  const durationNs = endNs - startNs || 1n;

  const flat: FlatSpan[] = [];

  const visit = (s: OtlpSpan, depth: number) => {
    const sNs = BigInt(s.startTimeUnixNano ?? "0");
    const eNs = s.endTimeUnixNano != null ? BigInt(s.endTimeUnixNano) : null;
    const durationMs = eNs != null ? Number(eNs - sNs) / 1_000_000 : null;
    const offsetPct = Number((sNs - startNs) * 10000n / durationNs) / 100;
    const widthPct = eNs != null
      ? Number((eNs - sNs) * 10000n / durationNs) / 100
      : 0;

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
      isSlow: false, // set in post-pass below
    });

    const children = spans
      .filter(c => c.spanId && c.parentSpanId === s.spanId)
      .sort((a, b) => (BigInt(a.startTimeUnixNano ?? "0") < BigInt(b.startTimeUnixNano ?? "0") ? -1 : 1));
    for (const child of children) visit(child, depth + 1);
  };

  const roots = spans
    .filter(s => !s.parentSpanId || !byId.has(s.parentSpanId))
    .sort((a, b) => (BigInt(a.startTimeUnixNano ?? "0") < BigInt(b.startTimeUnixNano ?? "0") ? -1 : 1));
  for (const root of roots) visit(root, 0);

  // Mark slow spans: compare non-root spans against their within-trace median
  const childDurations = flat
    .filter(s => s.depth > 0 && s.durationMs != null)
    .map(s => s.durationMs as number)
    .sort((a, b) => a - b);
  if (childDurations.length > 0) {
    const mid = Math.floor(childDurations.length / 2);
    const spanMedian = childDurations.length % 2 === 0
      ? (childDurations[mid - 1] + childDurations[mid]) / 2
      : childDurations[mid];
    for (const s of flat) {
      if (s.depth > 0 && s.durationMs != null && s.durationMs > 1.5 * spanMedian) {
        s.isSlow = true;
      }
    }
  }

  return {
    traceId,
    label: roots[0]?.name ?? "Trace",
    startNs,
    startMs: Number(startNs / 1_000_000n),
    totalDurationMs: Number(endNs - startNs) / 1_000_000,
    hasError: flat.some(s => s.hasError),
    spanCount: flat.length,
    spans: flat,
  };
}

const traceGroups = computed((): TraceGroup[] => {
  const records = tracesStore.traceData as OtlpRecord[] | null;
  if (!records) return [];

  const rawSpans: OtlpSpan[] = records
    .flatMap(r => r.resourceSpans ?? [])
    .flatMap(rs => rs.scopeSpans ?? [])
    .flatMap(ss => ss.spans ?? []);

  if (rawSpans.length === 0) return [];

  const byTrace = new Map<string, OtlpSpan[]>();
  for (const s of rawSpans) {
    const tid = s.traceId ?? "unknown";
    const group = byTrace.get(tid);
    if (group) group.push(s);
    else byTrace.set(tid, [s]);
  }

  const groups = Array.from(byTrace.entries()).map(([tid, spans]) =>
    buildTraceGroup(tid, spans)
  );

  return groups.sort((a, b) => (a.startNs > b.startNs ? -1 : 1));
});

const maxTraceDurationMs = computed(() =>
  Math.max(1, ...traceGroups.value.map(g => g.totalDurationMs))
);

const medianDurationMs = computed(() => {
  const sorted = traceGroups.value.map(g => g.totalDurationMs).sort((a, b) => a - b);
  if (sorted.length === 0) return 0;
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
});

// All traces collapsed by default
const expanded = reactive(new Set<string>());

function toggle(traceId: string) {
  if (expanded.has(traceId)) expanded.delete(traceId);
  else expanded.add(traceId);
}

function formatTime(ms: number): string {
  return new Date(ms).toLocaleString();
}

function formatDuration(ms: number): string {
  if (ms >= 1000) return (ms / 1000).toFixed(2) + " s";
  return ms.toFixed(1) + " ms";
}

function timeAgo(isoString: string): string {
  const secs = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const STATUS_LABEL: Record<number, string> = { 0: "Active", 1: "Finished", 2: "Finalized" };
const STATUS_COLOR: Record<number, string> = {
  0: "text-green-600",
  1: "text-gray-400",
  2: "text-gray-400",
};
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

    <LoadingSpinner v-if="tracesStore.isLoading" message="Loading..." class="mt-16" />

    <div v-else-if="tracesStore.error" class="text-red-600 text-sm">
      {{ tracesStore.error }}
    </div>

    <div v-else-if="traceGroups.length">
      <p class="text-xs text-gray-400 mb-2">{{ traceGroups.length }} traces</p>

      <div v-for="group in traceGroups" :key="group.traceId" class="mb-0.5">

        <!-- Header row — same layout as span rows -->
        <div class="flex items-center gap-2 py-0.5 rounded cursor-pointer select-none hover:bg-gray-50"
             @click="toggle(group.traceId)">
          <!-- Chevron + name + timestamp -->
          <div class="w-64 shrink-0 flex items-center gap-1.5 min-w-0 pl-1">
            <svg class="w-3 h-3 shrink-0 text-gray-400 transition-transform duration-100"
                 :class="expanded.has(group.traceId) ? 'rotate-90' : ''"
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
          <!-- Summary bar: width proportional across all traces -->
          <div class="relative flex-1 h-5 bg-gray-100 rounded overflow-hidden">
            <div class="absolute inset-y-0 left-0 rounded"
                 :class="group.totalDurationMs > 1.5 * medianDurationMs ? 'bg-amber-400' : 'bg-blue-400'"
                 :style="{ width: `${(group.totalDurationMs / maxTraceDurationMs) * 100}%` }">
            </div>
          </div>
          <!-- Total duration -->
          <div class="w-16 text-right text-xs text-gray-600 shrink-0 font-mono">
            {{ formatDuration(group.totalDurationMs) }}
          </div>
        </div>

        <!-- Span rows (collapsed by default) -->
        <ul v-if="expanded.has(group.traceId)" class="space-y-0.5 mt-0.5">
          <li v-for="span in group.spans" :key="span.spanId"
              class="flex items-center gap-2 py-0.5">
            <!-- Name, indented by depth -->
            <div class="w-64 shrink-0 flex items-center min-w-0"
                 :style="{ paddingLeft: `${span.depth * 16 + 4}px` }">
              <span class="text-gray-300 mr-1 shrink-0 text-xs leading-none">└</span>
              <span class="text-sm text-gray-600 truncate" :title="span.name">{{ span.name }}</span>
            </div>
            <!-- Timeline bar: position + width relative to this trace's duration -->
            <div class="relative flex-1 h-5 bg-gray-100 rounded overflow-hidden">
              <div class="absolute inset-y-0 rounded"
                   :class="span.hasError ? 'bg-red-300' : span.isSlow ? 'bg-amber-300' : 'bg-blue-300'"
                   :style="{ left: `${span.offsetPct}%`, width: `${Math.max(span.widthPct, 0.5)}%` }">
              </div>
            </div>
            <!-- Duration -->
            <div class="w-16 text-right text-xs text-gray-500 shrink-0 font-mono">
              {{ span.durationMs != null ? span.durationMs.toFixed(1) + ' ms' : '—' }}
            </div>
          </li>
        </ul>

      </div>
    </div>

    <div v-else class="text-gray-500 text-sm">No trace data available.</div>
  </div>
</template>
