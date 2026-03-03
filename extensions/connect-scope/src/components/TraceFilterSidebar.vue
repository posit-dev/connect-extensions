<script setup lang="ts">
const props = defineProps<{
  durationStops: (number | null)[];
  durationSliderValue: number;
  sortedFacets: Array<{ key: string; total: number }>;
  expandedFacets: Set<string>;
  activeFilterMap: Map<string, Set<string>>;
  allFacets: Map<string, Map<string, number>>;
  activeFilters: Array<{ key: string; value: string }>;
  hasAnyFilter: boolean;
  searchQuery: string;
}>();

const emit = defineEmits<{
  'update:durationSliderValue': [e: Event];
  'update:searchQuery': [value: string];
  toggleFacet: [key: string];
  addFilter: [key: string, value: string];
  removeFilter: [key: string, value: string];
  clearAllFilters: [];
}>();

function durationSliderLabel(index: number): string {
  const v = props.durationStops[index];
  if (v == null) return '0ms';
  return v >= 1000 ? `${v / 1000}s` : `${v}ms`;
}

function facetValues(key: string): [string, number][] {
  const m = props.allFacets.get(key);
  return m ? [...m.entries()].sort((a, b) => b[1] - a[1]) : [];
}

function activeCountForKey(key: string): number {
  return props.activeFilters.filter(f => f.key === key).length;
}
</script>

<template>
  <aside class="w-56 shrink-0">
    <!-- Search -->
    <div class="mb-3">
      <input
        type="text"
        :value="searchQuery"
        placeholder="Filter by name..."
        class="w-full px-2 py-1.5 text-xs border border-gray-200 rounded bg-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-400 focus:border-blue-400"
        @input="emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <!-- Duration slider -->
    <div class="mb-3">
      <div class="flex items-center justify-between mb-1">
        <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Duration</h4>
        <span class="text-xs font-mono text-gray-600">&gt;= {{ durationSliderLabel(durationSliderValue) }}</span>
      </div>
      <input
        type="range"
        min="0"
        :max="durationStops.length - 1"
        step="1"
        :value="durationSliderValue"
        class="w-full h-1.5 bg-gray-200 rounded-full appearance-none cursor-pointer accent-blue-600"
        @input="emit('update:durationSliderValue', $event)"
      />
      <div class="flex justify-between mt-0.5">
        <span v-for="(_, i) in durationStops" :key="i"
              class="text-[10px] text-gray-400 tabular-nums"
              :class="i === durationSliderValue ? 'text-blue-600 font-medium' : ''"
        >{{ durationSliderLabel(i) }}</span>
      </div>
    </div>
    <!-- Filter header with clear all -->
    <div class="flex items-center justify-between mb-2">
      <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filters</h3>
      <button
        class="text-xs transition-colors"
        :class="hasAnyFilter ? 'text-blue-600 hover:text-blue-800' : 'text-gray-300 cursor-default'"
        :disabled="!hasAnyFilter"
        @click="emit('clearAllFilters')"
      >Clear all</button>
    </div>
    <!-- Facets -->
    <div v-if="sortedFacets.length > 0" class="space-y-0.5">
      <div v-for="facet in sortedFacets" :key="facet.key">
        <button
          class="w-full flex items-center gap-1.5 px-2 py-1.5 rounded text-left text-xs hover:bg-gray-50"
          @click="emit('toggleFacet', facet.key)"
        >
          <svg class="w-3 h-3 shrink-0 text-gray-400 transition-transform duration-100"
               :class="expandedFacets.has(facet.key) ? 'rotate-90' : ''"
               viewBox="0 0 6 10" fill="none"
               stroke="currentColor" stroke-width="1.5"
               stroke-linecap="round" stroke-linejoin="round">
            <polyline points="1,1 5,5 1,9" />
          </svg>
          <span class="font-mono text-gray-700 truncate flex-1">{{ facet.key }}</span>
          <span
            v-if="activeCountForKey(facet.key) > 0"
            class="ml-auto shrink-0 px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium leading-none"
          >{{ activeCountForKey(facet.key) }}</span>
        </button>
        <ul v-if="expandedFacets.has(facet.key)" class="max-h-48 overflow-y-auto pl-5 pr-1 pb-1">
          <li
            v-for="[val, count] in facetValues(facet.key)"
            :key="val"
            class="flex items-center gap-1.5 py-0.5"
          >
            <input
              type="checkbox"
              class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5 shrink-0"
              :checked="activeFilterMap.has(facet.key) && activeFilterMap.get(facet.key)!.has(val)"
              @change="activeFilterMap.has(facet.key) && activeFilterMap.get(facet.key)!.has(val) ? emit('removeFilter', facet.key, val) : emit('addFilter', facet.key, val)"
            />
            <span class="font-mono text-xs text-gray-600 truncate flex-1" :title="val">{{ val }}</span>
            <span class="shrink-0 text-xs text-gray-400 tabular-nums">{{ count }}</span>
          </li>
        </ul>
      </div>
    </div>
    <p v-else class="text-xs text-gray-400">No facets available</p>
  </aside>
</template>
