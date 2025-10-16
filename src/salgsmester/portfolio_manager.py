"""Porteføljestyring og handelslogikk."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .config import FeeStructure, StrategyTargets
from .data_models import InstrumentSnapshot, Portfolio, Position
from .nordnet_client import NordnetClient
from .strategy import MomentumGrowthStrategy, TradeDecision


@dataclass(slots=True)
class TradeLogEntry:
    timestamp: datetime
    action: str
    symbol: str
    quantity: float
    price: float
    note: str


class PortfolioManager:
    def __init__(
        self,
        client: NordnetClient,
        targets: StrategyTargets,
        fees: FeeStructure,
    ) -> None:
        self.client = client
        self.strategy = MomentumGrowthStrategy(targets)
        self.fees = fees
        self.trade_log: list[TradeLogEntry] = []

    def run_daily_cycle(self, now: datetime) -> tuple[Portfolio, TradeDecision]:
        """Henter data, evaluerer strategi og utfører eventuelle handler."""

        portfolio = self.client.fetch_portfolio()
        instruments = self.client.fetch_instruments()
        decision = self.strategy.evaluate(now, portfolio, instruments)

        self._execute_sales(decision.sell_symbols, portfolio)
        self._execute_purchases(decision.buy_candidates, portfolio)

        return portfolio, decision

    def _execute_sales(self, symbols: Iterable[str], portfolio: Portfolio) -> None:
        for symbol in symbols:
            position = portfolio.remove_position(symbol)
            if position is None:
                continue
            quantity = position.quantity
            price = position.instrument.last_price
            self.client.place_order(symbol=symbol, quantity=quantity, side="sell")
            self.trade_log.append(
                TradeLogEntry(
                    timestamp=datetime.utcnow(),
                    action="SELL",
                    symbol=symbol,
                    quantity=quantity,
                    price=price,
                    note="Måloppnåelse utløste salg",
                )
            )
            portfolio.cash += quantity * price

    def _execute_purchases(
        self, candidates: Iterable[InstrumentSnapshot], portfolio: Portfolio
    ) -> None:
        available_cash = portfolio.cash
        if available_cash <= 0:
            return

        candidate_list = list(candidates)
        per_trade_budget = available_cash / max(len(candidate_list), 1)

        for candidate in candidate_list:
            if per_trade_budget <= 0:
                break
            price = candidate.last_price
            quantity = max(int(per_trade_budget // price), 0)
            if quantity <= 0:
                continue

            total_cost = self.client.estimate_trade_cost(price, quantity)
            if total_cost > portfolio.cash:
                continue

            self.client.place_order(symbol=candidate.symbol, quantity=quantity, side="buy")
            portfolio.cash -= total_cost
            portfolio.add_position(
                Position(
                    instrument=candidate,
                    quantity=quantity,
                    entry_price=price,
                    entry_time=datetime.utcnow(),
                )
            )
            self.trade_log.append(
                TradeLogEntry(
                    timestamp=datetime.utcnow(),
                    action="BUY",
                    symbol=candidate.symbol,
                    quantity=quantity,
                    price=price,
                    note="Strategivalg basert på forventet vekst",
                )
            )

    def generate_weekly_summary(self) -> str:
        """Returnerer en tekstlig rapport over ukens aktiviteter."""

        lines = ["Ukentlig rapport", "================", ""]
        if not self.trade_log:
            lines.append("Ingen handler denne uken.")
        else:
            for entry in self.trade_log:
                lines.append(
                    f"{entry.timestamp:%Y-%m-%d %H:%M} {entry.action} {entry.symbol} x{entry.quantity} til {entry.price:.2f} NOK - {entry.note}"
                )
        return "\n".join(lines)
