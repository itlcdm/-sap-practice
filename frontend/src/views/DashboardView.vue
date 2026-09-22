<script setup>
import { computed, onMounted, ref } from "vue";
import { listExecutions, listSchedules, listTasks } from "../services/tasksApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";
import StatusBadge from "../components/StatusBadge.vue";

const tasks = ref([]); const schedules = ref([]); const history = ref([]); const running = ref([]); const loading = ref(true); const refreshing = ref(false); const error = ref("");
const today = new Date().toISOString().slice(0, 10);
const executionsToday = computed(() => history.value.filter((item) => item.started_at?.slice(0, 10) === today).length);
const successes = computed(() => history.value.filter((item) => item.status === "success").length);
const failures = computed(() => history.value.filter((item) => item.status === "failed").length);
const totalExecutions = computed(() => history.value.length + running.value.length);
const statusIndicators = computed(() => [
  { key: "running", label: "En curso", value: running.value.length, color: "#b45309" },
  { key: "success", label: "Exitosas", value: successes.value, color: "#067647" },
  { key: "failed", label: "Fallidas", value: failures.value, color: "#b42318" },
]);
function percentage(value) {
  if (!totalExecutions.value) return 0;
  return Math.round((value / totalExecutions.value) * 100);
}
const metrics = computed(() => [
  { label: "Tareas activas", value: tasks.value.filter((item) => item.is_active).length },
  { label: "Tareas programadas", value: schedules.value.length },
  { label: "Ejecuciones del día", value: executionsToday.value },
  { label: "Ejecuciones exitosas", value: successes.value },
  { label: "Ejecuciones fallidas", value: failures.value },
  { label: "Ejecuciones en curso", value: running.value.length },
]);
async function load() { loading.value = true; refreshing.value = true; error.value = ""; try { [tasks.value, schedules.value, history.value, running.value] = await Promise.all([listTasks(), listSchedules(), listExecutions({ status: "history", limit: 100 }), listExecutions({ status: "running" })]); } catch (err) { error.value = extractErrorMessage(err, "No se pudieron cargar los indicadores"); } finally { loading.value = false; refreshing.value = false; } }
onMounted(load);
</script>

<template>
  <section class="dashboard">
    <header class="dashboard-header">
      <h1>Dashboard</h1>
      <p class="subtitle">Resumen general de tareas y ejecuciones</p>
      <button class="button refresh-button" :disabled="refreshing" @click="load">{{ refreshing ? "Actualizando…" : "Actualizar" }}</button>
    </header>

    <p v-if="error" class="alert">{{ error }}</p>
    <p v-if="loading" class="empty-state">Cargando indicadores…</p>
    <div v-else class="metrics-grid">
      <article
        v-for="metric in metrics"
        :key="metric.label"
        class="metric-card"
      >
        <p class="metric-value">{{ metric.value }}</p>
        <p class="metric-label">{{ metric.label }}</p>
      </article>
    </div>
    <section v-if="!loading" class="status-section">
      <div class="card status-card">
        <div class="section-heading"><div><h2>Ejecuciones por estado</h2><p class="subtitle">Distribución de las ejecuciones registradas.</p></div><strong class="total-count">{{ totalExecutions }} total</strong></div>
        <div class="chart" role="img" aria-label="Gráfica de ejecuciones por estado">
          <div v-for="indicator in statusIndicators" :key="indicator.key" class="chart-row">
            <div class="chart-label"><span class="legend-dot" :style="{ backgroundColor: indicator.color }"></span><span>{{ indicator.label }}</span><strong>{{ indicator.value }}</strong></div>
            <div class="bar-track"><div class="bar" :style="{ width: `${Math.max(percentage(indicator.value), indicator.value ? 3 : 0)}%`, backgroundColor: indicator.color }"></div></div>
            <span class="percentage">{{ percentage(indicator.value) }}%</span>
          </div>
        </div>
      </div>
    </section>
    <section v-if="!loading" class="recent card">
      <div class="section-heading"><div><h2>Actividad reciente</h2><p class="subtitle">Últimas ejecuciones registradas.</p></div><router-link to="/ejecuciones/historial">Ver historial</router-link></div>
      <p v-if="!history.length" class="empty-state">Todavía no hay ejecuciones.</p>
      <ul v-else><li v-for="execution in history.slice(0, 5)" :key="execution.id"><router-link :to="`/ejecuciones/${execution.id}`">{{ execution.task_name }}</router-link><span>{{ formatDateTime(execution.started_at) }}</span><StatusBadge :status="execution.status" /></li></ul>
    </section>
  </section>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); padding: 20px; }
.section-heading { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }.section-heading h2 { margin: 0 0 2px; }.section-heading a, .recent a { color: var(--accent); text-decoration: none; font-size: 13px; }
.status-section { display: grid; grid-template-columns: minmax(0, 1fr); }.status-card { min-width: 0; }.total-count { color: var(--text); font-size: 13px; font-weight: 500; white-space: nowrap; }.chart { display: flex; flex-direction: column; gap: 18px; margin-top: 24px; }.chart-row { display: grid; grid-template-columns: 150px minmax(100px, 1fr) 46px; align-items: center; gap: 14px; }.chart-label { display: flex; align-items: center; gap: 8px; color: var(--text-h); font-size: 14px; }.chart-label strong { margin-left: auto; font-weight: 600; }.legend-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }.bar-track { height: 13px; overflow: hidden; background: var(--code-bg); border-radius: 999px; }.bar { height: 100%; min-width: 0; border-radius: inherit; transition: width .35s ease; }.percentage { color: var(--text); font-size: 13px; text-align: right; }
.recent ul { display: flex; flex-direction: column; gap: 10px; padding: 0; margin: 18px 0 0; list-style: none; }.recent li { display: grid; grid-template-columns: 1fr auto auto; gap: 16px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 13px; }.recent li:last-child { border-bottom: 0; }.recent li span { color: var(--text); }.alert { padding: 12px 16px; color: #b42318; background: rgba(180,35,24,.08); border-radius: 8px; }.empty-state { padding: 20px 0; color: var(--text); text-align: center; }

.dashboard-header h1 {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 4px;
}

.dashboard-header { position: relative; }
.refresh-button { position: absolute; top: 0; right: 0; }

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

  .chart-row {
    grid-template-columns: 120px minmax(70px, 1fr) 38px;
    gap: 8px;
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

.button { padding: 9px 14px; border: 1px solid var(--border); border-radius: 7px; color: var(--text-h); background: var(--code-bg); font: inherit; cursor: pointer; }
.button:disabled { opacity: .6; cursor: not-allowed; }
@media (max-width: 600px) { .refresh-button { position: static; margin-top: 12px; } }
</style>
