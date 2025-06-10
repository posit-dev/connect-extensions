<script setup lang="ts">
import VulnerabilityChecker from './components/VulnerabilityChecker.vue'
import ContentInput from './components/ContentInput.vue'
import PoweredByFooter from './components/PoweredByFooter.vue'
import { useVulnsStore } from './stores/vulns';

const vulnStore = useVulnsStore();

vulnStore.fetchVulns();
</script>

<template>
  <div class="flex flex-col min-h-svh">
    <main class="flex-1 p-4 md:p-8 bg-gray-100">
      <div class="max-w-4xl mx-auto">
        <ContentInput />
        <VulnerabilityChecker />
      </div>
    </main>

    <PoweredByFooter />
  </div>
</template>
