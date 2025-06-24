<script setup lang="ts">
import VulnerabilityChecker from "./components/VulnerabilityChecker.vue";
import ContentList from "./components/ContentList.vue";
import PoweredByFooter from "./components/PoweredByFooter.vue";
import { useVulnsStore } from "./stores/vulns";
import { useContentStore } from "./stores/content";
import LoadingSpinner from "./components/ui/LoadingSpinner.vue";

const vulnStore = useVulnsStore();
const contentStore = useContentStore();

vulnStore.fetchVulns();
contentStore.fetchContentList();

const loadingMessage = "Fetching content and vulnerabilities...";
</script>

<template>
  <div class="flex flex-col min-h-svh">
    <LoadingSpinner
      v-if="vulnStore.isLoading || contentStore.isLoading"
      class="grow bg-gray-100"
      :message="loadingMessage"
    />
    <main v-else class="flex-1 p-4 md:p-8 bg-gray-100">
      <div class="max-w-4xl mx-auto">
        <VulnerabilityChecker v-if="contentStore.currentContentId" />
        <ContentList v-else />
      </div>
    </main>

    <PoweredByFooter />
  </div>
</template>
