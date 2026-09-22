import logging
from datetime import date

import httpx

from app.services.app_settings_repository import app_settings_repository
from app.services.currency_task_repository import currency_task_repository

logger = logging.getLogger(__name__)


async def execute_currency_task(task_id: int, trigger_type: str = "manual") -> list[str]:
    execution_id = await currency_task_repository.create_execution(task_id, trigger_type)
    task = await currency_task_repository.get_execution_config(task_id)
    if task is None:
        await currency_task_repository.finish_execution(execution_id, "failed", "Tarea no encontrada o inactiva")
        raise LookupError("Tarea de cambio de moneda no encontrada o inactiva")

    base_url = task["service_layer_url"].rstrip("/")
    local_currency = task["local_currency"].upper()
    targets = [currency.upper() for currency in task["target_currencies"]]
    logger.info("[MONEDAS] Iniciando tarea=%s filial=%s moneda_local=%s", task_id, task["company_db"], local_currency)

    async with httpx.AsyncClient(verify=False, timeout=35.0) as client:
        login = await client.post(
            f"{base_url}/Login",
            json={"CompanyDB": task["company_db"], "UserName": task["username"], "Password": task["password"]},
        )
        login.raise_for_status()
        logger.info("[MONEDAS] Login Service Layer correcto: filial=%s", task["company_db"])

        try:
            usd_rates: dict[str, float] = {}
            for currency in set(targets + ([local_currency] if local_currency not in {"USD", "PAB"} else [])):
                if currency == "USD":
                    usd_rates[currency] = 1.0
                    continue
                response = await client.get(f"{task['rate_api_url'].rstrip('/')}/USD/{'MXN' if currency == 'MX' else currency}")
                response.raise_for_status()
                conversion_rate = response.json().get("conversion_rate")
                if not conversion_rate or float(conversion_rate) <= 0:
                    raise ValueError(f"Tasa inválida para USD/{currency}")
                usd_rates[currency] = float(conversion_rate)
                logger.info("[MONEDAS] Tasa externa USD/%s=%s", currency, conversion_rate)

            local_usd_rate = 1.0 if local_currency in {"USD", "PAB"} else usd_rates[local_currency]
            updated = []
            for currency in targets:
                if currency == local_currency:
                    continue
                rate = usd_rates.get(currency, 1.0) / local_usd_rate
                payload = {
                    "Currency": currency,
                    "Rate": f"{rate:.6f}",
                    "RateDate": date.today().strftime("%Y%m%d"),
                }
                response = await client.post(f"{base_url}/SBOBobService_SetCurrencyRate", json=payload)
                response.raise_for_status()
                updated.append(f"{local_currency} -> {currency}: {rate:.6f}")
                logger.info("[MONEDAS] ORTT actualizado filial=%s moneda=%s tasa=%.6f", task["company_db"], currency, rate)

            await _send_summary(task, updated)
            await currency_task_repository.finish_execution(execution_id, "success", updated_rates=updated)
            logger.info("[MONEDAS] Tarea completada: task_id=%s actualizadas=%s", task_id, len(updated))
            return updated
        except Exception as exc:
            await currency_task_repository.finish_execution(execution_id, "failed", str(exc))
            logger.exception("[MONEDAS] Error en tarea=%s", task_id)
            raise
        finally:
            try:
                await client.post(f"{base_url}/Logout", json={})
                logger.info("[MONEDAS] Logout Service Layer correcto: filial=%s", task["company_db"])
            except Exception as exc:
                logger.warning("[MONEDAS] Error en logout filial=%s: %s", task["company_db"], exc)


async def _send_summary(task: dict, updated: list[str]) -> None:
    mail_config = await app_settings_repository.get_mail_config()
    if not mail_config["mail_password"]:
        logger.warning("[MONEDAS] Correo omitido: no hay contraseña de correo configurada")
        return
    message = "\n".join(updated) or "No hubo monedas para actualizar."
    from email.message import EmailMessage
    import asyncio
    import smtplib

    def send_sync() -> None:
        email = EmailMessage()
        email["From"] = mail_config["mail_from"]
        email["To"] = task["mail_to"]
        if task["mail_cc"]:
            email["Cc"] = task["mail_cc"]
        email["Subject"] = f"Actualización de tasas SAP B1 ({task['company_db']})"
        email.set_content(f"La actualización se ejecutó correctamente el {date.today():%Y-%m-%d}.\n\n{message}")
        recipients = [item.strip() for item in task["mail_to"].replace(";", ",").split(",") if item.strip()]
        if task["mail_cc"]:
            recipients.extend(item.strip() for item in task["mail_cc"].replace(";", ",").split(",") if item.strip())
        with smtplib.SMTP(mail_config["smtp_server"], mail_config["smtp_port"]) as server:
            server.starttls()
            server.login(mail_config["mail_user"], mail_config["mail_password"])
            server.send_message(email, to_addrs=recipients)

    await asyncio.to_thread(send_sync)
    logger.info("[MONEDAS] Correo de resumen enviado: task_id=%s", task["id"])
