<script setup>
const METRICS = [
  { label: "Tareas activas", value: 12 },
  { label: "Tareas programadas", value: 8 },
  { label: "Ejecuciones del día", value: 34 },
  { label: "Ejecuciones exitosas", value: 30 },
  { label: "Ejecuciones fallidas", value: 4 },
  { label: "Próximas ejecuciones", value: 5 },
];
</script>

<template>
  <section class="dashboard">
    <header class="dashboard-header">
      <h1>Dashboard</h1>
      <p class="subtitle">Resumen general de tareas y ejecuciones</p>
    </header>

    <div class="metrics-grid">
      <article
        v-for="metric in METRICS"
        :key="metric.label"
        class="metric-card"
      >
        <p class="metric-value">{{ metric.value }}</p>
        <p class="metric-label">{{ metric.label }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dashboard-header h1 {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 4px;
}

.subtitle {
  color: var(--text);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

.metric-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 20px;
}

.metric-value {
  font-size: 32px;
  font-weight: 600;
  color: var(--text-h);
  margin: 0;
}

.metric-label {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--text);
}
</style>
