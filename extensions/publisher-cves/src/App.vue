<script setup lang="ts">
import { useVulnsStore } from './stores/vulns'
import { onMounted } from 'vue'

const vulnStore = useVulnsStore()

vulnStore.fetchVulns()
</script>

<template>
  <div class="container">
    <div v-if="vulnStore.isLoading" class="loading">Loading vulnerabilities...</div>
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
