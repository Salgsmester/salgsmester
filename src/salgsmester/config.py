"""Konfigurasjonsmodeller og -lastere for Salgsmester-tradingplattformen."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class NordnetCredentials:
    """Holder på opplysninger som trengs for å autentisere mot Nordnet.

    Brukeren må selv fylle inn informasjonen før programmet kan logge inn.
    """

    username: str
    password: str
    secret_key: Optional[str] = None
    account_id: Optional[str] = None


@dataclass(slots=True)
class StrategyTargets:
    """Målparametere for strategien.

    Verdiene er ønskede mål og kan ikke garanteres.
    """

    weekly_growth_target: float = 0.05
    max_portfolio_volatility: float = 0.25
    min_trades_per_week: int = 1
    rebalance_cadence: timedelta = field(default_factory=lambda: timedelta(days=1))


@dataclass(slots=True)
class FeeStructure:
    """Representerer faste og variable kostnader knyttet til handler."""

    fixed_fee: float = 29.0
    variable_fee_rate: float = 0.00055


@dataclass(slots=True)
class AppConfig:
    """Samler konfigurasjon for applikasjonen."""

    credentials: NordnetCredentials
    strategy: StrategyTargets = field(default_factory=StrategyTargets)
    fees: FeeStructure = field(default_factory=FeeStructure)
    data_directory: Path = field(default_factory=lambda: Path("data"))


def load_config_from_env() -> AppConfig:
    """Laster konfigurering fra miljøvariabler.

    Funksjonen leser kun verdier som er tilgjengelige og overlater til brukeren å
    sette resten manuelt. Dette gjør det mulig å benytte Git-repositoriet uten å
    sjekke inn sensitiv informasjon.
    """

    import os

    credentials = NordnetCredentials(
        username=os.environ.get("SALGSMESTER_NORDNET_USERNAME", ""),
        password=os.environ.get("SALGSMESTER_NORDNET_PASSWORD", ""),
        secret_key=os.environ.get("SALGSMESTER_NORDNET_SECRET"),
        account_id=os.environ.get("SALGSMESTER_ACCOUNT_ID"),
    )

    strategy = StrategyTargets(
        weekly_growth_target=float(
            os.environ.get("SALGSMESTER_WEEKLY_TARGET", 0.05)
        ),
        max_portfolio_volatility=float(
            os.environ.get("SALGSMESTER_MAX_VOL", 0.25)
        ),
        min_trades_per_week=int(os.environ.get("SALGSMESTER_MIN_TRADES", 1)),
    )

    fees = FeeStructure(
        fixed_fee=float(os.environ.get("SALGSMESTER_FIXED_FEE", 29.0)),
        variable_fee_rate=float(
            os.environ.get("SALGSMESTER_VARIABLE_FEE", 0.00055)
        ),
    )

    data_directory = Path(
        os.environ.get("SALGSMESTER_DATA_DIR", "data")
    )

    return AppConfig(
        credentials=credentials,
        strategy=strategy,
        fees=fees,
        data_directory=data_directory,
    )
