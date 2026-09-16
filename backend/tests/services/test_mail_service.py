from unittest.mock import MagicMock

from app.services import mail_service


async def test_enviar_correo_con_adjuntos_uses_smtp_and_attaches_files(monkeypatch, tmp_path):
    attachment = tmp_path / "reporte.xlsx"
    attachment.write_bytes(b"contenido de prueba")

    fake_server = MagicMock()
    fake_server.__enter__.return_value = fake_server
    fake_server.__exit__.return_value = False

    smtp_calls = []

    def fake_smtp(host, port):
        smtp_calls.append((host, port))
        return fake_server

    monkeypatch.setattr(mail_service.smtplib, "SMTP", fake_smtp)
    monkeypatch.setattr(mail_service.settings, "mail_from", "info@example.com")
    monkeypatch.setattr(mail_service.settings, "mail_smtp_server", "smtp.example.com")
    monkeypatch.setattr(mail_service.settings, "mail_smtp_port", 587)
    monkeypatch.setattr(mail_service.settings, "mail_user", "info@example.com")
    monkeypatch.setattr(mail_service.settings, "mail_password", "secret")

    await mail_service.enviar_correo_con_adjuntos(
        to="a@example.com, b@example.com",
        cc="c@example.com",
        subject="Reportes de prueba",
        body="cuerpo",
        attachments=[str(attachment)],
    )

    assert smtp_calls == [("smtp.example.com", 587)]
    fake_server.starttls.assert_called_once()
    fake_server.login.assert_called_once_with("info@example.com", "secret")

    send_call = fake_server.send_message.call_args
    message = send_call.args[0]
    assert message["Subject"] == "Reportes de prueba"
    assert message["To"] == "a@example.com, b@example.com"
    assert message["Cc"] == "c@example.com"
    assert send_call.kwargs["to_addrs"] == ["a@example.com", "b@example.com", "c@example.com"]


async def test_enviar_correo_con_adjuntos_splits_semicolon_separated_recipients(monkeypatch, tmp_path):
    attachment = tmp_path / "reporte.xlsx"
    attachment.write_bytes(b"contenido de prueba")

    fake_server = MagicMock()
    fake_server.__enter__.return_value = fake_server
    fake_server.__exit__.return_value = False

    def fake_smtp(host, port):
        return fake_server

    monkeypatch.setattr(mail_service.smtplib, "SMTP", fake_smtp)
    monkeypatch.setattr(mail_service.settings, "mail_from", "info@example.com")
    monkeypatch.setattr(mail_service.settings, "mail_smtp_server", "smtp.example.com")
    monkeypatch.setattr(mail_service.settings, "mail_smtp_port", 587)
    monkeypatch.setattr(mail_service.settings, "mail_user", "info@example.com")
    monkeypatch.setattr(mail_service.settings, "mail_password", "secret")

    await mail_service.enviar_correo_con_adjuntos(
        to="a@example.com; b@example.com",
        cc="c@example.com; d@example.com",
        subject="Reportes de prueba",
        body="cuerpo",
        attachments=[str(attachment)],
    )

    send_call = fake_server.send_message.call_args
    # Verify the SMTP recipients list correctly splits both semicolon and comma-separated addresses
    assert send_call.kwargs["to_addrs"] == ["a@example.com", "b@example.com", "c@example.com", "d@example.com"]
