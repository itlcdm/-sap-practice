export function formatDateTime(value) {
  if (!value) return "—";

  return new Date(value).toLocaleString("es-PA", {
    dateStyle: "short",
    timeStyle: "medium",
  });
}

export function extractErrorMessage(err, fallback) {
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }

  return fallback;
}
