import api from "./api";

export function getAppSettings() {
  return api.get("/api/settings/app").then((r) => r.data);
}

export function updateAppSettings(payload) {
  return api.put("/api/settings/app", payload).then((r) => r.data);
}

export function getMailSettings() {
  return api.get("/api/settings/mail").then((r) => r.data);
}

export function updateMailSettings(payload) {
  return api.put("/api/settings/mail", payload).then((r) => r.data);
}

export function sendTestEmail(to) {
  return api.post("/api/settings/mail/test-email", { to }).then((r) => r.data);
}

export function listSqlConnections() {
  return api.get("/api/settings/sql-connections").then((r) => r.data);
}

export function createSqlConnection(payload) {
  return api.post("/api/settings/sql-connections", payload).then((r) => r.data);
}

export function updateSqlConnection(id, payload) {
  return api.put(`/api/settings/sql-connections/${id}`, payload).then((r) => r.data);
}

export function deleteSqlConnection(id) {
  return api.delete(`/api/settings/sql-connections/${id}`);
}

export function getAuthInfo() {
  return api.get("/api/settings/auth").then((r) => r.data);
}

export function getPostgresSettings() {
  return api.get("/api/settings/postgres").then((r) => r.data);
}
