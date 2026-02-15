# External Data Sources — Phase 5

This document describes all external (non-physics) data sources used in Phase 5 of the
Seasonal Energy Storage Exergy Copilot.

---

## Electricity Price Data

### Source
**SMARD (Strommarktdaten, Germany)**

### Endpoint Stability Note
The older SMARD `app/chart_data/...` endpoints were unstable in our environment
(404 / redirects / TLS issues). Therefore, the official SMARD Download Center backend
was used, which is designed for bulk historical downloads and proved reliable.

### Unit Handling
Electricity prices are stored exactly as provided by the SMARD CSV export and labeled
as EUR/MWh in the local cache. No unit conversion is performed in Phase 5.

### Market / Region
- **DE-LU** (Germany–Luxembourg bidding zone)
- Valid for historical analysis 2021–2023

### Data Type
- Day-ahead electricity prices
- Resolution: **hourly**

### Access Method (Implemented)
- SMARD **Download Center backend**
- Endpoint:
https://www.smard.de/nip-download-manager/nip/download/market-data
- Format: CSV

### Reason for Choosing Download Center Method
- No API key required
- Reliable for large historical ranges
- Avoids instability observed in older `app/chart_data/...` endpoints
(404 / redirect / TLS issues)

### Caching Strategy
- Local cache: **SQLite**
- Database: `data/cache/external_data.db`
- Table: `electricity_price(market, timestamp, price_EUR_per_MWh, source)`
- Rule:
- First run downloads and fills cache
- Subsequent runs **do not re-download** data

### Provenance
- All electricity prices are wrapped as `ValueSpec(EXTERNAL)`
- Source metadata: `SMARD`

### Explicit Non-Actions
- No unit conversion (EUR/MWh → J)
- No interpolation of missing hours
- No price-based physics calculations

---

## Weather Data
- Not yet implemented in Phase 5
- Reserved for future Phase (explicitly out of current scope)

---

## Reproducibility Statement
Once the cache is filled, all simulations:
- Run fully offline
- Produce deterministic results
- Are independent of external network availability