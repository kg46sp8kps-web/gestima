<script setup lang="ts">
/**
 * Proxy Features Test Panel - iframe wrapper for standalone test page
 *
 * Embeds /static/test_proxy_features.html for quick testing:
 * - 3D viewer with inner/outer visualization
 * - Proxy metrics display
 * - Basic time estimation
 */
</script>

<template>
  <div class="proxy-test-panel">
    <iframe
      src="/static/test_proxy_features.html"
      frameborder="0"
      class="test-iframe"
      title="Proxy Features Test Environment"
    ></iframe>
  </div>
</template>

<style scoped>
.proxy-test-panel {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.test-iframe {
  width: 100%;
  height: 100%;
  border: none;
}
</style>
