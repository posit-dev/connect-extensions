<script setup lang="ts">
import { ref } from 'vue';
import { usePackagesStore } from '../stores/packages';
import { useVulnsStore } from '../stores/vulns';
import FormInput from './ui/FormInput.vue';
import StatusMessage from './ui/StatusMessage.vue';

const packagesStore = usePackagesStore();
const vulnStore = useVulnsStore();

const contentId = ref('');
const isLoading = ref(false);
const errorMessage = ref('');
const hasFoundContent = ref(false);

// Ensure vulnerabilities are loaded once
async function ensureVulnsLoaded() {
  if (!vulnStore.isFetched && !vulnStore.isLoading) {
    await vulnStore.fetchVulns();
  }
}

async function handleSubmit(value: string) {
  if (!value) {
    errorMessage.value = 'Please enter a content GUID';
    return;
  }

  contentId.value = value;
  isLoading.value = true;
  errorMessage.value = '';

  try {
    // First ensure vulnerabilities are loaded
    await ensureVulnsLoaded();
    
    // Then fetch packages for the provided content ID
    await packagesStore.fetchPackagesForContent(contentId.value);
    hasFoundContent.value = true;
  } catch (err) {
    console.error('Error fetching content:', err);
    errorMessage.value = err instanceof Error 
      ? err.message 
      : 'Failed to fetch packages for the provided content ID';
    hasFoundContent.value = false;
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="mb-10 p-5 bg-white rounded-lg shadow-md">
    <h2 class="mb-4 text-xl font-semibold text-gray-800">Content Vulnerability Scanner</h2>
    
    <div class="mb-5">
      <p class="text-gray-600 mb-3">
        Enter the GUID of the content you want to scan for package vulnerabilities.
      </p>
      
      <FormInput
        placeholder="Enter Content GUID (e.g., 12345678-1234-1234-1234-1234567890ab)"
        buttonText="Scan Content"
        loadingText="Scanning..."
        :isLoading="isLoading"
        @submit="handleSubmit"
      />
      
      <StatusMessage
        v-if="errorMessage"
        type="error"
        :message="errorMessage"
        class="mt-3"
      />
    </div>
    
    <StatusMessage
      v-if="packagesStore.isFetched && !hasFoundContent && !errorMessage"
      type="warning"
      message="No packages found"
      details="No packages found for the provided content or no content was found."
    />
  </div>
</template>