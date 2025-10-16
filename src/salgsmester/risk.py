"""Moduler for risikovurdering."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable

from .data_models import InstrumentSnapshot, Portfolio


@dataclass(slots=True)
class RiskMetrics:
    volatility: float
    downside_risk: float
    exposure_concentration: float


def estimate_portfolio_risk(portfolio: Portfolio) -> RiskMetrics:
    """Estimerer porteføljerisiko basert på posisjonsvolatilitet."""

    if not portfolio.positions:
        return RiskMetrics(volatility=0.0, downside_risk=0.0, exposure_concentration=0.0)

    volatilities = [p.instrument.volatility for p in portfolio.positions]
    weights = [p.market_value() / portfolio.total_value() for p in portfolio.positions]

    weighted_volatility = sum(v * w for v, w in zip(volatilities, weights))
    downside = fmean(max(-p.instrument.daily_change_pct, 0.0) for p in portfolio.positions)
    concentration = max(weights)

    return RiskMetrics(
        volatility=weighted_volatility,
        downside_risk=downside,
        exposure_concentration=concentration,
    )


def score_instrument_risk(instrument: InstrumentSnapshot) -> float:
    """Gir et risikoscore for instrumentet basert på volatilitet og momentum."""

    volatility_penalty = instrument.volatility
    downside_buffer = max(-instrument.daily_change_pct, 0.0)
    return volatility_penalty + downside_buffer


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
