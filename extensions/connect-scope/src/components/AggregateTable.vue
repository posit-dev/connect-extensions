<script setup lang="ts">
import type { SpanAggregate, AggSortKey } from "../types";
import { formatDuration } from "../utils/formatting";

defineProps<{
  aggregates: SpanAggregate[];
  sortKey: AggSortKey;
  sortAsc: boolean;
  summaryStats: { totalTraces: number; avgDuration: number; errorRate: number };
}>();

defineEmits<{
  toggleSort: [key: AggSortKey];
  drillToOperation: [name: string];
}>();
</script>

<template>
  <div class="border border-gray-200 rounded-lg overflow-hidden">
    <!-- Summary stats -->
    <div class="flex items-center gap-4 px-3 py-2 bg-gray-50 border-b border-gray-200 text-xs">
      <span class="text-gray-500"><span class="font-semibold text-gray-700">{{ summaryStats.totalTraces }}</span> traces</span>
      <span class="text-gray-500">avg <span class="font-mono font-semibold text-gray-700">{{ formatDuration(summaryStats.avgDuration) }}</span></span>
      <span :class="summaryStats.errorRate > 0 ? 'text-red-600' : 'text-gray-500'">
        <span class="font-semibold">{{ summaryStats.errorRate.toFixed(1) }}%</span> errors
      </span>
    </div>
    <table class="w-full text-xs">
      <thead>
        <tr class="bg-gray-50 text-gray-500 uppercase tracking-wide">
          <th class="text-left px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="$emit('toggleSort', 'name')">
            Operation<span v-if="sortKey === 'name'" class="ml-0.5">{{ sortAsc ? '↑' : '↓' }}</span>
          </th>
          <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="$emit('toggleSort', 'count')">
            Count<span v-if="sortKey === 'count'" class="ml-0.5">{{ sortAsc ? '↑' : '↓' }}</span>
          </th>
          <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="$emit('toggleSort', 'avg')">
            Avg<span v-if="sortKey === 'avg'" class="ml-0.5">{{ sortAsc ? '↑' : '↓' }}</span>
          </th>
          <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="$emit('toggleSort', 'p50')">
            p50<span v-if="sortKey === 'p50'" class="ml-0.5">{{ sortAsc ? '↑' : '↓' }}</span>
          </th>
          <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="$emit('toggleSort', 'p95')">
            p95<span v-if="sortKey === 'p95'" class="ml-0.5">{{ sortAsc ? '↑' : '↓' }}</span>
          </th>
          <th class="text-right px-3 py-2 font-semibold cursor-pointer select-none hover:text-gray-700" @click="$emit('toggleSort', 'max')">
            Max<span v-if="sortKey === 'max'" class="ml-0.5">{{ sortAsc ? '↑' : '↓' }}</span>
          </th>
          <th class="text-right px-3 py-2 font-semibold">% Total</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="agg in aggregates"
          :key="agg.name"
          class="border-t border-gray-100 hover:bg-blue-50 cursor-pointer group"
          @click="$emit('drillToOperation', agg.name)"
        >
          <td class="px-3 py-1.5 font-mono text-gray-800">
            <span class="flex items-center gap-1">
              {{ agg.name }}
              <svg class="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
              </svg>
            </span>
          </td>
          <td class="px-3 py-1.5 text-right tabular-nums text-gray-600">{{ agg.count }}</td>
          <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ formatDuration(agg.avg) }}</td>
          <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ formatDuration(agg.p50) }}</td>
          <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ formatDuration(agg.p95) }}</td>
          <td class="px-3 py-1.5 text-right tabular-nums font-mono text-gray-600">{{ formatDuration(agg.max) }}</td>
          <td class="px-3 py-1.5 text-right">
            <div class="flex items-center gap-1.5 justify-end">
              <div class="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div class="h-full bg-blue-400 rounded-full" :style="{ width: `${agg.pctOfTotal}%` }"></div>
              </div>
              <span class="tabular-nums text-gray-500 w-10 text-right">{{ agg.pctOfTotal.toFixed(1) }}%</span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="aggregates.length === 0" class="px-3 py-4 text-gray-400 text-center text-sm">No matching spans</p>
  </div>
</template>
