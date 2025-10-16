"""Moduler for risikovurdering."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable

from .config import FeeStructure
from .data_models import InstrumentSnapshot, Portfolio


@dataclass(slots=True)
class RiskMetrics:
    volatility: float
    downside_risk: float
    exposure_concentration: float


def estimate_portfolio_risk(portfolio: Portfolio, fees: FeeStructure) -> RiskMetrics:
    """Estimerer porteføljerisiko basert på posisjonsvolatilitet."""

    if not portfolio.positions:
        return RiskMetrics(volatility=0.0, downside_risk=0.0, exposure_concentration=0.0)

    volatilities = [p.instrument.volatility for p in portfolio.positions]
    net_values: list[float] = []
    for position in portfolio.positions:
        gross_value = position.market_value()
        fee = fees.fixed_fee + gross_value * fees.variable_fee_rate
        net_values.append(max(gross_value - fee, 0.0))

    total_net_value = sum(net_values) + portfolio.cash
    if total_net_value <= 0:
        return RiskMetrics(volatility=0.0, downside_risk=0.0, exposure_concentration=0.0)

    weights = [value / total_net_value for value in net_values]

    weighted_volatility = sum(v * w for v, w in zip(volatilities, weights))
    downside_components = []
    for position in portfolio.positions:
        gross_value = position.market_value()
        fee = fees.fixed_fee + gross_value * fees.variable_fee_rate
        fee_drag = fee / gross_value if gross_value else 0.0
        downside_components.append(max(-position.instrument.daily_change_pct, 0.0) + fee_drag)

    downside = fmean(downside_components)
    concentration = max(weights)

    return RiskMetrics(
        volatility=weighted_volatility,
        downside_risk=downside,
        exposure_concentration=concentration,
    )


def score_instrument_risk(
    instrument: InstrumentSnapshot,
    fees: FeeStructure,
    notional: float = 10000.0,
) -> float:
    """Gir et risikoscore for instrumentet basert på volatilitet og momentum."""

    volatility_penalty = instrument.volatility
    downside_buffer = max(-instrument.daily_change_pct, 0.0)
    gross = max(notional, instrument.last_price)
    fee_ratio = (fees.fixed_fee + gross * fees.variable_fee_rate) / gross
    return volatility_penalty + downside_buffer + fee_ratio


def diversify_candidates(candidates: Iterable[InstrumentSnapshot], max_per_sector: int = 2) -> list[InstrumentSnapshot]:
    """Filtrer kandidater slik at porteføljen får bedre diversifisering."""

    selected: list[InstrumentSnapshot] = []
    sector_counts: dict[str, int] = {}

    for candidate in sorted(candidates, key=lambda c: c.expected_short_term_growth(), reverse=True):
        sector = candidate.sector or "ukjent"
        if sector_counts.get(sector, 0) >= max_per_sector:
            continue
        selected.append(candidate)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    return selected
