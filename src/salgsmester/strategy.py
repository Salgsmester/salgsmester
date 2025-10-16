"""Strategimoduler som prioriterer instrumenter etter forventet vekst og risiko."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from .config import FeeStructure, StrategyTargets
from .data_models import InstrumentSnapshot, Portfolio
from .risk import (
    RiskMetrics,
    diversify_candidates,
    estimate_portfolio_risk,
    score_instrument_risk,
)


@dataclass(slots=True)
class TradeDecision:
    buy_candidates: list[InstrumentSnapshot]
    sell_symbols: list[str]
    reason: str


@dataclass(slots=True)
class StrategyContext:
    targets: StrategyTargets
    last_rebalance: datetime | None = None


class MomentumGrowthStrategy:
    """Momentumdrevet strategi med risikovurdering og kurtasjehensyn."""

    def __init__(self, targets: StrategyTargets, fees: FeeStructure) -> None:
        self.context = StrategyContext(targets=targets)
        self.fees = fees

    def should_rebalance(self, now: datetime) -> bool:
        if self.context.last_rebalance is None:
            return True
        return now - self.context.last_rebalance >= self.context.targets.rebalance_cadence

    def evaluate(
        self,
        now: datetime,
        portfolio: Portfolio,
        instruments: Iterable[InstrumentSnapshot],
    ) -> TradeDecision:
        """Analysér markedet og identifiser kjøps- og salgsanbefalinger."""

        if not self.should_rebalance(now):
            return TradeDecision(buy_candidates=[], sell_symbols=[], reason="Rebalansering ikke nødvendig ennå")

        portfolio_risk: RiskMetrics = estimate_portfolio_risk(portfolio, self.fees)
        growth_candidates = [inst for inst in instruments if inst.last_price > 0]
        growth_candidates.sort(key=lambda inst: inst.expected_short_term_growth(), reverse=True)

        diversified = diversify_candidates(growth_candidates)
        sell_symbols = [
            position.instrument.symbol
            for position in portfolio.positions
            if position.unrealised_return_pct() >= self.context.targets.weekly_growth_target
        ]

        max_volatility = self.context.targets.max_portfolio_volatility
        filtered = [
            candidate
            for candidate in diversified
            if score_instrument_risk(candidate, self.fees) <= max_volatility
        ]

        self.context.last_rebalance = now

        reason_parts = [
            f"Porteføljevolatilitet: {portfolio_risk.volatility:.2f}",
            f"Utvalgte kandidater: {len(filtered)}",
        ]
        return TradeDecision(
            buy_candidates=filtered,
            sell_symbols=sell_symbols,
            reason="; ".join(reason_parts),
        )

    def required_weekly_trade(self, now: datetime, portfolio: Portfolio) -> bool:
        """Sjekk om det må gjennomføres minst én handel denne uken."""

        last_trade = portfolio.last_trade_time
        if last_trade is None:
            return True
        return now - last_trade >= timedelta(days=7)
