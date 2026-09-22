<script setup>
import { onMounted, ref } from "vue";
import Icon from "../components/Icon.vue";
import { listCompanies } from "../services/companiesApi";
import { createCurrencyTask, deleteCurrencyTask, listCurrencyTasks, runCurrencyTask, updateCurrencyTask } from "../services/currencyTasksApi";
import { extractErrorMessage } from "../utils/format";

const tasks = ref([]);
const companies = ref([]);
const loading = ref(true);
const saving = ref(false);
const runningId = ref(null);
const error = ref("");
const message = ref("");
const showForm = ref(false);
const editingTask = ref(null);
const showSchedule = ref(false);
const schedulingTask = ref(null);
const scheduleTime = ref("08:00");
const currencyOptions = ["USD", "EUR", "GBP", "JPY", "SEK", "MX", "GTQ", "CHF", "PAB"];
const defaultTargets = ["EUR", "GBP", "JPY", "SEK", "MX", "GTQ", "CHF"];
const form = ref(emptyForm());

function emptyForm() {
  return { name: "", company_id: "", local_currency: "USD", target_currencies: [...defaultTargets], run_at: "08:00", mail_to: "", mail_cc: "", is_active: true };
}

async function load() {
  try { [tasks.value, companies.value] = await Promise.all([listCurrencyTasks(), listCompanies()]); }
  catch (err) { error.value = extractErrorMessage(err, "No se pudieron cargar las tareas de monedas"); }
  finally { loading.value = false; }
}

function openCreate() {
  editingTask.value = null;
  form.value = { ...emptyForm(), company_id: companies.value[0]?.id || "" };
  error.value = "";
  showForm.value = true;
}

function openEdit(task) {
  editingTask.value = task;
  form.value = {
    name: task.name,
    company_id: task.company_id,
    local_currency: task.local_currency,
    target_currencies: [...task.target_currencies],
    run_at: String(task.run_at).slice(0, 5),
    mail_to: task.mail_to,
    mail_cc: task.mail_cc || "",
    is_active: task.is_active,
  };
  error.value = "";
  showForm.value = true;
}

async function save() {
  if (!form.value.name || !form.value.company_id || !form.value.mail_to || !form.value.target_currencies.length) {
    error.value = "Completa filial, nombre, destinatario y monedas destino.";
    return;
  }
  saving.value = true;
  error.value = "";
  try {
    const payload = { ...form.value, company_id: Number(form.value.company_id), mail_cc: form.value.mail_cc || null };
    if (editingTask.value) {
      await updateCurrencyTask(editingTask.value.id, payload);
      message.value = "Tarea de cambio de moneda actualizada.";
    } else {
      await createCurrencyTask(payload);
      message.value = "Tarea de cambio de moneda creada.";
    }
    showForm.value = false;
    await load();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo guardar la tarea de monedas");
  } finally { saving.value = false; }
}

function openSchedule(task) {
  schedulingTask.value = task;
  scheduleTime.value = String(task.run_at).slice(0, 5);
  error.value = "";
  showSchedule.value = true;
}

async function saveSchedule() {
  saving.value = true;
  error.value = "";
  try {
    const task = schedulingTask.value;
    const payload = {
      name: task.name,
      company_id: task.company_id,
      local_currency: task.local_currency,
      target_currencies: task.target_currencies,
      rate_api_url: task.rate_api_url,
      run_at: scheduleTime.value,
      mail_to: task.mail_to,
      mail_cc: task.mail_cc || null,
      is_active: task.is_active,
    };
    await updateCurrencyTask(task.id, payload);
    message.value = `"${task.name}" programada a las ${scheduleTime.value}.`;
    showSchedule.value = false;
    await load();
  } catch (err) {
    error.value = extractErrorMessage(err, "No se pudo programar la tarea");
  } finally {
    saving.value = false;
  }
}

async function run(task) {
  runningId.value = task.id;
  error.value = "";
  try {
    const result = await runCurrencyTask(task.id);
    message.value = `${task.name}: ${result.updated.length} monedas actualizadas.`;
  } catch (err) { error.value = extractErrorMessage(err, "No se pudo ejecutar la tarea"); }
  finally { runningId.value = null; }
}

async function remove(task) {
  if (!window.confirm(`¿Eliminar la tarea ${task.name}?`)) return;
  try { await deleteCurrencyTask(task.id); await load(); message.value = "Tarea eliminada."; }
  catch (err) { error.value = extractErrorMessage(err, "No se pudo eliminar la tarea"); }
}

onMounted(load);
</script>

<template>
  <section class="currency-page">
    <header class="page-header"><div><h1>Tareas de cambio de monedas</h1><p class="subtitle">Actualiza diariamente las tasas en ORTT por filial mediante SAP Service Layer.</p></div><button class="icon-button primary" data-tooltip="Nueva tarea de monedas" @click="openCreate"><Icon name="plus" /></button></header>
    <p v-if="message" class="alert success">{{ message }}</p><p v-if="error" class="alert error">{{ error }}</p>
    <div class="card"><p v-if="loading" class="empty">Cargando tareas…</p><p v-else-if="!tasks.length" class="empty">No hay tareas de cambio de moneda configuradas.</p><table v-else class="table"><thead><tr><th>Tarea</th><th>Filial</th><th>Moneda local</th><th>Monedas destino</th><th>Hora diaria</th><th>Acciones</th></tr></thead><tbody><tr v-for="task in tasks" :key="task.id"><td class="strong"><span class="status-dot" :class="task.is_active ? 'active' : 'inactive'" :data-tooltip="task.is_active ? 'Activa' : 'Inactiva'"></span>{{ task.name }}</td><td>{{ task.company_name }}</td><td>{{ task.local_currency }}</td><td>{{ task.target_currencies.join(", ") }}</td><td>{{ task.run_at }}</td><td class="actions"><button class="icon-button" :disabled="runningId === task.id" :data-tooltip="runningId === task.id ? 'Ejecutando…' : 'Ejecutar ahora'" @click="run(task)"><Icon name="play" /></button><button class="icon-button" data-tooltip="Editar" @click="openEdit(task)"><Icon name="edit" /></button><button class="icon-button" data-tooltip="Programar" @click="openSchedule(task)"><Icon name="schedule" /></button><button class="icon-button delete" data-tooltip="Eliminar" @click="remove(task)"><Icon name="trash" /></button></td></tr></tbody></table></div>
    <div v-if="showSchedule" class="backdrop"><form class="modal schedule-modal" @submit.prevent="saveSchedule"><h2>Programar "{{ schedulingTask?.name }}"</h2><p class="subtitle">Hora diaria en que se actualizan las tasas de cambio.</p><label>Hora de ejecución<input v-model="scheduleTime" type="time" required /></label><div class="modal-actions"><button type="button" class="secondary" @click="showSchedule = false">Cancelar</button><button class="primary-button" :disabled="saving">{{ saving ? "Guardando…" : "Guardar programación" }}</button></div></form></div>
    <div v-if="showForm" class="backdrop"><form class="modal" @submit.prevent="save"><h2>{{ editingTask ? "Editar tarea de cambio de monedas" : "Nueva tarea de cambio de monedas" }}</h2><label>Nombre<input v-model="form.name" placeholder="Tasas diarias por filial" required /></label><label>Filial<select v-model="form.company_id" required><option value="" disabled>Selecciona una empresa</option><option v-for="company in companies" :key="company.id" :value="company.id">{{ company.name }} · {{ company.company_db }}</option></select></label><div class="grid"><label>Moneda local<select v-model="form.local_currency"><option v-for="currency in currencyOptions" :key="currency" :value="currency">{{ currency }}</option></select></label><label>Hora de ejecución<input v-model="form.run_at" type="time" required /></label></div><fieldset><legend>Monedas a actualizar</legend><label v-for="currency in currencyOptions" :key="currency" class="check"><input v-model="form.target_currencies" type="checkbox" :value="currency" :disabled="currency === form.local_currency" /> {{ currency }}</label></fieldset><label>Correo destinatario<input v-model="form.mail_to" type="email" required /></label><label>CC<input v-model="form.mail_cc" placeholder="opcional" /></label><label v-if="editingTask" class="check"><input v-model="form.is_active" type="checkbox" /> Tarea activa</label><div class="modal-actions"><button type="button" class="secondary" @click="showForm = false">Cancelar</button><button class="primary-button" :disabled="saving">{{ saving ? "Guardando…" : editingTask ? "Guardar cambios" : "Crear tarea" }}</button></div></form></div>
  </section>
</template>

<style scoped>
.currency-page{display:flex;flex-direction:column;gap:20px}.page-header{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}h1{font-size:24px;margin:0 0 4px}.subtitle{color:var(--text)}.card{overflow:auto;background:var(--bg);border:1px solid var(--border);border-radius:12px;box-shadow:var(--shadow);padding:8px 24px}.table{width:100%;min-width:850px;border-collapse:collapse}.table th,.table td{padding:13px 10px;text-align:left;border-bottom:1px solid var(--border);font-size:13px}.table th{color:var(--text);font-size:12px;text-transform:uppercase}.table tr:last-child td{border-bottom:0}.strong{color:var(--text-h);font-weight:600}small{display:block;color:var(--text);margin-top:3px}.actions{display:flex;gap:8px;white-space:nowrap}.primary-button,.secondary{padding:9px 13px;border:1px solid var(--border);border-radius:7px;background:var(--code-bg);color:var(--text-h);cursor:pointer}.primary-button{color:#fff;background:var(--accent);border:0;font-weight:600}.primary-button:disabled{opacity:.6;cursor:wait}.icon-button{position:relative;display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;padding:0;border:1px solid var(--border);border-radius:7px;background:var(--code-bg);color:var(--text-h);cursor:pointer}.icon-button:disabled{opacity:.6;cursor:wait}.icon-button.delete{color:#b42318}.icon-button.primary{width:40px;height:40px;border:0;border-radius:9px;background:var(--accent);color:#fff}.icon-button[data-tooltip]::after,.status-dot[data-tooltip]::after{content:attr(data-tooltip);position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%) scale(.96);padding:5px 9px;border-radius:6px;background:#111827;color:#fff;font-size:12px;font-weight:500;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,.2);opacity:0;visibility:hidden;transition:opacity .12s ease,transform .12s ease;pointer-events:none;z-index:5}.icon-button[data-tooltip]:hover::after,.icon-button[data-tooltip]:focus-visible::after,.status-dot[data-tooltip]:hover::after{opacity:1;visibility:visible;transform:translateX(-50%) scale(1)}.status-dot{position:relative;display:inline-block;width:9px;height:9px;margin-right:8px;border-radius:50%;vertical-align:middle}.status-dot.active{background:#16a34a;box-shadow:0 0 0 3px rgba(22,163,74,.15)}.status-dot.inactive{background:#dc2626;box-shadow:0 0 0 3px rgba(220,38,38,.15)}.empty{text-align:center;color:var(--text);padding:30px}.alert{padding:12px 16px;border-radius:8px}.success{color:#067647;background:rgba(6,118,71,.08)}.error{color:#b42318;background:rgba(180,35,24,.08)}.backdrop{position:fixed;z-index:20;inset:0;display:grid;place-items:center;padding:20px;background:rgba(9,12,22,.65)}.modal{width:min(560px,100%);max-height:calc(100vh - 40px);overflow:auto;display:flex;flex-direction:column;gap:16px;padding:24px;background:var(--bg);border-radius:10px;box-shadow:0 24px 60px rgba(0,0,0,.25)}h2{margin:0;color:var(--text-h);font-size:19px}label,legend{color:var(--text-h);font-size:13px;font-weight:600}label{display:flex;flex-direction:column;gap:6px}input,select{box-sizing:border-box;width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:7px;background:var(--bg);color:var(--text-h);font:inherit}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}fieldset{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;border:1px solid var(--border);border-radius:7px;padding:14px}.check{display:flex;flex-direction:row;align-items:center;gap:5px;font-weight:400}.check input{width:auto}.modal-actions{display:flex;justify-content:flex-end;gap:10px}.schedule-modal{width:min(380px,100%)}@media(max-width:650px){.grid,fieldset{grid-template-columns:1fr 1fr}}
</style>
