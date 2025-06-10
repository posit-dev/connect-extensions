<script setup lang="ts">
import { onMounted, ref, defineEmits, computed } from 'vue';
import { usePackagesStore } from '../stores/packages';
import { useVulnsStore } from '../stores/vulns';
import LoadingSpinner from './ui/LoadingSpinner.vue';
import StatusMessage from './ui/StatusMessage.vue';

// Define emits
const emit = defineEmits<{
  'content-selected': [contentId: string]
}>();

const packagesStore = usePackagesStore();
const vulnStore = useVulnsStore();
const loadingMessage = ref('Loading content list...');
const isInitialLoad = ref(true);

// Count how many content items still need their packages fetched
const contentItemsNeedingFetch = computed(() => {
  if (packagesStore.contentList.length === 0) return 0;
  
  return packagesStore.contentList.filter(content => 
    !packagesStore.contentItems[content.guid]?.isFetched
  ).length;
});

// Ensure vulnerabilities are loaded once
async function ensureVulnsLoaded() {
  if (!vulnStore.isFetched && !vulnStore.isLoading) {
    loadingMessage.value = 'Loading vulnerability database...';
    await vulnStore.fetchVulns();
    loadingMessage.value = 'Loading content list...';
  }
}

// Load content list and automatically fetch packages in batches
async function loadContentList(fetchAllPackages = false) {
  try {
    // First ensure vulnerabilities are loaded
    await ensureVulnsLoaded();

    // Only fetch the content list if it hasn't been loaded yet or is empty
    if (packagesStore.contentList.length === 0 || isInitialLoad.value) {
      await packagesStore.fetchContentList();
      isInitialLoad.value = false;
      
      // Start automatically fetching packages in batches
      if (packagesStore.contentList.length > 0) {
        await fetchPackagesInBatches();
      }
    } else if (fetchAllPackages) {
      // Manual trigger to fetch any remaining packages
      loadingMessage.value = 'Loading package data for all content...';
      await fetchAllRemainingPackages();
    }
  } catch (error) {
    console.error("Error loading content:", error);
  }
}

// Fetch packages in batches to avoid overwhelming the server
async function fetchPackagesInBatches(batchSize = 3) {
  const contentToFetch = packagesStore.contentList
    .filter(content => !packagesStore.contentItems[content.guid]?.isFetched && 
                     !packagesStore.contentItems[content.guid]?.isLoading);
  
  // Process in batches
  for (let i = 0; i < contentToFetch.length; i += batchSize) {
    const batch = contentToFetch.slice(i, i + batchSize);
    
    // Fetch packages for this batch in parallel
    const fetchPromises = batch.map(content => {
      return packagesStore.fetchPackagesForContent(content.guid)
        .catch(err => console.error(`Error fetching packages for ${content.guid}:`, err));
    });
    
    await Promise.all(fetchPromises);
  }
}

// Fetch packages for all remaining unfetched content items
async function fetchAllRemainingPackages() {
  const contentToFetch = packagesStore.contentList
    .filter(content => !packagesStore.contentItems[content.guid]?.isFetched);
  
  if (contentToFetch.length === 0) return;
  
  const fetchPromises = contentToFetch.map(content => {
    return packagesStore.fetchPackagesForContent(content.guid)
      .catch(err => console.error(`Error fetching packages for ${content.guid}:`, err));
  });
  
  await Promise.all(fetchPromises);
}

// Select a content item to view its details
async function selectContent(contentGuid: string) {
  // Set the current content ID in the store
  packagesStore.setCurrentContentId(contentGuid);
  
  // If packages haven't been fetched for this content yet, fetch them
  const contentItem = packagesStore.contentItems[contentGuid];
  if (!contentItem?.isFetched && !contentItem?.isLoading) {
    await packagesStore.fetchPackagesForContent(contentGuid);
  }
  
  // Emit event for parent components
  emit('content-selected', contentGuid);
}

// Count vulnerable packages in a content item
function countVulnerablePackages(contentGuid: string): number {
  const content = packagesStore.contentItems[contentGuid];
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

// Load content on component mount
onMounted(async () => {
  // Only load content list initially, don't fetch all packages
  await loadContentList(false);
});
</script>

<template>
  <div class="mb-10 p-5 bg-white rounded-lg shadow-md">
    <div v-if="packagesStore.contentListLoading || isInitialLoad">
      <LoadingSpinner :message="loadingMessage" size="md" />
    </div>

    <div v-else-if="packagesStore.contentListError">
      <StatusMessage type="error" message="Error loading content" :details="packagesStore.contentListError.message" />
    </div>

    <div v-else-if="packagesStore.contentList.length === 0">
      <StatusMessage type="warning" message="No content found"
        details="No published content was found on this Connect server." />
    </div>

    <div v-else class="space-y-4">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">Your Connect Content</h2>

      <div class="flex justify-between items-center mb-6">
        <p class="text-gray-600">
          Select a content item to check for package vulnerabilities.
        </p>
        
        <button 
          @click="loadContentList(true)" 
          class="px-3 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 text-sm rounded-md transition-colors"
          :disabled="packagesStore.isFetchingAny"
          v-if="contentItemsNeedingFetch > 0"
        >
          {{ packagesStore.isFetchingAny ? 'Loading...' : `Analyze Remaining (${contentItemsNeedingFetch})` }}
        </button>
      </div>

      <div class="grid gap-4 md:grid-cols-2">
        <div v-for="content in packagesStore.contentList" :key="content.guid"
          class="border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer bg-white"
          @click="selectContent(content.guid)">
          <div class="flex justify-between items-start mb-2">
            <h3 class="font-medium text-blue-600 truncate">{{ content.title || 'Unnamed Content' }}</h3>
            <span v-if="packagesStore.contentItems[content.guid]?.isFetched" class="text-xs px-2 py-1 rounded-full"
              :class="countVulnerablePackages(content.guid) > 0 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'">
              {{ countVulnerablePackages(content.guid) > 0
                ? `${countVulnerablePackages(content.guid)} vulnerable packages`
                : 'No vulnerabilities' }}
            </span>
            <span v-else-if="packagesStore.contentItems[content.guid]?.isLoading"
              class="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600">
              Loading...
            </span>
          </div>

          <div class="text-xs text-gray-500 truncate">
            {{ content.app_mode || 'Unknown type' }} · ID: {{ content.guid }}
          </div>

          <div class="mt-2 text-sm">
            <span v-if="packagesStore.contentItems[content.guid]?.packages.length">
              {{ packagesStore.contentItems[content.guid].packages.length }} packages
            </span>
            <span v-else-if="packagesStore.contentItems[content.guid]?.error" class="text-red-600">
              Error loading packages
            </span>
            <span v-else-if="!packagesStore.contentItems[content.guid]" class="text-gray-400">
              Click to load packages
            </span>
            <span v-else-if="packagesStore.contentItems[content.guid]?.isLoading" class="text-gray-400">
              Loading packages...
            </span>
            <span v-else class="text-gray-400">
              No packages found
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
