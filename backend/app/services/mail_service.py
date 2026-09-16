import asyncio
import smtplib
from email.message import EmailMessage

from app.config import settings


def _send_sync(to: str, cc: str | None, subject: str, body: str, attachments: list[str]) -> None:
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    if cc:
        message["Cc"] = cc
    message["Subject"] = subject
    message.set_content(body)

    for path in attachments:
        with open(path, "rb") as f:
            data = f.read()

        file_name = path.replace("\\", "/").rsplit("/", 1)[-1]
        message.add_attachment(
            data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=file_name,
        )

    recipients = [addr.strip() for addr in to.replace(";", ",").split(",") if addr.strip()]
    if cc:
        recipients += [addr.strip() for addr in cc.replace(";", ",").split(",") if addr.strip()]

    with smtplib.SMTP(settings.mail_smtp_server, settings.mail_smtp_port) as server:
        server.starttls()
        server.login(settings.mail_user, settings.mail_password)
        server.send_message(message, to_addrs=recipients)


async def enviar_correo_con_adjuntos(
    to: str, cc: str | None, subject: str, body: str, attachments: list[str]
) -> None:
    await asyncio.to_thread(_send_sync, to, cc, subject, body, attachments)
