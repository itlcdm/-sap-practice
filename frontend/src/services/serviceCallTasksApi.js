import api from "./api";

export function listServiceCallTasks() {
  return api.get("/api/service-call-tasks").then((r) => r.data);
}

export function createServiceCallTask(payload) {
  return api.post("/api/service-call-tasks", payload).then((r) => r.data);
}

export function updateServiceCallTask(id, payload) {
  return api.put(`/api/service-call-tasks/${id}`, payload).then((r) => r.data);
}

export function deleteServiceCallTask(id) {
  return api.delete(`/api/service-call-tasks/${id}`);
}

export function previewServiceCallTask(id) {
  return api.get(`/api/service-call-tasks/${id}/preview`).then((r) => r.data);
}

export function runServiceCallTask(id, { batchSize = 20, dryRun = false } = {}) {
  return api
    .post(`/api/service-call-tasks/${id}/run`, { batch_size: batchSize, dry_run: dryRun })
    .then((r) => r.data);
}
