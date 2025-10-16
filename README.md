# Salgsmester – Automatisert Nordnet-rammeverk

> **Viktig:** All handel i finansmarkedene innebærer risiko. Koden i dette
> prosjektet gir ingen garantier for avkastning og må brukes ansvarlig i tråd med
> gjeldende lovverk, kundevilkår og egen risikotoleranse.

Dette repositoriet inneholder et Python-rammeverk som hjelper deg å analysere og
handle verdipapirer på Oslo Børs via Nordnet. Systemet forsøker å:

- identifisere instrumenter med høy forventet kortsiktig vekst
- ta hensyn til volatilitet, kurtasje og diversifisering
- sikre minst én handel per uke
- generere ukentlige rapporter over aktivitet

## Arkitektur

Prosjektet består av flere moduler i `src/salgsmester`:

- `config.py` – konfigurasjonsmodeller, inkludert mål for ukentlig vekst
- `nordnet_client.py` – innlogging og kommunikasjon med Nordnet API
- `data_models.py` – modeller for markedsdata og portefølje
- `risk.py` – beregninger knyttet til risiko og diversifisering
- `strategy.py` – momentumstrategi som forsøker å nå ukentlig vekstmål
- `portfolio_manager.py` – styrer handler, kurtasje og loggføring
- `reporting.py` – skriver og sender ukentlige rapporter
- `main.py` – kommandolinjegrensesnitt

## Komme i gang

### 1. Installer og aktiver prosjektet

```bash
git clone https://github.com/<din-bruker>/salgsmester.git
cd salgsmester
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

Dette installerer pakken i utviklingsmodus slik at du får et kommandolinjeprogram
som heter `salgsmester`.

### 2. Konfigurer legitimasjon

Kopier `.env.example` til `.env` og fyll inn egne verdier. Deretter kan du laste
inn variablene i terminalen:

```bash
cp .env.example .env
source .env
```

Vil du sette dem permanent, kan du legge dem i shell-profilen din eller bruke en
hemmelighetsmanager. Følgende variabler må være satt:

| Variabel | Beskrivelse |
| --- | --- |
| `SALGSMESTER_NORDNET_USERNAME` | Nordnet-brukernavn |
| `SALGSMESTER_NORDNET_PASSWORD` | Passordet ditt |
| `SALGSMESTER_ACCOUNT_ID` | Konto-ID for aksjesparekontoen som skal brukes |
| `SALGSMESTER_NORDNET_SECRET` | *(Valgfritt)* Base32-kodet TOTP-nøkkel for 2FA |

### 3. Kjør i testmodus (anbefalt)

Start programmet i «dry-run» slik at det analyserer markedet, men ikke legger inn
faktiske ordre:

```bash
salgsmester --dry-run
```

Terminalen vil vise porteføljeverdien og hvilken beslutning strategien tok.
Rapporter lagres i `data/weekly_report.txt`.

### 4. Bytt til livehandel

Når du er trygg på at konfigurasjonen er korrekt og har bekreftet med Nordnet at
automatisert handel er lov, kan du fjerne `--dry-run`:

```bash
salgsmester
```

Programmet logger inn, gjør nødvendige handler og oppdaterer rapporten.

### 5. Automatiser kjøringen (valgfritt)

Verktøyet er designet for å kjøres én gang per børsdag. Du kan for eksempel bruke
`cron` på Linux/macOS:

```bash
0 7 * * 1-5 /path/til/prosjekt/.venv/bin/python -m salgsmester.main >> salgsmester.log 2>&1
```

Tilpass tidspunktet til når markedet åpner og sørg for at miljøvariablene er
tilgjengelige i cron-jobben.

## Rapportering

Rapporter lagres under `data/weekly_report.txt`. Vil du sende dem på e-post, må
du samtidig oppgi SMTP-innstillinger via flaggene:

```bash
salgsmester --report-email mottaker@domene.no \
            --report-sender avsender@domene.no \
            --smtp-host smtp.domene.no \
            --smtp-port 587
```

CLI-en støtter `--help` for komplett oversikt over flaggene.

## Videre arbeid

- Integrere bedre risikomodeller (Value at Risk, Monte Carlo)
- Implementere historisk datalagring for forbedret analyse
- Utvide strategi med stop-loss og dynamiske mål
