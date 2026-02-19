<script setup lang="ts">
import { onMounted, onUnmounted, computed, watch } from "vue";
import LoadingSpinner from "./components/ui/LoadingSpinner.vue";
import ContentList from "./components/ContentList.vue";
import JobList from "./components/JobList.vue";
import TraceViewer from "./components/TraceViewer.vue";
import TraceDetail from "./components/TraceDetail.vue";
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

function closePanel() {
  tracesStore.selectedTraceId = null;
}

function goBackToJobs() {
  tracesStore.clear();
  jobsStore.selectedJob = null;
}

function goBackToContent() {
  tracesStore.clear();
  jobsStore.clearSelection();
  contentStore.clearSelection();
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape") closePanel();
}

onMounted(async () => {
  window.addEventListener("keydown", handleKeydown);

  await userStore.fetchCurrentUser();

  const params = new URLSearchParams(window.location.search);
  const contentGuid = params.get('content');
  const jobKey = params.get('job');

  if (!contentGuid) return;

  await contentStore.fetchContent();
  const content = contentStore.items.find(c => c.guid === contentGuid);
  if (!content) return;
  contentStore.selectContent(content);

  if (!jobKey) return;

  await jobsStore.fetchJobs(contentGuid);
  const job = jobsStore.jobs.find(j => j.key === jobKey);
  if (!job) return;
  jobsStore.selectJob(job);

  const traceId = params.get('trace');
  if (traceId) tracesStore.selectedTraceId = traceId;
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
});

watch(() => contentStore.selectedContent, (content) => {
  const url = new URL(window.location.href);
  if (content) {
    url.searchParams.set('content', content.guid);
  } else {
    url.searchParams.delete('content');
    url.searchParams.delete('job');
  }
  history.replaceState({}, '', url);
});

watch(() => jobsStore.selectedJob, (job) => {
  const url = new URL(window.location.href);
  if (job) {
    url.searchParams.set('job', job.key);
  } else {
    url.searchParams.delete('job');
    url.searchParams.delete('trace');
  }
  history.replaceState({}, '', url);
});

watch(() => tracesStore.selectedTraceId, (traceId) => {
  const url = new URL(window.location.href);
  if (traceId) {
    url.searchParams.set('trace', traceId);
  } else {
    url.searchParams.delete('trace');
  }
  history.replaceState({}, '', url);
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

      <div v-else-if="userStore.user" :class="view === 'traces' ? '' : 'max-w-2xl mx-auto'">
        <!-- Breadcrumb -->
        <nav v-if="view !== 'content'" class="flex items-center gap-1 text-sm mb-6 text-gray-500">
          <button class="hover:text-blue-600 hover:underline" @click="goBackToContent">Content</button>
          <span>/</span>
          <template v-if="view === 'jobs'">
            <span class="text-gray-800 font-medium">{{ contentStore.selectedContent?.title || contentStore.selectedContent?.name }}</span>
          </template>
          <template v-else-if="view === 'traces'">
            <button class="hover:text-blue-600 hover:underline" @click="goBackToJobs">
              {{ contentStore.selectedContent?.title || contentStore.selectedContent?.name }}
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

    <!-- Backdrop -->
    <Transition name="fade">
      <div
        v-if="tracesStore.selectedTraceId"
        class="fixed inset-0 bg-black/25 z-40"
        @click="closePanel"
      />
    </Transition>

    <!-- Detail panel -->
    <Transition name="slide-right">
      <div
        v-if="tracesStore.selectedTraceId && contentStore.selectedContent && jobsStore.selectedJob"
        class="fixed inset-y-0 right-0 w-[62%] bg-white shadow-2xl z-50 flex flex-col"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 shrink-0">
          <span class="text-sm text-gray-500">Trace Detail</span>
          <button
            class="text-gray-400 hover:text-gray-700 text-xl leading-none"
            @click="closePanel"
          >×</button>
        </div>
        <div class="flex-1 overflow-y-auto p-6">
          <TraceDetail
            :content="contentStore.selectedContent"
            :job="jobsStore.selectedJob"
            :trace-id="tracesStore.selectedTraceId"
          />
        </div>
      </div>
    </Transition>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.25s ease;
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
