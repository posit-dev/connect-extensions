<script setup lang="ts">
import { computed, onMounted } from "vue";
import LoadingSpinner from "./ui/LoadingSpinner.vue";
import { useContentStore } from "../stores/content";
import { useUserStore } from "../stores/user";
import { timeAgo } from "../utils/formatting";
import type { OwnerFilter } from "../stores/content";

const contentStore = useContentStore();
const userStore = useUserStore();

onMounted(() => {
  contentStore.fetchContent();
});

const tabs: { key: OwnerFilter; label: string }[] = [
  { key: "mine", label: "My Content" },
  { key: "all", label: "All Content" },
];

const myCount = computed(() => {
  const guid = userStore.user?.guid;
  if (!guid) return 0;
  const query = contentStore.search.trim().toLowerCase();
  return contentStore.items.filter((item) => {
    if (item.owner_guid !== guid) return false;
    if (!query) return true;
    const title = (item.title || "").toLowerCase();
    const name = item.name.toLowerCase();
    const ownerUsername = (item.owner?.username || "").toLowerCase();
    return title.includes(query) || name.includes(query) || ownerUsername.includes(query);
  }).length;
});

const allCount = computed(() => {
  const query = contentStore.search.trim().toLowerCase();
  if (!query) return contentStore.items.length;
  return contentStore.items.filter((item) => {
    const title = (item.title || "").toLowerCase();
    const name = item.name.toLowerCase();
    const ownerUsername = (item.owner?.username || "").toLowerCase();
    return title.includes(query) || name.includes(query) || ownerUsername.includes(query);
  }).length;
});

function tabCount(key: OwnerFilter): number {
  return key === "mine" ? myCount.value : allCount.value;
}

function ownerDisplayName(item: (typeof contentStore.items)[number]): string {
  if (!item.owner) return "";
  const { first_name, last_name, username } = item.owner;
  if (first_name || last_name) return `${first_name} ${last_name}`.trim();
  return username;
}

const emptyMessage = computed(() => {
  const query = contentStore.search.trim();
  if (query) return `No content matching '${query}'.`;
  if (contentStore.ownerFilter === "mine")
    return "You don't have any content with trace collection enabled.";
  return "No content with trace collection enabled was found.";
});
</script>

<template>
  <div>
    <!-- Search -->
    <div class="relative mb-3">
      <svg
        class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="2"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M21 21l-4.35-4.35m0 0A7.5 7.5 0 1 0 5.1 5.1a7.5 7.5 0 0 0 11.55 11.55z"
        />
      </svg>
      <input
        v-model="contentStore.search"
        type="text"
        placeholder="Search content..."
        class="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400"
      />
    </div>

    <!-- Tabs -->
    <div class="flex border-b border-gray-200 mb-4">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="px-4 py-2 text-sm font-medium border-b-2 transition-colors"
        :class="
          contentStore.ownerFilter === tab.key
            ? 'border-blue-500 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        "
        @click="contentStore.ownerFilter = tab.key"
      >
        {{ tab.label }}
        <span
          class="ml-1.5 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-medium rounded-full"
          :class="
            contentStore.ownerFilter === tab.key
              ? 'bg-blue-100 text-blue-600'
              : 'bg-gray-100 text-gray-500'
          "
        >
          {{ tabCount(tab.key) }}
        </span>
      </button>
    </div>

    <!-- Loading -->
    <LoadingSpinner v-if="contentStore.isLoading" message="Loading content..." class="mt-16" />

    <!-- Error -->
    <div v-else-if="contentStore.error" class="text-red-600 text-sm">
      {{ contentStore.error }}
    </div>

    <!-- Empty state -->
    <div v-else-if="contentStore.filteredItems.length === 0" class="text-gray-500 text-sm py-8 text-center">
      {{ emptyMessage }}
    </div>

    <!-- Content list -->
    <ul v-else class="space-y-2">
      <li
        v-for="item in contentStore.filteredItems"
        :key="item.guid"
        class="bg-white rounded-lg border border-gray-200 px-4 py-3 cursor-pointer hover:border-blue-400 hover:shadow-sm transition-all"
        @click="contentStore.selectContent(item)"
      >
        <div class="flex items-center gap-2">
          <p class="font-medium text-gray-800 truncate">{{ item.title || item.name }}</p>
          <span
            v-if="item.app_mode"
            class="shrink-0 inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600"
          >
            {{ item.app_mode }}
          </span>
        </div>
        <p
          v-if="item.description"
          class="text-sm text-gray-500 mt-0.5 truncate"
        >
          {{ item.description }}
        </p>
        <div class="flex items-center gap-2 mt-1 text-xs text-gray-400">
          <span v-if="contentStore.ownerFilter === 'all' && item.owner">
            {{ ownerDisplayName(item) }}
          </span>
          <span v-if="contentStore.ownerFilter === 'all' && item.owner && item.last_deployed_time" aria-hidden="true">&middot;</span>
          <span v-if="item.last_deployed_time">
            Deployed {{ timeAgo(item.last_deployed_time) }}
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>
