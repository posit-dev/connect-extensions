<script setup lang="ts">
import { onMounted } from "vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";
import { useTracesStore } from "../stores/traces";
import type { ContentItem, Job } from "../types";

const props = defineProps<{
  content: ContentItem;
  job: Job;
}>();

const tracesStore = useTracesStore();

onMounted(() => {
  tracesStore.fetchTraces(props.content.guid, props.job.key);
});
</script>

<template>
  <div>
    <h2 class="text-lg font-semibold text-gray-700 mb-1">Traces</h2>
    <p class="text-sm text-gray-500 mb-4">Job <span class="font-mono">{{ job.key }}</span></p>

    <LoadingSpinner v-if="tracesStore.isLoading" message="Loading traces..." class="mt-16" />

    <div v-else-if="tracesStore.error" class="text-red-600 text-sm">
      {{ tracesStore.error }}
    </div>

    <pre
      v-else-if="tracesStore.traceData !== null"
      class="bg-gray-900 text-green-400 text-xs rounded-lg p-4 overflow-auto max-h-[70vh] whitespace-pre-wrap break-all"
    >{{ JSON.stringify(tracesStore.traceData, null, 2) }}</pre>

    <div v-else class="text-gray-500 text-sm">No trace data available.</div>
  </div>
</template>
