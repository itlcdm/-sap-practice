<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { createSchedule, deleteSchedule, getTask, listSchedules } from "../services/tasksApi";
import { extractErrorMessage, formatDateTime } from "../utils/format";

const route = useRoute();
const task = ref(null);
const schedule = ref(null);
const loading = ref(true);
const saving = ref(false);
const error = ref("");
const message = ref("");
const scheduleType = ref("recurring");
const date = ref("");
const time = ref("08:00");
const recurrence = ref("monthly");
const monthDay = ref(1);
const weekDay = ref(1);

const existingLabel = computed(() => schedule.value ? formatDateTime(schedule.value.next_run_time) : "Sin programación activa");
const recurrenceLabel = computed(() => ({ daily: "Todos los días", weekly: "Cada semana", monthly: "Cada mes" }[recurrence.value]));

function localDateValue(value) {
  if (!value) return "";
  const parsed = new Date(value);
  const pad = (number) => String(number).padStart(2, "0");
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}`;
}

function loadRecurringValues(cron) {
  if (!cron) return;
  const parts = cron.split(" ");
  time.value = `${String(parts[1]).padStart(2, "0")}:${String(parts[0]).padStart(2, "0")}`;
  if (parts[4] !== "*") { recurrence.value = "weekly"; weekDay.value = Number(parts[4]); }
  else if (parts[2] !== "*") { recurrence.value = "monthly"; monthDay.value = Number(parts[2]); }
  else recurrence.value = "daily";
}

async function load() {
  try {
    task.value = await getTask(route.params.id);
    const schedules = await listSchedules();
    schedule.value = schedules.find((item) => item.task_id === Number(route.params.id)) || null;
    if (schedule.value) {
      scheduleType.value = schedule.value.schedule_type;
      if (schedule.value.schedule_type === "once") date.value = localDateValue(schedule.value.scheduled_at);
      else loadRecurringValues(schedule.value.cron_expression);
    }
  } catch (err) { error.value = extractErrorMessage(err, "No se pudo cargar la programación"); }
  finally { loading.value = false; }
}

function buildCron() {
  const [hour, minute] = time.value.split(":");
  if (recurrence.value === "daily") return `${Number(minute)} ${Number(hour)} * * *`;
  if (recurrence.value === "weekly") return `${Number(minute)} ${Number(hour)} * * ${weekDay.value}`;
  return `${Number(minute)} ${Number(hour)} ${monthDay.value} * *`;
}

async function save() {
  error.value = ""; message.value = "";
  if (scheduleType.value === "once" && !date.value) { error.value = "Selecciona la fecha de ejecución."; return; }
  saving.value = true;
  const payload = scheduleType.value === "once"
    ? { schedule_type: "once", scheduled_at: `${date.value}T${time.value}:00`, cron_expression: null }
    : { schedule_type: "recurring", scheduled_at: null, cron_expression: buildCron() };
  try {
    schedule.value = await createSchedule(route.params.id, payload);
    message.value = scheduleType.value === "once" ? "Ejecución única programada correctamente." : `${recurrenceLabel.value} programada correctamente.`;
  } catch (err) { error.value = extractErrorMessage(err, "No se pudo guardar la programación"); }
  finally { saving.value = false; }
}

async function remove() {
  saving.value = true; error.value = "";
  try { await deleteSchedule(route.params.id); schedule.value = null; message.value = "Programación eliminada."; }
  catch (err) { error.value = extractErrorMessage(err, "No se pudo eliminar la programación"); }
  finally { saving.value = false; }
}

onMounted(load);
</script>

<template>
  <section class="schedule-view">
    <header class="page-header">
      <div><h1>Programar tarea</h1><p class="subtitle">{{ task?.name || "Configuración de ejecución recurrente" }}</p></div>
      <router-link class="button button-secondary" to="/programaciones">Ver programaciones</router-link>
    </header>
    <p v-if="error" class="alert alert-error">{{ error }}</p>
    <p v-if="message" class="alert alert-success">{{ message }}</p>
    <p v-if="loading" class="empty-state">Cargando programación…</p>
    <div v-else class="card schedule-card">
      <div class="current"><span class="eyebrow">PRÓXIMA EJECUCIÓN</span><strong>{{ existingLabel }}</strong><small v-if="schedule">{{ schedule.schedule_type === "once" ? "Ejecución única" : `Recurrente · ${schedule.cron_expression}` }}</small></div>
      <form @submit.prevent="save">
        <fieldset><legend>Tipo de programación</legend><label class="choice"><input v-model="scheduleType" type="radio" value="once" /> Una sola vez</label><label class="choice"><input v-model="scheduleType" type="radio" value="recurring" /> Recurrente</label></fieldset>
        <div class="form-grid"><label v-if="scheduleType === 'once'">Fecha de ejecución<input v-model="date" type="date" required /></label><label>Hora<input v-model="time" type="time" required /></label></div>
        <div v-if="scheduleType === 'recurring'" class="recurrence-panel"><label>Repetir<select v-model="recurrence"><option value="daily">Cada día</option><option value="weekly">Cada semana</option><option value="monthly">Cada mes</option></select></label><label v-if="recurrence === 'weekly'">Día de la semana<select v-model="weekDay"><option :value="1">Lunes</option><option :value="2">Martes</option><option :value="3">Miércoles</option><option :value="4">Jueves</option><option :value="5">Viernes</option><option :value="6">Sábado</option><option :value="0">Domingo</option></select></label><label v-if="recurrence === 'monthly'">Día del mes<input v-model.number="monthDay" type="number" min="1" max="28" required /><small>Usa un día entre 1 y 28 para que funcione en todos los meses.</small></label></div>
        <p class="preview">{{ scheduleType === "once" ? (date ? `Se ejecutará el ${date} a las ${time}.` : "Selecciona una fecha.") : `${recurrenceLabel} a las ${time}.` }}</p>
        <div class="form-actions"><button v-if="schedule" type="button" class="button danger" :disabled="saving" @click="remove">Eliminar programación</button><button class="button" :disabled="saving">{{ saving ? "Guardando…" : "Guardar programación" }}</button></div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.schedule-view { display: flex; flex-direction: column; gap: 20px; }
.page-header, .form-actions { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
h1 { font-size: 24px; margin: 0 0 4px; }.subtitle { color: var(--text); }
.card { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); padding: 24px; }
.schedule-card { max-width: 720px; display: flex; flex-direction: column; gap: 28px; }
.schedule-card form { display: flex; flex-direction: column; gap: 22px; }
.current { display: flex; flex-direction: column; gap: 4px; padding-bottom: 20px; border-bottom: 1px solid var(--border); }.eyebrow { font-size: 11px; letter-spacing: .08em; color: var(--text); }.current strong { color: var(--text-h); font-size: 20px; }.current small { color: var(--text); }
fieldset { display: flex; gap: 20px; padding: 0 0 20px; border: 0; border-bottom: 1px solid var(--border); }legend { margin-bottom: 10px; color: var(--text-h); font-size: 13px; font-weight: 600; }.choice { display: flex; flex-direction: row; align-items: center; gap: 7px; color: var(--text-h); font-size: 14px; }.choice input { width: auto; }.form-grid, .recurrence-panel { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }.recurrence-panel { padding-top: 16px; }label { display: flex; flex-direction: column; gap: 6px; color: var(--text-h); font-size: 13px; font-weight: 500; }input, select { width: 100%; box-sizing: border-box; padding: 11px 12px; color: var(--text-h); background: var(--bg); border: 1px solid var(--border); border-radius: 7px; font: inherit; }small { color: var(--text); font-weight: 400; }.preview { margin: 0; padding: 14px 16px; color: var(--accent); background: var(--accent-bg); border-radius: 7px; font-size: 14px; }.form-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding-top: 4px; }.button { padding: 10px 16px; border: 0; border-radius: 8px; color: #fff; background: var(--accent); font: inherit; font-weight: 600; text-decoration: none; cursor: pointer; }.button-secondary { color: var(--text-h); background: var(--code-bg); border: 1px solid var(--border); }.danger { color: #b42318; background: transparent; border: 1px solid rgba(180,35,24,.3); }.button:disabled { opacity: .6; cursor: not-allowed; }.alert { padding: 12px 16px; border-radius: 8px; font-size: 14px; }.alert-error { color: #b42318; background: rgba(180,35,24,.08); }.alert-success { color: #067647; background: rgba(6,118,71,.08); }.empty-state { color: var(--text); }
@media (max-width: 620px) { .form-grid, .recurrence-panel { grid-template-columns: 1fr; } fieldset { flex-direction: column; gap: 10px; } }
</style>
