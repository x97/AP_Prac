from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings
from app.core.security import mask_email

logger = logging.getLogger("app.email")

PURPOSE_LABELS = {
    "register": "注册",
    "reset": "重置密码",
    "bind_email": "绑定邮箱",
}


class EmailSender:
    def send_code(self, email: str, code: str, purpose: str) -> None:  # pragma: no cover
        raise NotImplementedError


class DevEmailSender(EmailSender):
    def send_code(self, email: str, code: str, purpose: str) -> None:
        logger.warning(
            "DEV email code for %s (%s): %s", mask_email(email), purpose, code
        )


class SmtpEmailSender(EmailSender):
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_code(self, email: str, code: str, purpose: str) -> None:
        if not (self.settings.smtp_host and self.settings.smtp_from):
            raise RuntimeError("SMTP_HOST and SMTP_FROM are not configured")

        label = PURPOSE_LABELS.get(purpose, "验证")
        message = EmailMessage()
        message["Subject"] = f"PsyPrac {label}验证码"
        message["From"] = self.settings.smtp_from
        message["To"] = email
        message.set_content(
            "你正在完成 PsyPrac 的"
            f"{label}操作，验证码是 {code}。\n\n"
            "验证码 5 分钟内有效，请勿转发给他人。\n"
            "如果不是你本人操作，请忽略这封邮件。"
        )

        try:
            if self.settings.smtp_ssl:
                client = smtplib.SMTP_SSL(
                    self.settings.smtp_host, self.settings.smtp_port, timeout=15
                )
            else:
                client = smtplib.SMTP(
                    self.settings.smtp_host, self.settings.smtp_port, timeout=15
                )
            with client:
                client.ehlo()
                if self.settings.smtp_starttls and not self.settings.smtp_ssl:
                    client.starttls()
                    client.ehlo()
                if self.settings.smtp_username:
                    client.login(
                        self.settings.smtp_username, self.settings.smtp_password
                    )
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            logger.exception(
                "failed to send verification email to %s", mask_email(email)
            )
            raise RuntimeError("verification email delivery failed") from exc


def get_email_sender(settings: Settings) -> EmailSender:
    if settings.email_provider == "dev":
        return DevEmailSender()
    if settings.email_provider == "smtp":
        return SmtpEmailSender(settings)
    raise RuntimeError(f"unknown email provider: {settings.email_provider}")
