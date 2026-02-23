import { watch, onMounted, type Ref } from "vue";

interface UrlSyncOptions {
  viewMode: Ref<string>;
  traceSortOrder: Ref<string>;
  nameFilter: Ref<string | null>;
  minDurationMs: Ref<number | null>;
  searchQuery: Ref<string>;
  activeFilters: Ref<Array<{ key: string; value: string }>>;
  durationSliderValue: Ref<number>;
  durationStops: { value: (number | null)[] };
}

export function useUrlSync(opts: UrlSyncOptions) {
  function writeToUrl() {
    const url = new URL(window.location.href);
    const p = url.searchParams;

    // Clear trace-viewer params
    for (const key of [...p.keys()]) {
      if (key === 'view' || key === 'sort' || key === 'name' || key === 'minDuration' || key === 'search' || key.startsWith('filter.')) {
        p.delete(key);
      }
    }

    if (opts.viewMode.value !== 'waterfall') p.set('view', opts.viewMode.value);
    if (opts.traceSortOrder.value !== 'newest') p.set('sort', opts.traceSortOrder.value);
    if (opts.nameFilter.value != null) p.set('name', opts.nameFilter.value);
    if (opts.minDurationMs.value != null) p.set('minDuration', String(opts.minDurationMs.value));
    if (opts.searchQuery.value !== '') p.set('search', opts.searchQuery.value);

    for (const f of opts.activeFilters.value) {
      const existing = p.get(`filter.${f.key}`);
      if (existing) {
        p.set(`filter.${f.key}`, existing + ',' + f.value);
      } else {
        p.set(`filter.${f.key}`, f.value);
      }
    }

    history.replaceState({}, '', url);
  }

  function readFromUrl() {
    const p = new URLSearchParams(window.location.search);

    const view = p.get('view');
    if (view === 'timeline' || view === 'aggregate') opts.viewMode.value = view;

    const sort = p.get('sort');
    if (sort === 'slowest') opts.traceSortOrder.value = 'slowest';

    const name = p.get('name');
    if (name != null) opts.nameFilter.value = name;

    const minDuration = p.get('minDuration');
    if (minDuration != null) {
      const val = Number(minDuration);
      if (!isNaN(val)) {
        opts.minDurationMs.value = val;
        // Find closest slider position
        const stops = opts.durationStops.value;
        let closest = 0;
        for (let i = 1; i < stops.length; i++) {
          if (stops[i] != null && stops[i]! <= val) closest = i;
        }
        opts.durationSliderValue.value = closest;
      }
    }

    const search = p.get('search');
    if (search != null) opts.searchQuery.value = search;

    const filters: Array<{ key: string; value: string }> = [];
    for (const [key, value] of p.entries()) {
      if (key.startsWith('filter.')) {
        const facetKey = key.slice(7);
        for (const v of value.split(',')) {
          filters.push({ key: facetKey, value: v });
        }
      }
    }
    if (filters.length > 0) opts.activeFilters.value = filters;
  }

  onMounted(() => {
    readFromUrl();
  });

  watch(
    [opts.viewMode, opts.traceSortOrder, opts.nameFilter, opts.minDurationMs, opts.searchQuery, opts.activeFilters],
    writeToUrl,
    { deep: true }
  );
}
