"""Håndtering av rapportering og varsler."""
from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable, Optional

from .portfolio_manager import TradeLogEntry


@dataclass(slots=True)
class ReportChannel:
    """Konfigurasjon av rapporteringskanaler."""

    email_recipient: Optional[str] = None
    email_sender: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587


class WeeklyReporter:
    def __init__(self, output_directory: Path, channel: ReportChannel | None = None) -> None:
        self.output_directory = output_directory
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.channel = channel or ReportChannel()

    def render_report(self, trade_log: Iterable[TradeLogEntry]) -> str:
        lines = ["Ukentlig rapport", "================", ""]
        for entry in trade_log:
            lines.append(
                f"{entry.timestamp:%Y-%m-%d %H:%M} {entry.action} {entry.symbol} x{entry.quantity} til {entry.price:.2f} NOK - {entry.note}"
            )
        if len(lines) == 3:
            lines.append("Ingen handler denne uken.")
        return "\n".join(lines)

    def write_report_to_file(self, report_text: str, filename: str = "weekly_report.txt") -> Path:
        path = self.output_directory / filename
        path.write_text(report_text, encoding="utf-8")
        return path

    def send_email_report(self, report_text: str) -> None:
        if not (self.channel.email_recipient and self.channel.email_sender and self.channel.smtp_host):
            return

        message = EmailMessage()
        message["Subject"] = "Salgsmester – ukentlig rapport"
        message["From"] = self.channel.email_sender
        message["To"] = self.channel.email_recipient
        message.set_content(report_text)

        import smtplib

        with smtplib.SMTP(self.channel.smtp_host, self.channel.smtp_port) as smtp:
            smtp.starttls()
            smtp.send_message(message)
