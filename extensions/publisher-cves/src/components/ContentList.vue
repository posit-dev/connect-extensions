<script setup lang="ts">
import { onMounted, ref, defineEmits, computed } from 'vue';
import { usePackagesStore } from '../stores/packages';
import { useContentStore } from '../stores/content';
import { useVulnsStore } from '../stores/vulns';
import LoadingSpinner from './ui/LoadingSpinner.vue';
import StatusMessage from './ui/StatusMessage.vue';
import ContentCard from './ContentCard.vue';

// Define emits
const emit = defineEmits<{
  'content-selected': [contentId: string]
}>();

const packagesStore = usePackagesStore();
const contentStore = useContentStore();
const vulnStore = useVulnsStore();
const loadingMessage = ref('Loading content list...');
const isInitialLoad = ref(true);

// Count how many content items still need their packages fetched
const contentItemsNeedingFetch = computed(() => {
  if (contentStore.contentList.length === 0) return 0;
  
  return contentStore.contentList.filter(content => 
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
    if (contentStore.contentList.length === 0 || isInitialLoad.value) {
      await contentStore.fetchContentList();
      isInitialLoad.value = false;
      
      // Start automatically fetching packages in batches
      if (contentStore.contentList.length > 0) {
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
  const contentToFetch = contentStore.contentList
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
  const contentToFetch = contentStore.contentList
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
  // Set the current content ID in both stores
  contentStore.setCurrentContentId(contentGuid);
  packagesStore.setCurrentContentId(contentGuid);
  
  // If packages haven't been fetched for this content yet, fetch them
  const contentItem = packagesStore.contentItems[contentGuid];
  if (!contentItem?.isFetched && !contentItem?.isLoading) {
    await packagesStore.fetchPackagesForContent(contentGuid);
  }
  
  // Emit event for parent components
  emit('content-selected', contentGuid);
}

// This function is redundant and can be removed
// handleContentSelect was just a passthrough to selectContent

// Load content on component mount
onMounted(async () => {
  // Only load content list initially, don't fetch all packages
  await loadContentList(false);
});
</script>

<template>
  <div class="mb-10 p-5 bg-white rounded-lg shadow-md">
    <div v-if="contentStore.isLoading || isInitialLoad">
      <LoadingSpinner :message="loadingMessage" size="md" />
    </div>

    <div v-else-if="contentStore.error">
      <StatusMessage type="error" message="Error loading content" :details="contentStore.error.message" />
    </div>

    <div v-else-if="contentStore.contentList.length === 0">
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
        <ContentCard 
          v-for="content in contentStore.contentList" 
          :key="content.guid" 
          :content="content"
          @select="selectContent"
        />
      </div>
    </div>
  </div>
</template>
