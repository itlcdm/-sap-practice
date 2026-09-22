<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { listExecutions } from "../services/tasksApi";
import { listCurrencyExecutions } from "../services/currencyTasksApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";
import StatusBadge from "../components/StatusBadge.vue";

const executions = ref([]); const loading = ref(true); const refreshing = ref(false); const error = ref(""); let timer;
async function load() { refreshing.value = true; try { const [regular, currency] = await Promise.all([listExecutions({ status: "running" }), listCurrencyExecutions({ status: "running" })]); executions.value = [...regular, ...currency.map((item) => ({ ...item, id: `currency-${item.id}`, task_name: `${item.task_name} · ${item.company_name}`, is_currency: true }))]; } catch (err) { error.value = extractErrorMessage(err, "No se pudieron cargar las ejecuciones"); } finally { loading.value = false; refreshing.value = false; } }
onMounted(() => { load(); timer = window.setInterval(load, 10000); });
onUnmounted(() => window.clearInterval(timer));
</script>

<template>
  <section class="page-view"><header class="page-header"><div><h1>Ejecuciones en curso</h1><p class="subtitle">Se actualiza automáticamente cada 10 segundos.</p></div><button class="button secondary" :disabled="refreshing" @click="load">{{ refreshing ? "Actualizando…" : "Actualizar" }}</button></header><p v-if="error" class="alert">{{ error }}</p><div class="card"><p v-if="loading" class="empty-state">Cargando…</p><p v-else-if="!executions.length" class="empty-state">No hay ejecuciones en curso.</p><table v-else class="table"><thead><tr><th>Tarea</th><th>Inicio</th><th>Disparador</th><th>Estado</th></tr></thead><tbody><tr v-for="execution in executions" :key="execution.id"><td><router-link :to="`/ejecuciones/${execution.id}`">{{ execution.task_name }}</router-link></td><td>{{ formatDateTime(execution.started_at) }}</td><td>{{ execution.trigger_type === "scheduled" ? "Programada" : "Manual" }}</td><td><StatusBadge status="running" /></td></tr></tbody></table></div></section>
</template>

<style scoped>
.page-view { display: flex; flex-direction: column; gap: 20px; }.page-header { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }h1 { font-size: 24px; margin: 0 0 4px; }.subtitle { color: var(--text); }.card { overflow-x: auto; background: var(--bg); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); padding: 8px 24px; }.table { width: 100%; border-collapse: collapse; min-width: 620px; }.table th, .table td { padding: 13px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }.table th { color: var(--text); font-size: 12px; text-transform: uppercase; }.table tr:last-child td { border-bottom: 0; }a { color: var(--accent); text-decoration: none; }.button { padding: 9px 14px; border-radius: 7px; border: 1px solid var(--border); color: var(--text-h); background: var(--code-bg); cursor: pointer; }.alert { padding: 12px 16px; color: #b42318; background: rgba(180,35,24,.08); border-radius: 8px; }.empty-state { padding: 24px 0; color: var(--text); text-align: center; }
</style>
