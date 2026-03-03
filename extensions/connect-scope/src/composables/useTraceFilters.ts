import { computed, reactive, ref } from "vue";
import type { FlatSpan, TraceGroup } from "../types";
import { otlpValue } from "../utils/trace-builder";

export function useTraceFilters(traceGroups: () => TraceGroup[]) {
  const traceSortOrder = ref<'newest' | 'slowest'>('newest');
  const minDurationMs = ref<number | null>(null);
  const durationSliderValue = ref(0);
  const nameFilter = ref<string | null>(null);
  const searchQuery = ref('');
  const activeFilters = ref<Array<{ key: string; value: string }>>([]);
  const expandedFacets = reactive(new Set<string>());

  // Data-driven duration stops based on actual span percentiles
  const durationStops = computed((): (number | null)[] => {
    const durations: number[] = [];
    for (const g of traceGroups()) {
      for (const s of g.spans) {
        if (s.durationMs != null) durations.push(s.durationMs);
      }
    }
    if (durations.length === 0) return [null, 10, 50, 100, 500, 1000, 10000];
    durations.sort((a, b) => a - b);
    const pct = (p: number) => {
      const idx = Math.ceil((p / 100) * durations.length) - 1;
      return durations[Math.max(0, idx)]!;
    };
    const raw = [pct(10), pct(25), pct(50), pct(75), pct(90), pct(99)];
    // Deduplicate and round to nice values
    const rounded = [...new Set(raw.map(v => {
      if (v < 1) return Math.round(v * 10) / 10;
      if (v < 10) return Math.round(v);
      if (v < 100) return Math.round(v / 5) * 5;
      if (v < 1000) return Math.round(v / 50) * 50;
      return Math.round(v / 100) * 100;
    }))];
    return [null, ...rounded];
  });

  function durationSliderLabel(index: number): string {
    const v = durationStops.value[index];
    if (v == null) return '0ms';
    return v >= 1000 ? `${v / 1000}s` : `${v}ms`;
  }

  function onDurationSlider(e: Event) {
    const val = Number((e.target as HTMLInputElement).value);
    durationSliderValue.value = val;
    minDurationMs.value = durationStops.value[val] ?? null;
  }

  // Facet computeds
  const allFacets = computed((): Map<string, Map<string, number>> => {
    const facets = new Map<string, Map<string, number>>();
    for (const group of traceGroups()) {
      for (const span of group.spans) {
        for (const attr of span.attributes) {
          const val = otlpValue(attr.value);
          if (!facets.has(attr.key)) facets.set(attr.key, new Map());
          const m = facets.get(attr.key)!;
          m.set(val, (m.get(val) ?? 0) + 1);
        }
      }
    }
    return facets;
  });

  const sortedFacets = computed(() =>
    [...allFacets.value.entries()]
      .map(([key, m]) => ({ key, total: [...m.values()].reduce((s, c) => s + c, 0) }))
      .sort((a, b) => b.total - a.total)
  );

  const activeFilterMap = computed((): Map<string, Set<string>> => {
    const m = new Map<string, Set<string>>();
    for (const f of activeFilters.value) {
      const s = m.get(f.key);
      if (s) s.add(f.value);
      else m.set(f.key, new Set([f.value]));
    }
    return m;
  });

  const hasAnyFilter = computed(() =>
    activeFilters.value.length > 0 || minDurationMs.value != null || nameFilter.value != null || searchQuery.value !== ''
  );

  function spanMatchesFilters(span: FlatSpan, filterMap: Map<string, Set<string>>): boolean {
    if (nameFilter.value != null && span.name !== nameFilter.value) return false;
    if (searchQuery.value !== '' && !span.name.toLowerCase().includes(searchQuery.value.toLowerCase())) return false;
    const minDur = minDurationMs.value;
    if (minDur != null && (span.durationMs === null || span.durationMs < minDur)) return false;
    for (const [key, allowed] of filterMap) {
      if (!span.attributes.some(a => a.key === key && allowed.has(otlpValue(a.value)))) return false;
    }
    return true;
  }

  const filteredTraceGroups = computed((): TraceGroup[] => {
    if (!hasAnyFilter.value) return traceGroups();
    const filterMap = activeFilterMap.value;
    return traceGroups()
      .filter(g => g.spans.some(span => spanMatchesFilters(span, filterMap)));
  });

  const sortedTraceGroups = computed((): TraceGroup[] => {
    const list = [...filteredTraceGroups.value];
    if (traceSortOrder.value === 'slowest') {
      return list.sort((a, b) => b.totalDurationMs - a.totalDurationMs);
    }
    return list.sort((a, b) => (a.startNs > b.startNs ? -1 : 1));
  });

  const matchingSpanIds = computed((): Set<string> => {
    if (!hasAnyFilter.value) return new Set();
    const filterMap = activeFilterMap.value;
    const ids = new Set<string>();
    for (const g of filteredTraceGroups.value) {
      for (const span of g.spans) {
        if (spanMatchesFilters(span, filterMap)) ids.add(span.spanId);
      }
    }
    return ids;
  });

  function isSpanDimmed(spanId: string): boolean {
    return hasAnyFilter.value && !matchingSpanIds.value.has(spanId);
  }

  function addFilter(key: string, value: string) {
    if (!activeFilters.value.some(f => f.key === key && f.value === value))
      activeFilters.value = [...activeFilters.value, { key, value }];
  }

  function removeFilter(key: string, value: string) {
    activeFilters.value = activeFilters.value.filter(f => !(f.key === key && f.value === value));
  }

  function toggleFacet(key: string) {
    if (expandedFacets.has(key)) expandedFacets.delete(key);
    else expandedFacets.add(key);
  }

  function facetValues(key: string): [string, number][] {
    const m = allFacets.value.get(key);
    return m ? [...m.entries()].sort((a, b) => b[1] - a[1]) : [];
  }

  function activeCountForKey(key: string): number {
    return activeFilters.value.filter(f => f.key === key).length;
  }

  function clearAllFilters() {
    activeFilters.value = [];
    minDurationMs.value = null;
    durationSliderValue.value = 0;
    nameFilter.value = null;
    searchQuery.value = '';
  }

  function drillToOperation(name: string, setViewMode: (mode: string) => void) {
    nameFilter.value = name;
    setViewMode('waterfall');
  }

  return {
    traceSortOrder,
    minDurationMs,
    durationSliderValue,
    durationStops,
    nameFilter,
    searchQuery,
    activeFilters,
    expandedFacets,
    allFacets,
    sortedFacets,
    activeFilterMap,
    hasAnyFilter,
    filteredTraceGroups,
    sortedTraceGroups,
    matchingSpanIds,
    isSpanDimmed,
    durationSliderLabel,
    onDurationSlider,
    spanMatchesFilters,
    addFilter,
    removeFilter,
    toggleFacet,
    facetValues,
    activeCountForKey,
    clearAllFilters,
    drillToOperation,
  };
}
