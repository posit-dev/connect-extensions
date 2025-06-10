<script setup lang="ts">
import VulnerabilityChecker from "./components/VulnerabilityChecker.vue";
import ContentList from "./components/ContentList.vue";
import PoweredByFooter from "./components/PoweredByFooter.vue";
import { useVulnsStore } from "./stores/vulns";
import { useContentStore } from "./stores/content";

const vulnStore = useVulnsStore();
const contentStore = useContentStore();

if (!vulnStore.isFetched && !vulnStore.isLoading) {
  vulnStore.fetchVulns();
}
</script>

<template>
  <div class="flex flex-col min-h-svh">
    <main class="flex-1 p-4 md:p-8 bg-gray-100">
      <div class="max-w-4xl mx-auto">
        <!-- Toggle between list and detail view -->
        <ContentList v-if="!contentStore.currentContentId" />
        <VulnerabilityChecker v-else />
      </div>
    </main>

    <PoweredByFooter />
  </div>
</template>
