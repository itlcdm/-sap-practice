import api from "./api";

export function listCurrencyTasks() {
  return api.get("/api/currency-tasks").then((response) => response.data);
}

export function createCurrencyTask(payload) {
  return api.post("/api/currency-tasks", payload).then((response) => response.data);
}

export function runCurrencyTask(id) {
  return api.post(`/api/currency-tasks/${id}/run`).then((response) => response.data);
}

export function deleteCurrencyTask(id) {
  return api.delete(`/api/currency-tasks/${id}`);
}

export function updateCurrencyTask(id, payload) {
  return api.put(`/api/currency-tasks/${id}`, payload).then((response) => response.data);
}
export function listCurrencyExecutions(params = {}) {
  return api.get("/api/currency-tasks/executions", { params }).then((response) => response.data);
}

export function getCurrencyExecution(id) {
  return api.get(`/api/currency-tasks/executions/${id}`).then((response) => response.data);
}
