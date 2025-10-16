"""Kommandolinjegrensesnitt for Salgsmester."""
from __future__ import annotations

import argparse
from datetime import datetime

from .config import AppConfig, load_config_from_env
from .nordnet_client import NordnetClient
from .portfolio_manager import PortfolioManager
from .reporting import ReportChannel, WeeklyReporter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automatisert handelsrammeverk for Nordnet")
    parser.add_argument(
        "--report-email",
        help="E-postadresse som skal motta ukentlig rapport",
    )
    parser.add_argument(
        "--report-sender",
        help="E-postadresse som skal stå som avsender av rapporten",
    )
    parser.add_argument("--smtp-host", help="SMTP-vert for e-postutsendelse")
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=587,
        help="SMTP-port (standard 587)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Loggfør beslutninger uten å sende ordre til Nordnet",
    )
    return parser.parse_args()


def build_manager(config: AppConfig, dry_run: bool = False) -> PortfolioManager:
    client = NordnetClient(credentials=config.credentials, fees=config.fees)
    if not dry_run:
        client.authenticate()
    return PortfolioManager(client=client, targets=config.strategy, fees=config.fees)


def main() -> None:
    args = parse_args()
    config = load_config_from_env()
    manager = build_manager(config, dry_run=args.dry_run)

    now = datetime.utcnow()
    portfolio, decision = manager.run_daily_cycle(now)

    reporter = WeeklyReporter(
        output_directory=config.data_directory,
        channel=ReportChannel(
            email_recipient=args.report_email,
            email_sender=args.report_sender,
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
        ),
    )
    report_text = reporter.render_report(manager.trade_log)
    reporter.write_report_to_file(report_text)
    reporter.send_email_report(report_text)

    print("Porteføljeverdi:", portfolio.total_value())
    print("Beslutning:", decision.reason)


if __name__ == "__main__":
    main()
