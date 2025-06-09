<script setup lang="ts">
import { ref } from 'vue'

const isLoading = ref(true);

// Immediately fetch vulnerabilities in setup
(async () => {
  try {
    const response = await fetch('/api/vulns')
    const data = await response.json()
    console.log(data)
    isLoading.value = false
  } catch (error) {
    console.error('Error fetching vulnerabilities:', error)
    isLoading.value = false
  }
})()
</script>

<template>
  <div class="container">
    <div v-if="isLoading" class="loading">Loading vulnerabilities...</div>
    <div v-else class="complete">Done</div>
  </div>
</template>

<style scoped>
.container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  font-size: 1.5rem;
}

.loading {
  color: #646cff;
}

.complete {
  color: #42b883;
  font-weight: bold;
}
</style>
