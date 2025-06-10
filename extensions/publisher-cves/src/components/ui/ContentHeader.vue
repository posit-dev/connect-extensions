<script setup lang="ts">
defineProps<{
  contentId: string;
}>();
</script>

<template>
  <div class="mb-4 p-3 bg-blue-50 border border-blue-100 rounded-md">
    <p class="text-blue-800 font-medium">
      Analyzing content: <span class="font-mono">{{ contentId }}</span>
    </p>
    <slot></slot>
  </div>
</template>