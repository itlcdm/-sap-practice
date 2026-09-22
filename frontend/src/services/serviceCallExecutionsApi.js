import api from "./api";

export function listServiceCallExecutions(taskId = undefined, { limit = 20, offset = 0 } = {}) {
  return api
    .get("/api/service-call-executions", { params: { task_id: taskId, limit, offset } })
    .then((r) => r.data);
}

export function getServiceCallExecution(executionId) {
  return api.get(`/api/service-call-executions/${executionId}`).then((r) => r.data);
}

export function listServiceCallExecutionItems(executionId, { status, limit = 100, offset = 0 } = {}) {
  return api
    .get(`/api/service-call-executions/${executionId}/items`, { params: { status, limit, offset } })
    .then((r) => r.data);
}

export function retryFailedItems(executionId) {
  return api.post(`/api/service-call-executions/${executionId}/retry-failed`).then((r) => r.data);
}
