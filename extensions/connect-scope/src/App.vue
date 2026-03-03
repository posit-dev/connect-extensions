<script setup lang="ts">
import { onMounted, computed, watch, ref } from "vue";
import LoadingSpinner from "./components/ui/LoadingSpinner.vue";
import ContentList from "./components/ContentList.vue";
import FlameGraphPage from "./components/FlameGraphPage.vue";
import { useUserStore } from "./stores/user";
import { useContentStore } from "./stores/content";
import { useJobsStore } from "./stores/jobs";

const userStore = useUserStore();
const contentStore = useContentStore();
const jobsStore = useJobsStore();

const resolvingDeepLink = ref(false);

const view = computed(() => {
  if (resolvingDeepLink.value) return "loading";
  if (contentStore.selectedContent) return "flamegraph";
  return "content";
});

function goBackToContent() {
  jobsStore.clearSelection();
  contentStore.clearSelection();
}

onMounted(async () => {
  const params = new URLSearchParams(window.location.search);
  const contentGuid = params.get('content');

  if (contentGuid) {
    resolvingDeepLink.value = true;
  }

  await userStore.fetchCurrentUser();

  if (!contentGuid) return;

  const jobKey = params.get('job');

  await contentStore.fetchContent();
  const content = contentStore.items.find(c => c.guid === contentGuid);
  if (!content) {
    resolvingDeepLink.value = false;
    return;
  }
  contentStore.selectContent(content);

  if (jobKey) {
    await jobsStore.fetchJobs(contentGuid);
    const job = jobsStore.jobs.find(j => j.key === jobKey);
    if (job) jobsStore.selectJob(job);
  }

  resolvingDeepLink.value = false;
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
        v-if="userStore.isLoading || view === 'loading'"
        message="Loading..."
        class="mt-16"
      />

      <div v-else-if="userStore.error" class="text-red-600 text-sm">
        {{ userStore.error }}
      </div>

      <div v-else-if="userStore.user" :class="view === 'flamegraph' ? '' : 'max-w-2xl mx-auto'">
        <!-- Breadcrumb -->
        <nav v-if="view !== 'content'" class="flex items-center gap-1 text-sm mb-6 text-gray-500">
          <button
            class="hover:text-blue-600 hover:underline"
            @click="goBackToContent"
          >
            Content
          </button>
          <span>/</span>
          <span class="text-gray-800 font-medium">{{ contentStore.selectedContent?.title || contentStore.selectedContent?.name }}</span>
        </nav>

        <!-- Views -->
        <ContentList v-if="view === 'content'" />

        <FlameGraphPage
          v-else-if="view === 'flamegraph' && contentStore.selectedContent"
          :content="contentStore.selectedContent"
        />
      </div>
    </main>
  </div>
</template>
