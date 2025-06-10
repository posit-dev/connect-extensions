<script setup lang="ts">
import { computed, defineProps, defineEmits } from 'vue';
import { usePackagesStore } from '../stores/packages';
import { useVulnsStore } from '../stores/vulns';
import { useContentStore } from '../stores/content';

const props = defineProps<{
  content: {
    guid: string;
    title: string;
    app_mode?: string;
    content_url?: string;
    dashboard_url?: string;
  };
}>();

const emit = defineEmits<{
  'select': [contentId: string];
}>();

const packagesStore = usePackagesStore();
const vulnStore = useVulnsStore();

// Compute if this content has been fetched
const isFetched = computed(() => !!packagesStore.contentItems[props.content.guid]?.isFetched);
const isLoading = computed(() => !!packagesStore.contentItems[props.content.guid]?.isLoading);
const hasError = computed(() => !!packagesStore.contentItems[props.content.guid]?.error);
const packageCount = computed(() => packagesStore.contentItems[props.content.guid]?.packages.length || 0);

// Count vulnerable packages in this content item
function countVulnerablePackages(): number {
  const content = packagesStore.contentItems[props.content.guid];
  if (!content || !content.packages.length) return 0;

  let count = 0;
  for (const pkg of content.packages) {
    const repo = pkg.language.toLowerCase() === 'python' ? 'pypi' : 'cran';
    const vulnerabilityMap = repo === 'pypi' ? vulnStore.pypi : vulnStore.cran;
    const packageName = pkg.name.toLowerCase();

    if (vulnerabilityMap[packageName] &&
      vulnerabilityMap[packageName].some(vuln => vuln.versions && vuln.versions[pkg.version])) {
      count++;
    }
  }

  return count;
}

// Computed properties for display
const hasVulnerabilities = computed(() => countVulnerablePackages() > 0);
const vulnerabilityText = computed(() => {
  const count = countVulnerablePackages();
  return count > 0 ? `${count} vulnerable packages` : 'No vulnerabilities';
});

// Handle card click
function handleClick() {
  emit('select', props.content.guid);
}
</script>

<template>
  <div 
    class="border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer bg-white"
    @click="handleClick"
  >
    <div class="flex justify-between items-start mb-2">
      <h3 class="font-medium text-blue-600 truncate">{{ content.title || 'Unnamed Content' }}</h3>
      <span 
        v-if="isFetched" 
        class="text-xs px-2 py-1 rounded-full"
        :class="hasVulnerabilities ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'"
      >
        {{ vulnerabilityText }}
      </span>
      <span 
        v-else-if="isLoading" 
        class="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600"
      >
        Loading...
      </span>
    </div>

    <div class="text-xs text-gray-500 truncate">
      {{ content.app_mode || 'Unknown type' }} · ID: {{ content.guid }}
    </div>

    <div class="mt-2 text-sm">
      <span v-if="packageCount > 0">
        {{ packageCount }} packages
      </span>
      <span v-else-if="hasError" class="text-red-600">
        Error loading packages
      </span>
      <span v-else-if="!isFetched && !isLoading" class="text-gray-400">
        Click to load packages
      </span>
      <span v-else-if="isLoading" class="text-gray-400">
        Loading packages...
      </span>
      <span v-else class="text-gray-400">
        No packages found
      </span>
    </div>
  </div>
</template>