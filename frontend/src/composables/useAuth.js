import { ref } from "vue";
import api from "../services/api";

const STORAGE_KEY = "sap_authenticated";

const isAuthenticated = ref(sessionStorage.getItem(STORAGE_KEY) === "true");

async function login(email, password) {
  await api.post("/api/auth/login", { email, password });

  sessionStorage.setItem(STORAGE_KEY, "true");
  isAuthenticated.value = true;
}

function logout() {
  sessionStorage.removeItem(STORAGE_KEY);
  isAuthenticated.value = false;
}

export function useAuth() {
  return { isAuthenticated, login, logout };
}
