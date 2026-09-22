import api from "./api";

export function listCompanies() {
  return api.get("/api/companies").then((response) => response.data);
}

export function createCompany(payload) {
  return api.post("/api/companies", payload).then((response) => response.data);
}

export function updateCompany(id, payload) {
  return api.put(`/api/companies/${id}`, payload).then((response) => response.data);
}

export function deleteCompany(id) {
  return api.delete(`/api/companies/${id}`);
}

export function testCompanyConnection(id) {
  return api.post(`/api/companies/${id}/test-connection`).then((response) => response.data);
}
