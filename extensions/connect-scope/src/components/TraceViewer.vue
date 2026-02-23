<script setup lang="ts">
import { ref, watch } from "vue";
import type { ContentItem, Job } from "../types";
import { timeAgo } from "../utils/formatting";
import { useTraceData } from "../composables/useTraceData";
import { useTraceFilters } from "../composables/useTraceFilters";
import { useTraceExpansion } from "../composables/useTraceExpansion";
import { useAggregateView } from "../composables/useAggregateView";
import { useUrlSync } from "../composables/useUrlSync";
import TraceSkeleton from "./ui/TraceSkeleton.vue";
import EmptyTraceState from "./EmptyTraceState.vue";
import TraceFilterSidebar from "./TraceFilterSidebar.vue";
import TraceViewControls from "./TraceViewControls.vue";
import AggregateTable from "./AggregateTable.vue";
import TraceRow from "./TraceRow.vue";
import WaterfallSpanList from "./WaterfallSpanList.vue";
import TimelineChart from "./TimelineChart.vue";

const props = defineProps<{
  content: ContentItem;
  job: Job;
}>();

const viewMode = ref<'waterfall' | 'timeline' | 'aggregate'>('waterfall');

const { traceGroups, maxTraceDurationMs, isLoading, error, retry } = useTraceData(props.content, props.job);

const {
  traceSortOrder, durationSliderValue, durationStops, nameFilter, searchQuery,
  activeFilters, expandedFacets, allFacets, sortedFacets, activeFilterMap,
  hasAnyFilter, sortedTraceGroups, matchingSpanIds,
  onDurationSlider, addFilter, removeFilter,
  toggleFacet, clearAllFilters, drillToOperation,
  filteredTraceGroups, minDurationMs,
} = useTraceFilters(() => traceGroups.value);

const {
  expanded, expandedSpans, toggle, allExpanded, toggleAllTraces, toggleSpan, autoExpandFirst,
} = useTraceExpansion(() => sortedTraceGroups.value);

const {
  aggSortKey, aggSortAsc, toggleAggSort, spanAggregates, traceSummaryStats,
} = useAggregateView(() => filteredTraceGroups.value);

watch(sortedTraceGroups, () => { autoExpandFirst(); }, { once: true });

useUrlSync({
  viewMode, traceSortOrder, nameFilter, minDurationMs,
  searchQuery, activeFilters, durationSliderValue, durationStops,
});

function handleDrillToOperation(name: string) {
  drillToOperation(name, (mode: string) => { viewMode.value = mode as typeof viewMode.value; });
}

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

    <TraceSkeleton v-if="isLoading" />

    <EmptyTraceState v-else-if="error" :has-error="true" :error-message="error" @retry="retry" />

    <div v-else-if="traceGroups.length">
      <div class="flex gap-6">
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
          <TraceViewControls
            :view-mode="viewMode"
            :trace-sort-order="traceSortOrder"
            :name-filter="nameFilter"
            :total-traces="traceGroups.length"
            :visible-traces="sortedTraceGroups.length"
            :has-any-filter="hasAnyFilter"
            :all-expanded="allExpanded"
            @update:view-mode="viewMode = $event as typeof viewMode"
            @update:trace-sort-order="traceSortOrder = $event as typeof traceSortOrder"
            @update:name-filter="nameFilter = $event"
            @toggle-all-traces="toggleAllTraces"
          />

          <AggregateTable
            v-if="viewMode === 'aggregate'"
            :aggregates="spanAggregates"
            :sort-key="aggSortKey"
            :sort-asc="aggSortAsc"
            :summary-stats="traceSummaryStats"
            @toggle-sort="toggleAggSort"
            @drill-to-operation="handleDrillToOperation"
          />

          <template v-else>
            <div
              v-for="group in sortedTraceGroups"
              :key="group.traceId"
              class="rounded-lg transition-all"
              :class="expanded.has(group.traceId)
                ? 'mb-2 border border-gray-200 bg-white px-3 py-2'
                : 'mb-0.5 px-1'"
            >
              <TraceRow
                :group="group"
                :is-expanded="expanded.has(group.traceId)"
                :max-trace-duration-ms="maxTraceDurationMs"
                @toggle="toggle(group.traceId)"
              />

              <WaterfallSpanList
                v-if="expanded.has(group.traceId) && viewMode === 'waterfall'"
                :spans="group.spans"
                :expanded-spans="expandedSpans"
                :matching-span-ids="matchingSpanIds"
                :has-any-filter="hasAnyFilter"
                @toggle-span="toggleSpan"
              />

              <TimelineChart
                v-if="expanded.has(group.traceId) && viewMode === 'timeline'"
                :spans="group.spans"
                :max-depth="group.maxDepth"
                :expanded-spans="expandedSpans"
                :matching-span-ids="matchingSpanIds"
                :has-any-filter="hasAnyFilter"
                @toggle-span="toggleSpan"
              />
            </div>
          </template>
        </div>
      </div>
    </div>

    <EmptyTraceState v-else :has-error="false" @retry="retry" />
  </div>
</template>
