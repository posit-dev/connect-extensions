<script setup lang="ts">
import { onMounted } from "vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";
import { useJobsStore } from "../stores/jobs";
import type { ContentItem } from "../types";

const props = defineProps<{
  content: ContentItem;
}>();

const jobsStore = useJobsStore();

const STATUS_LABELS: Record<number, string> = {
  0: "Active",
  1: "Finished",
  2: "Finalized",
};

const STATUS_CLASSES: Record<number, string> = {
  0: "bg-green-100 text-green-700",
  1: "bg-gray-100 text-gray-600",
  2: "bg-blue-100 text-blue-700",
};

onMounted(() => {
  jobsStore.fetchJobs(props.content.guid);
});
</script>

<template>
  <div>
    <h2 class="text-lg font-semibold text-gray-700 mb-4">
      Jobs for <span class="text-gray-900">{{ content.title || content.name }}</span>
    </h2>

    <LoadingSpinner v-if="jobsStore.isLoading" message="Loading jobs..." class="mt-16" />

    <div v-else-if="jobsStore.error" class="text-red-600 text-sm">
      {{ jobsStore.error }}
    </div>

    <div v-else-if="jobsStore.jobs.length === 0" class="text-gray-500 text-sm">
      No jobs found for this content.
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="job in jobsStore.jobs"
        :key="job.id"
        class="bg-white rounded-lg border border-gray-200 px-4 py-3 cursor-pointer hover:border-blue-400 hover:shadow-sm transition-all"
        @click="jobsStore.selectJob(job)"
      >
        <div class="flex items-center justify-between">
          <p class="font-medium text-gray-800 font-mono text-sm">{{ job.key }}</p>
          <span
            class="text-xs font-medium px-2 py-0.5 rounded-full"
            :class="STATUS_CLASSES[job.status]"
          >
            {{ STATUS_LABELS[job.status] }}
          </span>
        </div>
        <p class="text-xs text-gray-500 mt-0.5">{{ job.tag }} · {{ job.hostname }}</p>
      </li>
    </ul>
  </div>
</template>
