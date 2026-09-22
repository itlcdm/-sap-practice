<script setup>
import { onMounted, ref } from "vue";
import { listSchedules } from "../services/tasksApi";
import { listCurrencyTasks } from "../services/currencyTasksApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";

const schedules = ref([]);
const loading = ref(true);
const refreshing = ref(false);
const error = ref("");

const WEEK_DAYS = {
  "0": "domingo",
  "1": "lunes",
  "2": "martes",
  "3": "miércoles",
  "4": "jueves",
  "5": "viernes",
  "6": "sábado",
};

function formatScheduleTime(cronExpression) {
  const parts = cronExpression.split(" ");
  const date = new Date();
  date.setHours(Number(parts[1]), Number(parts[0]), 0, 0);

  return new Intl.DateTimeFormat("es-PA", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

function describeSchedule(schedule) {
  if (schedule.schedule_type === "once") {
    return `Una sola vez: ${formatDateTime(schedule.scheduled_at)}`;
  }

  const parts = schedule.cron_expression?.split(" ") || [];
  if (parts.length !== 5) return "Programación recurrente";

  const time = formatScheduleTime(schedule.cron_expression);
  if (parts[2] !== "*") return `Día ${parts[2]} de cada mes a las ${time}`;
  if (parts[4] !== "*") return `Cada ${WEEK_DAYS[parts[4]] || `día ${parts[4]}`} a las ${time}`;
  if (parts[1] === "*" && parts[0] !== "*") return `Cada hora, al minuto ${parts[0]}`;
  return `Todos los días a las ${time}`;
}

async function load() {
  refreshing.value = true;
  try {
    const [regular, currency] = await Promise.all([listSchedules(), listCurrencyTasks()]);
    schedules.value = [
      ...regular,
      ...currency.map((task) => ({
        task_id: `currency-${task.id}`,
        task_name: task.name,
        schedule_type: "recurring",
        cron_expression: `${task.run_at.slice(3, 5)} ${task.run_at.slice(0, 2)} * * *`,
        scheduled_at: null,
        next_run_time: null,
        currency_company: task.company_name,
      })),
    ];
  }
  catch (err) { error.value = extractErrorMessage(err, "No se pudieron cargar las programaciones"); }
  finally { loading.value = false; refreshing.value = false; }
}

onMounted(load);
</script>

<template>
  <section class="page-view">
    <header class="page-header"><div><h1>Tareas programadas</h1><p class="subtitle">Horarios activos y próxima ejecución.</p></div><button class="button button-secondary" :disabled="refreshing" @click="load">{{ refreshing ? "Actualizando…" : "Actualizar" }}</button></header>
    <p v-if="error" class="alert alert-error">{{ error }}</p>
    <div class="card"><p v-if="loading" class="empty-state">Cargando…</p><p v-else-if="!schedules.length" class="empty-state">No hay tareas programadas.</p><table v-else class="table"><thead><tr><th>Tarea</th><th>Tipo</th><th>Detalle</th><th>Próxima ejecución</th><th></th></tr></thead><tbody><tr v-for="schedule in schedules" :key="schedule.task_id"><td class="strong">{{ schedule.task_name }}<small v-if="schedule.currency_company">Filial: {{ schedule.currency_company }}</small></td><td>{{ schedule.currency_company ? "Cambio de monedas" : schedule.schedule_type === "once" ? "Una sola vez" : "Recurrente" }}</td><td><strong>{{ describeSchedule(schedule) }}</strong></td><td>{{ schedule.currency_company ? "Diariamente" : formatDateTime(schedule.next_run_time) }}</td><td><router-link v-if="!schedule.currency_company" :to="`/tareas/${schedule.task_id}/programar`">Editar</router-link></td></tr></tbody></table></div>
  </section>
</template>

<style scoped>
.page-view { display: flex; flex-direction: column; gap: 20px; }.page-header { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }h1 { font-size: 24px; margin: 0 0 4px; }.subtitle { color: var(--text); }.card { overflow-x: auto; background: var(--bg); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); padding: 8px 24px; }.table { width: 100%; border-collapse: collapse; min-width: 680px; }.table th, .table td { padding: 13px 10px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }.table th { color: var(--text); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }.table tr:last-child td { border-bottom: 0; }.strong { color: var(--text-h); font-weight: 600; }td strong, td small { display: block; }td strong { color: var(--text-h); font-weight: 500; }.technical { margin-top: 3px; color: var(--text); font-size: 11px; }a { color: var(--accent); text-decoration: none; }.button { padding: 9px 14px; border: 0; border-radius: 7px; color: #fff; background: var(--accent); font: inherit; cursor: pointer; }.button:disabled { opacity: .6; cursor: not-allowed; }.button-secondary { color: var(--text-h); background: var(--code-bg); border: 1px solid var(--border); }.alert { padding: 12px 16px; border-radius: 8px; }.alert-error { color: #b42318; background: rgba(180,35,24,.08); }.empty-state { padding: 24px 0; color: var(--text); text-align: center; }
</style>
