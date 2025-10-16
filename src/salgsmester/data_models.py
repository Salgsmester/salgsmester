"""Datamodeller og porteføljestrukturer for Salgsmester."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional


@dataclass(slots=True)
class InstrumentSnapshot:
    """Representerer markedsdata for ett enkelt instrument."""

    symbol: str
    name: str
    last_price: float
    daily_change_pct: float
    weekly_change_pct: float
    volatility: float
    sector: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def expected_short_term_growth(self) -> float:
        """Estimer forventet kortsiktig vekst basert på momentum og trender."""

        momentum = (self.daily_change_pct * 0.4) + (self.weekly_change_pct * 0.6)
        risk_adjustment = max(1.0 - self.volatility, 0.1)
        return momentum * risk_adjustment


@dataclass(slots=True)
class Position:
    """Representerer en posisjon i porteføljen."""

    instrument: InstrumentSnapshot
    quantity: float
    entry_price: float
    entry_time: datetime

    def market_value(self) -> float:
        return self.instrument.last_price * self.quantity

    def unrealised_return_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return (self.instrument.last_price - self.entry_price) / self.entry_price


@dataclass(slots=True)
class Portfolio:
    """Representerer hele porteføljen."""

    positions: list[Position] = field(default_factory=list)
    cash: float = 0.0
    last_trade_time: Optional[datetime] = None

    def total_value(self) -> float:
        return self.cash + sum(position.market_value() for position in self.positions)

    def add_position(self, position: Position) -> None:
        self.positions.append(position)
        self.last_trade_time = position.entry_time

    def remove_position(self, symbol: str) -> Optional[Position]:
        for idx, position in enumerate(self.positions):
            if position.instrument.symbol == symbol:
                removed = self.positions.pop(idx)
                self.last_trade_time = datetime.utcnow()
                return removed
        return None

    def iter_positions(self) -> Iterable[Position]:
        return iter(self.positions)

    def exposure_by_sector(self) -> dict[str, float]:
        exposure: dict[str, float] = {}
        for position in self.positions:
            sector = position.instrument.sector or "ukjent"
            exposure[sector] = exposure.get(sector, 0.0) + position.market_value()
        return exposure
