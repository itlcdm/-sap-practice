import api from "./api";

export function listTasks() {
  return api.get("/api/tasks").then((r) => r.data);
}

export function getTask(id) {
  return api.get(`/api/tasks/${id}`).then((r) => r.data);
}

export function createTask(payload) {
  return api.post("/api/tasks", payload).then((r) => r.data);
}

export function updateTask(id, payload) {
  return api.put(`/api/tasks/${id}`, payload).then((r) => r.data);
}

export function runTask(id) {
  return api.post(`/api/tasks/${id}/run`).then((r) => r.data);
}

export function deleteTask(id) {
  return api.delete(`/api/tasks/${id}`);
}

export function createSchedule(id, payload) {
  return api.post(`/api/tasks/${id}/schedule`, payload).then((r) => r.data);
}

export function deleteSchedule(id) {
  return api.delete(`/api/tasks/${id}/schedule`);
}

export function listSchedules() {
  return api.get("/api/schedules").then((r) => r.data);
}

export function listExecutions(params = {}) {
  return api.get("/api/executions", { params }).then((r) => r.data);
}

export function getExecution(id) {
  return api.get(`/api/executions/${id}`).then((r) => r.data);
}

export function getExecutionLogs(id) {
  return api.get(`/api/executions/${id}/logs`).then((r) => r.data);
}

export function downloadReportUrl(executionId, reportId) {
  return `/api/executions/${executionId}/reports/${reportId}/download`;
}
