<script setup lang="ts">
import VulnerabilityChecker from './components/VulnerabilityChecker.vue'
import ContentList from './components/ContentList.vue'
import PoweredByFooter from './components/PoweredByFooter.vue'
import { useVulnsStore } from './stores/vulns';
import { usePackagesStore } from './stores/packages';
import { ref, onMounted } from 'vue';

const vulnStore = useVulnsStore();
const packagesStore = usePackagesStore();

// Manage application state
const activeView = ref('list'); // 'list' or 'detail'

// Load vulnerabilities on mount
onMounted(async () => {
  // Load vulnerabilities once at the beginning
  if (!vulnStore.isFetched && !vulnStore.isLoading) {
    await vulnStore.fetchVulns();
  }
});

// Return to content list
function handleBack() {
  activeView.value = 'list';
  packagesStore.setCurrentContentId('');
}

// Handle content selection
function handleContentSelected(contentId: string) {
  if (contentId) {
    activeView.value = 'detail';
  }
}

// Watch for content selection changes
function onContentSelected() {
  handleContentSelected(packagesStore.currentContentId || '');
}
</script>

<template>
  <div class="flex flex-col min-h-svh">
    <main class="flex-1 p-4 md:p-8 bg-gray-100">
      <div class="max-w-4xl mx-auto">
        <!-- Toggle between list and detail view -->
        <ContentList v-if="activeView === 'list'" @content-selected="onContentSelected" />
        <VulnerabilityChecker v-else :showBackButton="true" @back="handleBack" />
      </div>
    </main>

    <PoweredByFooter />
  </div>
</template>
