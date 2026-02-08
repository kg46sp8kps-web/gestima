<script setup lang="ts">
// No props needed - pure display component
</script>

<template>
  <div class="header-center">
    <router-link to="/" class="logo-link">
      <div class="logo-text">
        <span class="logo-red">GESTI</span><span class="logo-black">MA</span>
      </div>
    </router-link>
  </div>
</template>

<style scoped>
.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
}

.logo-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
}

.logo-text {
  font-size: calc(var(--text-2xl) * 2);
  font-weight: 700;
  letter-spacing: 0.5px;
}

.logo-red {
  color: var(--color-danger);
}

.logo-black {
  color: var(--text-primary);
}
</style>
