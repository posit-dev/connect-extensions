<script setup lang="ts">
defineProps<{
  message?: string;
}>();
</script>

<template>
  <div class="flex flex-col items-center justify-center gap-3">
    <div
      class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"
    ></div>
    <p v-if="message" class="text-sm text-gray-500">{{ message }}</p>
  </div>
</template>
