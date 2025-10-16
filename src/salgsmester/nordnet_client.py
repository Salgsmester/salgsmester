"""Klient for å kommunisere med Nordnet sine API-endepunkter.

Merk: Nordnet tilbyr ikke et offisielt offentlig API for automatisert handel. Denne
klassen bruker konvensjoner fra det uoffisielle API-et som er dokumentert av
miljøet rundt Nordnet. Brukeren må selv sørge for at automatisert handel er
lovlig og at avtaler med banken tillater bruk av et slikt verktøy.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import requests

from .config import FeeStructure, NordnetCredentials
from .data_models import InstrumentSnapshot, Portfolio, Position


@dataclass(slots=True)
class NordnetClient:
    """Håndterer innlogging, henting av data og ordrelegging."""

    credentials: NordnetCredentials
    fees: FeeStructure
    base_url: str = "https://www.nordnet.no/api"
    session: requests.Session = field(default_factory=requests.Session)

    def authenticate(self) -> None:
        """Logger inn i Nordnet.

        Implementasjonen bruker web-grensesnittet sitt innloggingsendepunkt. For å
        beskytte brukeren lagres ingen sensitive data i klartekst i koden.
        """

        if not self.credentials.username or not self.credentials.password:
            raise ValueError(
                "Mangler brukernavn/passord. Sett miljøvariabler eller oppdater konfigurasjon."
            )

        login_payload = {
            "username": self.credentials.username,
            "password": self.credentials.password,
        }

        response = self.session.post(
            f"{self.base_url}/login",
            data=json.dumps(login_payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()

        if self.credentials.secret_key:
            self._complete_two_factor(self.credentials.secret_key)

    def _complete_two_factor(self, secret_key: str) -> None:
        """Fullfører tofaktorautentisering dersom det er aktivert."""

        token = self._generate_totp(secret_key)
        response = self.session.post(
            f"{self.base_url}/login/2fa",
            data=json.dumps({"token": token}),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()

    def _generate_totp(self, secret_key: str) -> str:
        """Genererer en TOTP-kode.

        I produksjon anbefales det å bruke et bibliotek som `pyotp`. Her benyttes
        en lettvektsimplementasjon for å unngå ekstra avhengigheter.
        """

        import base64
        import hmac
        import struct
        import time

        key = base64.b32decode(secret_key.upper())
        timestep = int(time.time() // 30)
        msg = struct.pack(">Q", timestep)
        h = hmac.new(key, msg, "sha1").digest()
        o = h[-1] & 0x0F
        code = (struct.unpack(">I", h[o : o + 4])[0] & 0x7FFFFFFF) % 1000000
        return f"{code:06d}"

    # ------------------------- Markedsdata -------------------------
    def fetch_instruments(self) -> list[InstrumentSnapshot]:
        """Henter tilgjengelige instrumenter på Oslo Børs."""

        response = self.session.get(
            f"{self.base_url}/market/nor/ose/instruments",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        instruments: list[InstrumentSnapshot] = []
        for item in data:
            instruments.append(
                InstrumentSnapshot(
                    symbol=item["symbol"],
                    name=item.get("name", item["symbol"]),
                    last_price=float(item.get("lastPrice", 0.0)),
                    daily_change_pct=float(item.get("changePercent", 0.0)) / 100,
                    weekly_change_pct=float(item.get("weekChangePercent", 0.0)) / 100,
                    volatility=float(item.get("volatility", 0.2)),
                    sector=item.get("sector"),
                )
            )
        return instruments

    def fetch_portfolio(self) -> Portfolio:
        """Henter porteføljeinformasjon for valgt aksjesparekonto."""

        account_id = self.credentials.account_id
        if not account_id:
            raise ValueError(
                "Mangler konto-ID. Oppdater konfigurasjonen med gyldig aksjesparekonto."
            )

        response = self.session.get(
            f"{self.base_url}/accounts/{account_id}/positions",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        portfolio = Portfolio(cash=float(data.get("cash", 0.0)))
        for position in data.get("positions", []):
            instrument = InstrumentSnapshot(
                symbol=position["symbol"],
                name=position.get("name", position["symbol"]),
                last_price=float(position.get("lastPrice", 0.0)),
                daily_change_pct=float(position.get("changePercent", 0.0)) / 100,
                weekly_change_pct=float(position.get("weekChangePercent", 0.0)) / 100,
                volatility=float(position.get("volatility", 0.2)),
                sector=position.get("sector"),
            )
            portfolio.positions.append(
                Position(
                    instrument=instrument,
                    quantity=float(position.get("quantity", 0.0)),
                    entry_price=float(position.get("averagePrice", 0.0)),
                    entry_time=datetime.fromisoformat(
                        position.get("purchaseDate", datetime.utcnow().isoformat())
                    ),
                )
            )
        return portfolio

    # -------------------------- Ordrehåndtering --------------------------
    def place_order(
        self,
        symbol: str,
        quantity: float,
        order_type: str = "market",
        side: str = "buy",
        price: Optional[float] = None,
    ) -> dict[str, Any]:
        """Plasserer en ordre gjennom Nordnet.

        `side` må være `buy` eller `sell`. Programmet tar hensyn til kurtasje via
        `FeeStructure` når volum foreslås.
        """

        if side not in {"buy", "sell"}:
            raise ValueError("side må være 'buy' eller 'sell'")

        order_payload: dict[str, Any] = {
            "symbol": symbol,
            "quantity": quantity,
            "orderType": order_type,
            "side": side,
        }
        if price is not None:
            order_payload["price"] = price

        response = self.session.post(
            f"{self.base_url}/orders",
            data=json.dumps(order_payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def estimate_trade_fee(self, price: float, quantity: float) -> float:
        """Beregner forventet kurtasje for en handel."""

        gross = price * quantity
        return self.fees.fixed_fee + gross * self.fees.variable_fee_rate

    def estimate_total_buy_cost(self, price: float, quantity: float) -> float:
        """Beregner totalkostnaden for et kjøp inkludert kurtasje."""

        return price * quantity + self.estimate_trade_fee(price, quantity)

    def estimate_net_sell_proceeds(self, price: float, quantity: float) -> float:
        """Beregner netto salgsproveny etter kurtasje."""

        gross = price * quantity
        fee = self.estimate_trade_fee(price, quantity)
        return max(gross - fee, 0.0)
