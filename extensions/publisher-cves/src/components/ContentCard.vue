<script setup lang="ts">
import { computed, defineProps } from "vue";
import ColorBadge from "./ui/ColorBadge.vue";
import { usePackagesStore } from "../stores/packages";
import { useVulnsStore } from "../stores/vulns";
import { useContentStore } from "../stores/content";

const props = defineProps<{
  content: {
    guid: string;
    title: string;
    app_mode?: string;
    content_url?: string;
    dashboard_url?: string;
  };
}>();

const packagesStore = usePackagesStore();
const contentStore = useContentStore();
const vulnStore = useVulnsStore();

// Compute if this content has been fetched
const isFetched = computed(
  () => !!packagesStore.contentItems[props.content.guid]?.isFetched,
);
const isLoading = computed(
  () => !!packagesStore.contentItems[props.content.guid]?.isLoading,
);
const hasError = computed(
  () => !!packagesStore.contentItems[props.content.guid]?.error,
);
const packageCount = computed(
  () => packagesStore.contentItems[props.content.guid]?.packages.length || 0,
);

// Count vulnerable packages in this content item
function countVulnerablePackages(): number {
  const content = packagesStore.contentItems[props.content.guid];
  if (!content || !content.packages.length) return 0;

  let count = 0;
  for (const pkg of content.packages) {
    const vulnerabilityMap =
      pkg.language.toLowerCase() === "python" ? vulnStore.pypi : vulnStore.cran;
    const packageName = pkg.name.toLowerCase();

    if (
      vulnerabilityMap[packageName] &&
      vulnerabilityMap[packageName].some(
        (vuln) => vuln.versions && vuln.versions[pkg.version],
      )
    ) {
      count++;
    }
  }

  return count;
}

// Computed properties for display
const hasVulnerabilities = computed(() => countVulnerablePackages() > 0);
const vulnerabilityText = computed(() => {
  const count = countVulnerablePackages();
  if (count > 0) {
    return count === 1
      ? "1 vulnerable package"
      : `${count} vulnerable packages`;
  }
  return "No vulnerabilities";
});

// Handle card click
function handleClick() {
  contentStore.currentContentId = props.content.guid;
  scrollTo({ top: 0, left: 0, behavior: "instant" });
}
</script>

<template>
  <div
    class="border border-gray-300 hover:border-gray-400 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer bg-white group"
    @click="handleClick"
  >
    <div class="flex justify-between items-start mb-2">
      <h3 class="font-medium text-blue-600 truncate group-hover:underline">
        {{ content.title || "Unnamed Content" }}
      </h3>

      <template v-if="!hasError">
        <ColorBadge
          v-if="isFetched"
          :type="hasVulnerabilities ? 'error' : 'success'"
        >
          {{ vulnerabilityText }}
        </ColorBadge>

        <ColorBadge v-else-if="isLoading" type="neutral">Loading...</ColorBadge>
      </template>
    </div>

    <div class="text-xs text-gray-500 truncate">
      Type: {{ content.app_mode || "Unknown type" }} · GUID: {{ content.guid }}
    </div>

    <div class="mt-2 text-sm">
      <span v-if="packageCount > 0"> {{ packageCount }} packages </span>
      <span v-else-if="hasError" class="text-red-600">
        Error loading packages
      </span>
      <span v-else-if="isLoading" class="text-gray-400">
        Loading packages...
      </span>
      <span v-else class="text-gray-400"> No packages found </span>
    </div>
  </div>
</template>
