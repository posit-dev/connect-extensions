<script setup lang="ts">
import { onMounted, computed } from "vue";
import LoadingSpinner from "./components/ui/LoadingSpinner.vue";
import ContentList from "./components/ContentList.vue";
import JobList from "./components/JobList.vue";
import TraceViewer from "./components/TraceViewer.vue";
import { useUserStore } from "./stores/user";
import { useContentStore } from "./stores/content";
import { useJobsStore } from "./stores/jobs";
import { useTracesStore } from "./stores/traces";

const userStore = useUserStore();
const contentStore = useContentStore();
const jobsStore = useJobsStore();
const tracesStore = useTracesStore();

const view = computed(() => {
  if (contentStore.selectedContent && jobsStore.selectedJob) return "traces";
  if (contentStore.selectedContent) return "jobs";
  return "content";
});

function goBackToJobs() {
  tracesStore.clear();
  jobsStore.selectedJob = null;
}

function goBackToContent() {
  tracesStore.clear();
  jobsStore.clearSelection();
  contentStore.clearSelection();
}

onMounted(() => {
  userStore.fetchCurrentUser();
});
</script>

<template>
  <div class="flex flex-col min-h-svh bg-gray-100">
    <header class="bg-white border-b border-gray-200 px-6 py-4">
      <h1 class="text-xl font-semibold text-gray-800">Connect Scope</h1>
    </header>

    <main class="flex-1 p-6">
      <LoadingSpinner
        v-if="userStore.isLoading"
        message="Loading..."
        class="mt-16"
      />

      <div v-else-if="userStore.error" class="text-red-600 text-sm">
        {{ userStore.error }}
      </div>

      <div v-else-if="userStore.user" class="max-w-2xl mx-auto">
        <!-- Breadcrumb -->
        <nav v-if="view !== 'content'" class="flex items-center gap-1 text-sm mb-6 text-gray-500">
          <button
            class="hover:text-blue-600 hover:underline"
            @click="goBackToContent"
          >
            Content
          </button>
          <span>/</span>
          <template v-if="view === 'jobs'">
            <span class="text-gray-800 font-medium">Jobs</span>
          </template>
          <template v-else>
            <button
              class="hover:text-blue-600 hover:underline"
              @click="goBackToJobs"
            >
              Jobs
            </button>
            <span>/</span>
            <span class="text-gray-800 font-medium">Traces</span>
          </template>
        </nav>

        <!-- Views -->
        <ContentList v-if="view === 'content'" />

        <JobList
          v-else-if="view === 'jobs' && contentStore.selectedContent"
          :content="contentStore.selectedContent"
        />

        <TraceViewer
          v-else-if="view === 'traces' && contentStore.selectedContent && jobsStore.selectedJob"
          :content="contentStore.selectedContent"
          :job="jobsStore.selectedJob"
        />
      </div>
    </main>
  </div>
</template>
