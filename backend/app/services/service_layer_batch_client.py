import asyncio
import logging
import re
import uuid
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 2.0


async def _request_with_retry(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    """SAP Service Layer a veces cierra la conexión a mitad de una respuesta
    (httpx.ReadError/ConnectError). Estos son errores transitorios de red, no
    de negocio, así que se reintentan con backoff antes de dejar que fallen
    hacia arriba y arrastren un lote completo a needs_review."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt == _MAX_RETRIES:
                break
            logger.warning(
                "[LLAMADAS] Error de red en %s %s (intento %s/%s): %s",
                method, url, attempt, _MAX_RETRIES, exc,
            )
            await asyncio.sleep(_RETRY_BACKOFF_SECONDS * attempt)
    raise last_exc

_HTTP_BLOCK_RE = re.compile(
    r"HTTP/1\.[01]\s+(?P<status>\d{3})[^\r\n]*\r?\n(?P<content>.*?)(?=HTTP/1\.[01]\s+\d{3}|\Z)",
    re.DOTALL | re.IGNORECASE,
)
_CONTENT_ID_RE = re.compile(r"Content-ID:\s*(?P<id>\d+)", re.IGNORECASE)
_MULTIPART_BOUNDARY_RE = re.compile(r"(?m)^--[A-Za-z0-9_-]+--?\s*$")


@dataclass
class BatchItemResult:
    item_id: int
    success: bool
    http_status_code: int | None
    response_body: str
    needs_review: bool = False


async def _login(client: httpx.AsyncClient, base_url: str, company_db: str, username: str, password: str) -> str:
    response = await _request_with_retry(
        client,
        "POST",
        f"{base_url}/Login",
        json={"CompanyDB": company_db, "UserName": username, "Password": password},
    )
    response.raise_for_status()
    session_id = response.json().get("SessionId")
    if not session_id:
        raise RuntimeError("Service Layer no devolvió SessionId.")
    return session_id


def _build_batch_body(items: list[tuple[int, str]]) -> tuple[str, str]:
    """items: lista de (item_id, payload_json). Devuelve (boundary, body)."""
    batch_boundary = f"batch_{uuid.uuid4().hex}"
    parts = []

    for index, (_item_id, payload_json) in enumerate(items, start=1):
        changeset_boundary = f"changeset_{uuid.uuid4().hex}"
        parts.append(f"--{batch_boundary}\r\n")
        parts.append(f"Content-Type: multipart/mixed; boundary={changeset_boundary}\r\n\r\n")
        parts.append(f"--{changeset_boundary}\r\n")
        parts.append("Content-Type: application/http\r\n")
        parts.append("Content-Transfer-Encoding: binary\r\n")
        parts.append(f"Content-ID: {index}\r\n\r\n")
        parts.append("POST /b1s/v1/ServiceCalls HTTP/1.1\r\n")
        parts.append("Content-Type: application/json\r\n\r\n")
        parts.append(payload_json)
        parts.append("\r\n")
        parts.append(f"--{changeset_boundary}--\r\n")

    parts.append(f"--{batch_boundary}--\r\n")
    return batch_boundary, "".join(parts)


def _clean_multipart_content(value: str) -> str:
    return _MULTIPART_BOUNDARY_RE.sub("", value).strip()


def _extract_message(content: str) -> str:
    import json as _json

    if not content.strip():
        return content

    try:
        data = _json.loads(content)
    except ValueError:
        return content

    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message
        if isinstance(message, dict):
            value = message.get("value")
            if isinstance(value, str):
                return value
            return " ".join(f"{k}: {v}" for k, v in message.items())
        return str(error)

    return content


def _parse_batch_response(items: list[tuple[int, str]], response_text: str) -> list[BatchItemResult]:
    http_matches = list(_HTTP_BLOCK_RE.finditer(response_text))
    id_matches = list(_CONTENT_ID_RE.finditer(response_text))

    results: list[BatchItemResult | None] = [None] * len(items)

    associated: dict[int, re.Match] = {}
    for id_match in id_matches:
        content_id = int(id_match.group("id"))
        candidate = next((m for m in http_matches if m.start() > id_match.start()), None)
        if candidate is not None:
            associated[content_id] = candidate

    used_spans = set()
    for content_id, match in associated.items():
        idx = content_id - 1
        if not (0 <= idx < len(items)):
            continue
        status = int(match.group("status"))
        raw_content = _clean_multipart_content(match.group("content"))
        message = _extract_message(raw_content)
        results[idx] = BatchItemResult(
            item_id=items[idx][0],
            success=200 <= status <= 299,
            http_status_code=status,
            response_body=message[:8000],
        )
        used_spans.add(match.start())

    fallback = [m for m in http_matches if m.start() not in used_spans]
    fb_index = 0
    for idx in range(len(items)):
        if results[idx] is not None or fb_index >= len(fallback):
            continue
        match = fallback[fb_index]
        fb_index += 1
        status = int(match.group("status"))
        raw_content = _clean_multipart_content(match.group("content"))
        message = _extract_message(raw_content)
        results[idx] = BatchItemResult(
            item_id=items[idx][0],
            success=200 <= status <= 299,
            http_status_code=status,
            response_body=message[:8000],
        )

    return [
        r
        if r is not None
        else BatchItemResult(
            item_id=items[i][0],
            success=False,
            http_status_code=None,
            response_body="No fue posible asociar una respuesta de SAP a este elemento.",
            needs_review=True,
        )
        for i, r in enumerate(results)
    ]


async def create_service_calls_batch(
    base_url: str,
    company_db: str,
    username: str,
    password: str,
    items: list[tuple[int, str]],
) -> list[BatchItemResult]:
    """items: lista de (item_id, payload_json). Crea las ServiceCalls en SAP B1 vía $batch OData."""
    if not items:
        return []

    base_url = base_url.rstrip("/")

    async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
        session_id = await _login(client, base_url, company_db, username, password)
        boundary, body = _build_batch_body(items)

        response = await _request_with_retry(
            client,
            "POST",
            f"{base_url}/$batch",
            content=body.encode("utf-8"),
            headers={
                "Cookie": f"B1SESSION={session_id}",
                "Content-Type": f"multipart/mixed; boundary={boundary}",
                "Accept": "application/json",
            },
        )

        if response.status_code == 401:
            session_id = await _login(client, base_url, company_db, username, password)
            response = await _request_with_retry(
                client,
                "POST",
                f"{base_url}/$batch",
                content=body.encode("utf-8"),
                headers={
                    "Cookie": f"B1SESSION={session_id}",
                    "Content-Type": f"multipart/mixed; boundary={boundary}",
                    "Accept": "application/json",
                },
            )

        try:
            await client.post(f"{base_url}/Logout", json={})
        except Exception:
            logger.warning("[LLAMADAS] No se pudo cerrar sesión en Service Layer (company_db=%s)", company_db)

        if not response.is_success:
            text = response.text[:8000]
            logger.warning(
                "[LLAMADAS] Batch falló company_db=%s status=%s: %s", company_db, response.status_code, text
            )
            return [
                BatchItemResult(item_id=item_id, success=False, http_status_code=response.status_code, response_body=text)
                for item_id, _ in items
            ]

        return _parse_batch_response(items, response.text)
