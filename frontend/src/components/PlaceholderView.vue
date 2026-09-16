<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
});
</script>

<template>
  <section class="placeholder">
    <header class="placeholder-header">
      <h1>{{ title }}</h1>
      <p v-if="description" class="subtitle">{{ description }}</p>
    </header>

    <div class="card empty-card">
      <p class="empty-state">Esta pantalla se construirá próximamente.</p>
    </div>
  </section>
</template>

<style scoped>
.placeholder {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.placeholder-header h1 {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 4px;
}

.subtitle {
  color: var(--text);
}

.card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 24px;
}

.empty-card {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}

.empty-state {
  color: var(--text);
  margin: 0;
}
</style>
