<script setup lang="ts">
import { onMounted } from "vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";
import { useContentStore } from "../stores/content";

const contentStore = useContentStore();

onMounted(() => {
  contentStore.fetchContent();
});
</script>

<template>
  <div>
    <h2 class="text-lg font-semibold text-gray-700 mb-4">Content</h2>

    <LoadingSpinner v-if="contentStore.isLoading" message="Loading content..." class="mt-16" />

    <div v-else-if="contentStore.error" class="text-red-600 text-sm">
      {{ contentStore.error }}
    </div>

    <div v-else-if="contentStore.items.length === 0" class="text-gray-500 text-sm">
      No content found.
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="item in contentStore.items"
        :key="item.guid"
        class="bg-white rounded-lg border border-gray-200 px-4 py-3 cursor-pointer hover:border-blue-400 hover:shadow-sm transition-all"
        @click="contentStore.selectContent(item)"
      >
        <p class="font-medium text-gray-800">{{ item.title || item.name }}</p>
        <p v-if="item.app_mode" class="text-xs text-gray-500 mt-0.5">{{ item.app_mode }}</p>
      </li>
    </ul>
  </div>
</template>
