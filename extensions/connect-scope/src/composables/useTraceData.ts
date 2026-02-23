import { computed, onMounted } from "vue";
import { useTracesStore } from "../stores/traces";
import type { ContentItem, Job, OtlpRecord, OtlpSpan, TraceGroup } from "../types";
import { buildTraceGroup } from "../utils/trace-builder";

export function useTraceData(content: ContentItem, job: Job) {
  const tracesStore = useTracesStore();

  onMounted(() => {
    tracesStore.fetchTraces(content.guid, job.key);
  });

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
    traceGroups.value.reduce((m, g) => Math.max(m, g.totalDurationMs), 1)
  );

  const isLoading = computed(() => tracesStore.isLoading);
  const error = computed(() => tracesStore.error);

  function retry() {
    tracesStore.fetchTraces(content.guid, job.key);
  }

  return { traceGroups, maxTraceDurationMs, isLoading, error, retry };
}
