<script setup lang="ts">
defineProps<{
  message?: string;
}>();
</script>

<template>
  <div class="flex flex-col items-center justify-center p-4">
    <div
      class="border-4 border-gray-200 rounded-full mb-3 border-t-indigo-500 animate-spin w-10 h-10"
    />
    <p v-if="message" class="text-indigo-500 text-center">{{ message }}</p>
  </div>
</template>
